import sys
from pathlib import Path

import cv2

from app.config import get_settings
from app.services.price_tags import PriceOcr, PriceTagReader

EXTS = {".jpg", ".jpeg", ".png", ".webp"}
BLUE, WHITE, BLACK = (255, 128, 0), (255, 255, 255), (0, 0, 0)
OUT_DIR = Path("tag_out")


def label(img, text: str, x: int, y: int, scale: float, thick: int) -> None:
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, BLACK, thick + 3)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, WHITE, thick)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ocr_only = "--ocr-only" in sys.argv
    if not args:
        print("usage: python tag_check.py <image|folder> [--ocr-only]")
        print("  --ocr-only: poori image ko ek tag maano (tag model ke baghair OCR test)")
        return

    settings = get_settings()
    target = Path(args[0])
    paths = [target] if target.is_file() else sorted(p for p in target.iterdir() if p.suffix.lower() in EXTS)
    ocr = PriceOcr(settings) if ocr_only else None
    reader = None if ocr_only else PriceTagReader(settings)
    OUT_DIR.mkdir(exist_ok=True)

    for path in paths:
        img = cv2.imread(str(path))
        if img is None:
            print(f"{path.name}: image nahi padhi gayi")
            continue

        if ocr is not None:
            text, price, conf = ocr.read_price(img, join=True)
            print(f"{path.name}: text={text!r} price={price} ocr_conf={conf:.2f}")
            continue

        readings = reader.read(img)
        thick = max(1, round(max(img.shape[:2]) / 700))
        read_ok = sum(1 for r in readings if r.price is not None)
        print(f"\n{path.name}: {len(readings)} tags, {read_ok} ke price parhe gaye")
        for i, r in enumerate(readings, start=1):
            b = r.box
            print(f"  #{i} det {b.conf:.2f} ({b.x1:.0f},{b.y1:.0f},{b.x2:.0f},{b.y2:.0f})"
                  f" text={r.text!r} price={r.price} ocr {r.ocr_confidence:.2f}")
            cv2.rectangle(img, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), BLUE, thick + 1)
            label(img, r.text or "?", int(b.x1), max(20, int(b.y1) - 6), 0.5 * thick + 0.5, thick)
        scale = min(1.0, 1600 / max(img.shape[:2]))
        out = cv2.resize(img, None, fx=scale, fy=scale) if scale < 1 else img
        cv2.imwrite(str(OUT_DIR / f"{path.stem}_tags.jpg"), out)

    if reader is not None:
        print(f"\nannotated images: {OUT_DIR}/")


if __name__ == "__main__":
    main()