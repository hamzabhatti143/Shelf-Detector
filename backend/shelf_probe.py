import sys
import time
from pathlib import Path

import cv2

from app.config import get_settings
from app.detectors.ensemble import EnsembleDetector
from app.services.audit_service import group_rows
from app.services.price_tags import PriceOcr, normalize_digits, parse_price

SCALES = (480, 640, 960, 1280)
STRIP_BELOW = 0.5  # shelf edge ke neeche patti, row ki ooncha-i ka itna hissa
GREEN, CYAN, YELLOW, RED = (0, 200, 0), (255, 200, 0), (0, 220, 255), (0, 0, 255)


def inside_any(cx: float, cy: float, boxes) -> bool:
    return any(b.x1 <= cx <= b.x2 and b.y1 <= cy <= b.y2 for b in boxes)


def main() -> None:
    path = Path(sys.argv[1])
    img = cv2.imread(str(path))
    assert img is not None, "image nahi mili, path check karo"
    height, width = img.shape[:2]
    s = get_settings()
    detector = EnsembleDetector(s)
    print(f"{path.name}: {width}x{height}")

    print("\n[1] product model, har size par (conf 0.25):")
    for size in SCALES:
        r = detector._product.predict(
            img, imgsz=size, conf=0.25, iou=s.product_iou, max_det=s.product_max_det, verbose=False
        )[0]
        print(f"  imgsz {size}: {len(r.boxes)} boxes")

    detection, info = detector.detect_debug(img)
    rows = group_rows(detection.products)
    print(f"\n[2] ensemble: {info.per_scale_counts} -> {len(detection.products)} products, {len(rows)} shelf rows")
    for row in rows:
        print(f"  row {row.index}: neeche ka kinara y={row.bottom:.0f}, median box {row.median_w:.0f}x{row.median_h:.0f}")
    print(f"  empty candidates: {len(info.verdicts)}, report mein: {len(detection.empties)}")

    print("\n[3] price-tag model:")
    tag_boxes: list[tuple[int, ...]] = []
    if s.pricetag_weights.exists():
        from ultralytics import YOLO

        tag_model = YOLO(str(s.pricetag_weights))
        for size in (960, 1280):
            for conf in (0.25, 0.10):
                r = tag_model.predict(img, imgsz=size, conf=conf, verbose=False)[0]
                names = [tag_model.names[int(c)] for c in r.boxes.cls]
                print(f"  imgsz {size} conf {conf}: tags {names.count('price-tags')}, prices {names.count('price-tag-price')}")
                if size == 1280 and conf == 0.10:
                    tag_boxes = [tuple(int(v) for v in b) for b in r.boxes.xyxy.tolist()]
    else:
        print("  weights/pricetag.pt nahi mila")

    print("\n[4] shelf-edge patti par OCR (tag model ke baghair):")
    reader = PriceOcr(s)._get_reader()
    strips: list[tuple[int, int, int, int]] = []
    hits: list[tuple[float, float, float, float, str]] = []
    if detection.products:
        left = int(max(0, min(b.x1 for b in detection.products)))
        right = int(min(width, max(b.x2 for b in detection.products)))
    started = time.perf_counter()
    for row in rows:
        y1 = int(max(0, row.bottom - 0.1 * row.median_h))
        y2 = int(min(height, row.bottom + STRIP_BELOW * row.median_h))
        if y2 - y1 < 10 or right - left < 10:
            continue
        strips.append((left, y1, right, y2))
        for points, text, conf in reader.readtext(img[y1:y2, left:right], detail=1, paragraph=False, mag_ratio=2.0):
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            bx1, by1, bx2, by2 = left + min(xs), y1 + min(ys), left + max(xs), y1 + max(ys)
            digits = sum(c.isdigit() for c in normalize_digits(text))
            price = parse_price(text)
            on_product = inside_any((bx1 + bx2) / 2, (by1 + by2) / 2, detection.products)
            is_price = digits >= 2 and price is not None and not on_product
            print(f"  row {row.index}: {text!r:22} conf {conf:.2f} price={price} {'PRICE' if is_price else '-'}")
            if is_price:
                hits.append((bx1, by1, bx2, by2, text))
    print(f"  price jaise {len(hits)} tokens mile, OCR ka waqt {time.perf_counter() - started:.0f}s")

    for b in detection.products:
        cv2.rectangle(img, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), GREEN, 1)
    for x1, y1, x2, y2 in tag_boxes:
        cv2.rectangle(img, (x1, y1), (x2, y2), CYAN, 2)
    for x1, y1, x2, y2 in strips:
        cv2.rectangle(img, (x1, y1), (x2, y2), YELLOW, 1)
    for x1, y1, x2, y2, text in hits:
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), RED, 2)
    scale = min(1.0, 1600 / max(height, width))
    out = cv2.resize(img, None, fx=scale, fy=scale) if scale < 1 else img
    cv2.imwrite("probe_out.jpg", out)
    print("\nsaved: probe_out.jpg (hara = product, cyan = tag model, peela = OCR ki patti, laal = price jaisa text)")


if __name__ == "__main__":
    main()