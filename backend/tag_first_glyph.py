import sys
from pathlib import Path

import cv2
import numpy as np

from app.config import get_settings
from app.detectors.base import Box
from app.services.price_tags import PriceTagReader, _prepare_crop, crop_with_margin

img = cv2.imread(sys.argv[1])
s = get_settings()
r = PriceTagReader(s)
ocr = r._ocr._get_reader()
res = r._model.predict(img, conf=0.25, imgsz=1280, verbose=False)[0]
names = r._model.names
out = Path("debug_price")
out.mkdir(exist_ok=True)


def ink_runs(crop):
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    has = (bw > 0).sum(axis=0) > 0
    runs, start = [], None
    for x, v in enumerate(has):
        if v and start is None:
            start = x
        if not v and start is not None:
            runs.append((start, x))
            start = None
    if start is not None:
        runs.append((start, len(has)))
    info = []
    for a, b in runs:
        if b - a < 3:
            continue
        rows = np.where((bw[:, a:b] > 0).any(axis=1))[0]
        info.append((a, b, b - a, int(rows.max() - rows.min() + 1)))
    return info


def read(c):
    return [(t, round(float(p), 2)) for _, t, p in ocr.readtext(c, allowlist=s.ocr_allowlist, detail=1)]


items = [
    (b, c) for b, c in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.cls.cpu().numpy().astype(int))
    if names[c] == "price-tag-price"
]
for n, (b, _) in enumerate(sorted(items, key=lambda t: (t[0][1] // 60, t[0][0]))):
    crop = _prepare_crop(crop_with_margin(img, Box(*map(float, b)), 0.05))
    cv2.imwrite(str(out / f"{n:02d}.png"), crop)
    runs = ink_runs(crop)
    print(f"#{n:02d} x={int(b[0])} y={int(b[1])}  blocks(w,h)={[(w, h) for _, _, w, h in runs]}")
    print("     full      ", read(crop))
    if len(runs) >= 2:
        cut = runs[0][1]
        print("     minus 1st ", read(_prepare_crop(crop[:, cut:])))