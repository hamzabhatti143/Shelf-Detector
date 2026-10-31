import sys
import time

import cv2

from app.config import get_settings
from app.services.price_tags import PriceTagReader

img = cv2.imread(sys.argv[1])
base = get_settings()
for workers, threads in [(1, 4), (2, 2), (4, 1)]:
    s = base.model_copy(update={"ocr_workers": workers, "ocr_threads": threads, "pricetag_time_budget_s": 120.0})
    r = PriceTagReader(s)  # engines are built here
    t = time.time()
    out = r.read(img)
    sec = time.time() - t
    got = sum(1 for x in out if x.price is not None)
    print(f"workers {workers} x threads {threads}: {sec:.1f}s | tags {len(out)} | with price {got}", flush=True)