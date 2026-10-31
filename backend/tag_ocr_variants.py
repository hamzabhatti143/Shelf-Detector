import sys

import cv2

from app.config import get_settings
from app.detectors.base import Box
from app.services.price_tags import PriceTagReader, _prepare_crop, crop_with_margin

img = cv2.imread(sys.argv[1])
s = get_settings()
r = PriceTagReader(s)
ocr = r._ocr._get_reader()
res = r._model.predict(img, conf=0.25, imgsz=1280, verbose=False)[0]
names = r._model.names

VARIANTS = {
    "now      ": s.ocr_allowlist,
    "digits   ": "0123456789.,",
    "+S$sRr   ": "0123456789.,$SsRr",
    "none     ": None,
}

rows = []
for b, c in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.cls.cpu().numpy().astype(int)):
    if names[c] != "price-tag-price":
        continue
    rows.append((b[1] // 60, b[0], b))

for _, _, b in sorted(rows, key=lambda t: (t[0], t[1])):
    crop = _prepare_crop(crop_with_margin(img, Box(*map(float, b)), 0.05))
    print(f"x={int(b[0])} y={int(b[1])}")
    for label, allow in VARIANTS.items():
        kw = {"allowlist": allow} if allow else {}
        out = [(t, round(float(p), 2)) for _, t, p in ocr.readtext(crop, detail=1, **kw)]
        print("  ", label, out)