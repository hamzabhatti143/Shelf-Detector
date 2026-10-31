import re
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
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
_NON_DIGIT = re.compile(r"\D")
_LEFTOVER_DOT = re.compile(r"[.,](?=\d{3,}(?:[.,]|$))")
_ARABIC_DECIMAL = "\u066b"
_ARABIC_THOUSANDS = "\u066c"
_QUOTE_NOISE = " '\"`\u2018\u2019"
_FRAGMENT_AREA_RATIO = 0.6  # an unreadable tag smaller than this share of the median tag is a fragment
_MIN_READ_HEIGHT = 10  # px: a box shorter than this is too small for OCR to read digits

Reading = tuple[str, float | None, float]  # text, price, ocr confidence
_EMPTY: Reading = ("", None, 0.0)


@dataclass(frozen=True, slots=True)
class PriceTagReading:
    box: Box  # pixel coordinates; box.conf is the detector's confidence
    text: str  # the digits as read from the tag, never edited
    price: float | None  # only set when the text is unambiguous
    ocr_confidence: float


class TagReader(Protocol):
    def read(self, image: np.ndarray, *, ocr: bool = True, budget_s: float | None = None) -> list[PriceTagReading]: ...


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
    # leftover dot of a currency like 'Rs.' ('.380', 's.320'): 3+ digits follow, so it is no decimal point
    if _LEFTOVER_DOT.match(cleaned):
        cleaned = cleaned[1:]

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


def read_line(tokens: list[OcrToken], join: bool) -> Reading | None:
    """join=True: the crop is the price area, so read the whole price line as printed.
    join=False: the crop is a whole tag, so take only the tallest number (the price is
    the biggest text; barcode and unit-price digits are smaller)."""
    numeric = [t for t in tokens if _has_digit(t)]
    if not numeric:
        return None
    main = max(numeric, key=lambda t: (t.height, t.conf))
    chosen = _line_around(main, numeric) if join else [main]
    text = "".join(normalize_digits(t.text).strip(_QUOTE_NOISE) for t in chosen)
    return text, parse_price(text), min(t.conf for t in chosen)


def _digit_key(text: str) -> str:
    return _NON_DIGIT.sub("", normalize_digits(text))


def consensus(readings: list[Reading]) -> Reading:
    """Merge several OCR passes over crops of the same price into one real OCR output.
    The digit sequence that at least two passes agree on wins; inside that group the
    longest text wins, since OCR drops small marks like '.' and '$' more often than it
    invents them. If two or more passes read something but none agree, the reading is
    unreliable (a '$' read as '5' flips the price), so nothing is reported rather than
    a wrong number. Text is never edited."""
    valid = [r for r in readings if r[0]]
    if not valid:
        return _EMPTY
    groups: dict[str, list[Reading]] = {}
    for r in valid:
        groups.setdefault(_digit_key(r[0]), []).append(r)
    best = max(groups.values(), key=lambda g: (len(g), max(r[2] for r in g)))
    if len(valid) >= 2 and len(best) < 2:
        return _EMPTY
    return max(best, key=lambda r: (len(r[0]), r[2]))


def _agreed(readings: list[Reading]) -> bool:
    """True once two passes read the same digit sequence."""
    seen: dict[str, int] = {}
    for text, _, _ in readings:
        if text:
            key = _digit_key(text)
            seen[key] = seen.get(key, 0) + 1
    return any(n >= 2 for n in seen.values())


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
    """OCR engines are not shared between threads: each worker thread builds its own."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._local = threading.local()

    def _get_engine(self):
        engine = getattr(self._local, "engine", None)
        if engine is None:
            if self._settings.ocr_engine == "rapidocr":
                from rapidocr import RapidOCR  # lazy; package `rapidocr` (v3)

                engine = RapidOCR(
                    params={
                        "Det.limit_side_len": self._settings.ocr_det_min_side,
                        "Det.limit_type": "min",
                        "EngineConfig.onnxruntime.intra_op_num_threads": self._settings.ocr_threads,
                        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
                        "Global.log_level": "warning",
                    }
                )
            else:
                import easyocr  # lazy: slow import and model download

                engine = easyocr.Reader(self._settings.ocr_languages, gpu=self._settings.ocr_gpu)
            self._local.engine = engine
        return engine

    def warm(self) -> None:
        self._get_engine()

    def _run(self, image: np.ndarray) -> list[tuple[list, str, float]]:
        engine = self._get_engine()
        if self._settings.ocr_engine == "rapidocr":
            result = engine(image)
            if result.boxes is None:
                return []
            return [
                (box.tolist(), str(text), float(score))
                for box, text, score in zip(result.boxes, result.txts, result.scores)
            ]
        return engine.readtext(
            image, allowlist=self._settings.ocr_allowlist, detail=1, paragraph=False
        )

    def read_price(self, crop: np.ndarray, join: bool = True) -> Reading:
        if crop.size == 0:
            return _EMPTY
        tokens: list[OcrToken] = []
        for points, text, conf in self._run(_prepare_crop(crop)):
            if conf < self._settings.ocr_min_conf:
                continue
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            tokens.append(OcrToken(min(xs), min(ys), max(xs), max(ys), text.strip(), float(conf)))
        found = read_line(tokens, join)
        return found if found is not None else _EMPTY


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


@dataclass(frozen=True, slots=True)
class _Job:
    box: Box  # the box that is reported
    price_box: Box | None  # tight price area to read first, when the model found one
    orphan: bool  # a price area with no tag around it


class PriceTagReader:
    """The model finds whole tags (price-tags) and their price area (price-tag-price).
    OCR runs on the price area (or the whole tag when no price area was found or it
    caught nothing) at several crop margins, and the passes are merged by consensus.
    If a tag has several price boxes, the biggest wins, so a 'card price' beats a small
    regular price. Whether that is the right one is a store decision, not something the
    code can tell.
    Tags are read in parallel (one OCR engine per worker thread) and reading stops after
    `pricetag_time_budget_s` seconds, so latency stays bounded however many tags there
    are. Tags left unread keep their box with no text."""

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
        self._pool = ThreadPoolExecutor(max_workers=max(1, settings.ocr_workers), thread_name_prefix="ocr")
        self._lock = threading.Lock()

        workers = max(1, settings.ocr_workers)
        barrier = threading.Barrier(workers)

        def warm_up(_: int) -> None:
            self._ocr.warm()
            barrier.wait(timeout=120)

        list(self._pool.map(warm_up, range(workers)))  # build every worker's OCR engine now, not on the first upload

    def _read_multi(self, image: np.ndarray, box: Box, join: bool, margins: list[float]) -> Reading:
        """One OCR pass per crop margin. Stops early when a pass is a clear, confident price, or
        as soon as two passes agree. A single weak pass can miss a small '.' or misread '$'."""
        passes: list[Reading] = []
        for margin in margins or [TAG_CROP_MARGIN]:
            passes.append(self._ocr.read_price(crop_with_margin(image, box, margin), join))
            _, price, conf = passes[-1]
            if price is not None and conf >= self._settings.ocr_accept_conf:
                break
            if _agreed(passes):
                break
        return consensus(passes)

    def _read_job(self, image: np.ndarray, job: _Job, deadline: float) -> Reading:
        s = self._settings
        if time.monotonic() > deadline:
            return _EMPTY
        result = _EMPTY
        if job.price_box is not None and job.price_box.height >= _MIN_READ_HEIGHT:
            result = self._read_multi(image, job.price_box, True, s.price_crop_margins)
        if not result[0] and not job.orphan and job.box.height >= _MIN_READ_HEIGHT:
            result = self._read_multi(image, job.box, False, s.tag_crop_margins)  # whole tag
        return result

    def read(self, image: np.ndarray, *, ocr: bool = True, budget_s: float | None = None) -> list[PriceTagReading]:
        s = self._settings
        started = time.monotonic()
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

            areas = sorted(_area(t) for t in tags)
            median_area = areas[len(areas) // 2] if areas else 0.0

            # Most confident first, then cap, so a crowded photo cannot make OCR run for minutes.
            tags = sorted(tags, key=lambda b: b.conf, reverse=True)[: s.pricetag_max_reads]
            prices = sorted(prices, key=lambda b: b.conf, reverse=True)[: s.pricetag_max_reads * 2]

            jobs: list[_Job] = []
            used: set[int] = set()
            for tag in tags:
                inside = [i for i, p in enumerate(prices) if inside_fraction(p, tag) >= PRICE_INSIDE_TAG_MIN]
                used.update(inside)
                price_box = prices[max(inside, key=lambda i: _area(prices[i]))] if inside else None
                jobs.append(_Job(tag, price_box, False))
            for index, price_box in enumerate(prices):
                if index not in used and len(jobs) < s.pricetag_max_reads:
                    jobs.append(_Job(price_box, price_box, True))

            if ocr:
                deadline = started + (budget_s if budget_s is not None else s.pricetag_time_budget_s)
                results = list(self._pool.map(lambda job: self._read_job(image, job, deadline), jobs))
            else:  # boxes only (live video frames): no OCR
                results = [_EMPTY for _ in jobs]

        readings: list[PriceTagReading] = []
        for job, (text, price, ocr_conf) in zip(jobs, results):
            if not text and job.orphan:
                continue  # a price box with no tag and nothing readable is noise
            if not text and _area(job.box) < _FRAGMENT_AREA_RATIO * median_area:
                continue  # unreadable and much smaller than real tags: a fragment, not a tag
            readings.append(PriceTagReading(box=job.box, text=text, price=price, ocr_confidence=ocr_conf))

        readings.sort(key=lambda r: (round(r.box.cy / 50), r.box.x1))
        return readings


def build_tag_reader(settings: Settings) -> PriceTagReader | None:
    return PriceTagReader(settings) if settings.price_tags else None