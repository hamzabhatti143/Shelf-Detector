import statistics
import sys

import cv2

from app.config import get_settings
from app.services import price_tags as pt

s = get_settings().model_copy(update={"pricetag_time_budget_s": 600.0})
img = cv2.imread(sys.argv[1])
print("image", img.shape[1], "x", img.shape[0], "| max side kept for cameras:", s.video_frame_max_side)

orig = pt.PriceTagReader._read_multi
rows = []


def logged(self, image, box, join, margins):
    passes = []
    for m in margins:
        r = self._ocr.read_price(pt.crop_with_margin(image, box, m), join)
        passes.append((m, r[0], round(r[2], 2)))
    rows.append((box, join, passes))
    return orig(self, image, box, join, margins)


pt.PriceTagReader._read_multi = logged
reader = pt.PriceTagReader(s)
readings = reader.read(img)

heights = []
for box, join, passes in sorted(rows, key=lambda r: (round(r[0].cy / 40), r[0].x1)):
    kind = "price area" if join else "whole tag"
    heights.append(box.height)
    print(f"{kind:10} {box.width:4.0f}x{box.height:3.0f}px at ({box.x1:.0f},{box.y1:.0f}) -> {passes}")
read_ok = sum(1 for r in readings if r.price is not None)
print(f"\ntags {len(readings)} | with a price {read_ok} | median box height {statistics.median(heights) if heights else 0:.0f}px")
print("final:", [(r.text, r.price) for r in readings])