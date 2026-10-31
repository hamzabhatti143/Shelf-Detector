import sys
from pathlib import Path

import cv2

from app.config import get_settings
from app.services import price_tags as pt

out = Path("debug_price")
out.mkdir(exist_ok=True)
for f in out.glob("*.png"):
    f.unlink()

orig = pt.PriceOcr._run
n = {"i": 0}


def logged(self, image):
    i = n["i"]
    n["i"] += 1
    cv2.imwrite(str(out / f"{i:02d}.png"), image)
    res = orig(self, image)
    toks = []
    for points, text, conf in res:
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        toks.append((text, round(float(conf), 2), int(max(xs) - min(xs)), int(max(ys) - min(ys))))
    print(f"#{i:02d} crop={image.shape[1]}x{image.shape[0]} tokens(text,conf,w,h)={toks}")
    return res


pt.PriceOcr._run = logged
reader = pt.PriceTagReader(get_settings())
img = cv2.imread(sys.argv[1])
for k, x in enumerate(reader.read(img)):
    print(f"final {k}: tag@({int(x.box.x1)},{int(x.box.y1)}) text={x.text!r} price={x.price}")