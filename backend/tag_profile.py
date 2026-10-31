import sys
import time

import cv2

from app.config import get_settings
from app.services.price_tags import PriceTagReader

s = get_settings()
reader = PriceTagReader(s)
img = cv2.imread(sys.argv[1])
print("image", img.shape[1], "x", img.shape[0], "| max_reads", s.pricetag_max_reads, "| price margins", s.price_crop_margins, "| tag margins", s.tag_crop_margins)

calls = {"price": [0, 0.0], "tag": [0, 0.0]}
orig = reader._ocr.read_price


def timed(crop, join=True):
    t = time.time()
    r = orig(crop, join)
    k = "price" if join else "tag"
    calls[k][0] += 1
    calls[k][1] += time.time() - t
    return r


reader._ocr.read_price = timed
reader.read(img)  # warm-up, model load
calls["price"] = [0, 0.0]
calls["tag"] = [0, 0.0]

t0 = time.time()
r = reader._model.predict(img, conf=s.pricetag_conf, imgsz=s.pricetag_imgsz, max_det=s.pricetag_max_det, verbose=False)[0]
t_yolo = time.time() - t0
cls = r.boxes.cls.cpu().numpy().astype(int)
print(f"YOLO tag model: {t_yolo:.1f}s | tags {int((cls == reader._tag_id).sum())} prices {int((cls == reader._price_id).sum())}")

t0 = time.time()
out = reader.read(img)
total = time.time() - t0
print(f"TOTAL read(): {total:.1f}s | readings {len(out)}")
for k, (n, sec) in calls.items():
    print(f"  OCR {k:5}: {n} calls, {sec:.1f}s total, {sec / max(n, 1):.2f}s each")