import re
import threading
import unicodedata
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np

from app.config import Settings
from app.constants import (
    ERR_NO_PRICETAG_CLASS,
    ERR_WEIGHTS_MISSING,
    OCR_CROP_PAD,
    OCR_MIN_CROP_HEIGHT,
    PRICE_INSIDE_TAG_MIN,
    PRICE_MIN,
    PRICETAG_CLASS_PRICE,
    PRICETAG_CLASS_TAG,
    TAG_CROP_MARGIN,
)
from app.detectors.base import Box

PRICE_MAX = 1_000_000_000.0  # some currencies print prices in the millions
_NON_PRICE = re.compile(r"[^0-9.,]")
_ARABIC_DECIMAL = "\u066b"
_ARABIC_THOUSANDS = "\u066c"


@dataclass(frozen=True, slots=True)
class PriceTagReading:
    box: Box  # pixel coordinates; box.conf is the detector's confidence
    text: str  # the digits as read from the tag, never edited
    price: float | None  # only set when the text is unambiguous
    ocr_confidence: float


class TagReader(Protocol):
    def read(self, image: np.ndarray) -> list[PriceTagReading]: ...


@dataclass(frozen=True, slots=True)
class OcrToken:
    x1: float
    y1: float
    x2: float
    y2: float
    text: str
    conf: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2


def normalize_digits(text: str) -> str:
    """Digits from any script become 0-9; Arabic decimal/thousands marks become . and ,"""
    out: list[str] = []
    for ch in text:
        if ch == _ARABIC_DECIMAL:
            out.append(".")
        elif ch == _ARABIC_THOUSANDS:
            out.append(",")
        elif ch.isdecimal():
            out.append(str(unicodedata.decimal(ch)))
        else:
            out.append(ch)
    return "".join(out)


def parse_price(text: str) -> float | None:
    """Number only when the separators are unambiguous, otherwise None.
    A thousands separator is always followed by exactly 3 digits, so a last separator
    followed by 1 or 2 digits is a decimal point in every country. One separator followed
    by 3 digits could be either, so it is not guessed. No decimal is ever added."""
    cleaned = _NON_PRICE.sub("", normalize_digits(text)).rstrip(".,")
    if not any(c.isdigit() for c in cleaned):
        return None

    parts = re.split(r"[.,]", cleaned)
    seps = [c for c in cleaned if c in ".,"]
    tail = parts[-1]
    if not seps:
        number = cleaned
    elif len(set(seps)) == 2:  # mixed: the last one is the decimal mark
        if len(tail) not in (1, 2):
            return None
        number = "".join(parts[:-1]) + "." + tail
    elif len(seps) == 1:
        if len(tail) not in (1, 2):
            return None  # 1,299 or 1.299: thousands or decimal, cannot tell
        number = parts[0] + "." + tail
    else:  # same mark repeated: grouping, e.g. 1,000,000 or 1,00,000
        if len(tail) != 3:
            return None
        number = "".join(parts)

    try:
        value = float(number)
    except ValueError:
        return None
    if not PRICE_MIN < value <= PRICE_MAX:
        return None
    return round(value, 2)


def _has_digit(token: OcrToken) -> bool:
    return any(c.isdigit() for c in normalize_digits(token.text))


def _line_around(main: OcrToken, numeric: list[OcrToken]) -> list[OcrToken]:
    """Tokens on the same line as `main` (their centre inside its height), left to right,
    stopping at a gap wider than the digit height. A big '5' with a small raised '99'
    is one line; weight or barcode digits printed below are not."""
    line = sorted((t for t in numeric if main.y1 <= t.cy <= main.y2), key=lambda t: t.x1)
    index = line.index(main)
    low = high = index
    while high + 1 < len(line) and line[high + 1].x1 - line[high].x2 <= main.height:
        high += 1
    while low > 0 and line[low].x1 - line[low - 1].x2 <= main.height:
        low -= 1
    return line[low : high + 1]


def read_line(tokens: list[OcrToken], join: bool) -> tuple[str, float | None, float] | None:
    """join=True: the crop is the price area, so read the whole price line as printed.
    join=False: the crop is a whole tag, so take only the tallest number (the price is
    the biggest text; barcode and unit-price digits are smaller)."""
    numeric = [t for t in tokens if _has_digit(t)]
    if not numeric:
        return None
    main = max(numeric, key=lambda t: (t.height, t.conf))
    chosen = _line_around(main, numeric) if join else [main]
    text = "".join(normalize_digits(t.text).strip() for t in chosen)
    return text, parse_price(text), min(t.conf for t in chosen)


def crop_with_margin(image: np.ndarray, box: Box, margin: float) -> np.ndarray:
    height, width = image.shape[:2]
    mx, my = box.width * margin, box.height * margin
    x1, y1 = max(0, int(box.x1 - mx)), max(0, int(box.y1 - my))
    x2, y2 = min(width, int(box.x2 + mx)), min(height, int(box.y2 + my))
    return image[y1:y2, x1:x2]


def _prepare_crop(crop: np.ndarray) -> np.ndarray:
    height = crop.shape[0]
    if height < OCR_MIN_CROP_HEIGHT:
        scale = OCR_MIN_CROP_HEIGHT / height
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(
        crop, OCR_CROP_PAD, OCR_CROP_PAD, OCR_CROP_PAD, OCR_CROP_PAD,
        cv2.BORDER_CONSTANT, value=(255, 255, 255),
    )


class PriceOcr:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._reader = None

    def _get_reader(self):
        if self._reader is None:
            import easyocr  # lazy: slow import and model download

            self._reader = easyocr.Reader(self._settings.ocr_languages, gpu=self._settings.ocr_gpu)
        return self._reader

    def read_price(self, crop: np.ndarray, join: bool = True) -> tuple[str, float | None, float]:
        if crop.size == 0:
            return "", None, 0.0
        results = self._get_reader().readtext(
            _prepare_crop(crop), allowlist=self._settings.ocr_allowlist, detail=1, paragraph=False
        )
        tokens: list[OcrToken] = []
        for points, text, conf in results:
            if conf < self._settings.ocr_min_conf:
                continue
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            tokens.append(OcrToken(min(xs), min(ys), max(xs), max(ys), text.strip(), float(conf)))
        found = read_line(tokens, join)
        return found if found is not None else ("", None, 0.0)


def _area(box: Box) -> float:
    return max(0.0, box.width) * max(0.0, box.height)


def inside_fraction(inner: Box, outer: Box) -> float:
    """Share of `inner` that lies inside `outer` (0 to 1)."""
    width = min(inner.x2, outer.x2) - max(inner.x1, outer.x1)
    height = min(inner.y2, outer.y2) - max(inner.y1, outer.y1)
    area = _area(inner)
    if width <= 0 or height <= 0 or area <= 0:
        return 0.0
    return (width * height) / area


class PriceTagReader:
    """The model finds whole tags (price-tags) and their price area (price-tag-price).
    OCR runs on the price area only. If a tag has several price boxes, the biggest wins,
    so a 'card price' beats a small regular price. Whether that is the right one is a
    store decision, not something the code can tell.
    At most `pricetag_max_reads` readings are made per image, to keep OCR time bounded."""

    def __init__(self, settings: Settings) -> None:
        from ultralytics import YOLO  # lazy import

        if not settings.pricetag_weights.exists():
            raise FileNotFoundError(ERR_WEIGHTS_MISSING.format(path=settings.pricetag_weights))
        self._settings = settings
        self._model = YOLO(str(settings.pricetag_weights))
        by_name = {name: idx for idx, name in self._model.names.items()}
        for wanted in (PRICETAG_CLASS_TAG, PRICETAG_CLASS_PRICE):
            if wanted not in by_name:
                raise ValueError(ERR_NO_PRICETAG_CLASS.format(name=wanted, names=list(by_name)))
        self._tag_id = by_name[PRICETAG_CLASS_TAG]
        self._price_id = by_name[PRICETAG_CLASS_PRICE]
        self._ocr = PriceOcr(settings)
        self._lock = threading.Lock()

    def read(self, image: np.ndarray) -> list[PriceTagReading]:
        s = self._settings
        readings: list[PriceTagReading] = []
        with self._lock:
            result = self._model.predict(
                image, conf=s.pricetag_conf, imgsz=s.pricetag_imgsz,
                max_det=s.pricetag_max_det, verbose=False,
            )[0]
            xyxy = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy().astype(int)

            tags: list[Box] = []
            prices: list[Box] = []
            for (x1, y1, x2, y2), conf, cls in zip(xyxy, confs, classes):
                box = Box(float(x1), float(y1), float(x2), float(y2), float(conf))
                if cls == self._tag_id:
                    tags.append(box)
                elif cls == self._price_id:
                    prices.append(box)

            # Most confident first, then cap, so a crowded photo cannot make OCR run for minutes.
            tags = sorted(tags, key=lambda b: b.conf, reverse=True)[: s.pricetag_max_reads]
            prices = sorted(prices, key=lambda b: b.conf, reverse=True)[: s.pricetag_max_reads * 2]

            used: set[int] = set()
            for tag in tags:
                inside = [i for i, p in enumerate(prices) if inside_fraction(p, tag) >= PRICE_INSIDE_TAG_MIN]
                used.update(inside)
                if inside:
                    source, join = prices[max(inside, key=lambda i: _area(prices[i]))], True
                else:
                    source, join = tag, False  # no price area found: read the tallest number on the tag
                text, price, ocr_conf = self._ocr.read_price(
                    crop_with_margin(image, source, TAG_CROP_MARGIN), join
                )
                readings.append(PriceTagReading(box=tag, text=text, price=price, ocr_confidence=ocr_conf))

            for index, price_box in enumerate(prices):
                if index in used:
                    continue
                if len(readings) >= s.pricetag_max_reads:
                    break
                text, price, ocr_conf = self._ocr.read_price(
                    crop_with_margin(image, price_box, TAG_CROP_MARGIN), True
                )
                readings.append(PriceTagReading(box=price_box, text=text, price=price, ocr_confidence=ocr_conf))

        readings.sort(key=lambda r: (round(r.box.cy / 50), r.box.x1))
        return readings


def build_tag_reader(settings: Settings) -> PriceTagReader | None:
    return PriceTagReader(settings) if settings.price_tags else None