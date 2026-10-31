import sys
from pathlib import Path

import cv2

from app.config import get_settings
from app.services.price_tags import PriceTagReader, crop_with_margin

path = sys.argv[1]
img = cv2.imread(path)
s = get_settings()
reader = PriceTagReader(s)
ocr = reader._ocr._get_reader()
res = reader._model.predict(img, conf=0.25, imgsz=1280, verbose=False)[0]
names = reader._model.names
out_dir = Path("debug_crops")
out_dir.mkdir(exist_ok=True)


def up(c, h):
    k = max(1.0, h / c.shape[0])
    return cv2.resize(c, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)


def clahe(c):
    g = cv2.createCLAHE(2.0, (8, 8)).apply(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY))
    return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)


def sharp(c):
    return cv2.addWeighted(c, 1.8, cv2.GaussianBlur(c, (0, 0), 3), -0.8, 0)


def pad(c):
    return cv2.copyMakeBorder(c, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255))


def read(c, allow=True):
    kw = {"allowlist": s.ocr_allowlist} if allow else {}
    return [(t, round(float(p), 2)) for _, t, p in ocr.readtext(pad(c), detail=1, **kw)]


for i, (b, cls) in enumerate(zip(res.boxes.xyxy.cpu().numpy(), res.boxes.cls.cpu().numpy().astype(int))):
    from app.detectors.base import Box
    box = Box(*map(float, b))
    crop = crop_with_margin(img, box, 0.05)
    cv2.imwrite(str(out_dir / f"{i:02d}_{names[cls]}.png"), crop)
    print(f"#{i} {names[cls]} {crop.shape[1]}x{crop.shape[0]}px")
    for label, v in [
        ("base96", up(crop, 96)),
        ("up200", up(crop, 200)),
        ("clahe200", clahe(up(crop, 200))),
        ("sharp200", sharp(up(crop, 200))),
    ]:
        print(f"   {label:9}", read(v))
    print("   noallow  ", read(up(crop, 200), allow=False))