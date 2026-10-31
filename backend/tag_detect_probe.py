import sys

import cv2

from app.config import get_settings
from app.services.price_tags import PriceTagReader

s = get_settings()
reader = PriceTagReader(s)
img = cv2.imread(sys.argv[1])
print("image", img.shape[1], "x", img.shape[0], "| settings: conf", s.pricetag_conf, "imgsz", s.pricetag_imgsz)

best = None
for imgsz in (960, 1280, 1920):
    for conf in (0.25, 0.1, 0.05):
        r = reader._model.predict(img, conf=conf, imgsz=imgsz, max_det=s.pricetag_max_det, verbose=False)[0]
        cls = r.boxes.cls.cpu().numpy().astype(int)
        tags = int((cls == reader._tag_id).sum())
        prices = int((cls == reader._price_id).sum())
        print(f"imgsz {imgsz} conf {conf}: tags {tags}, prices {prices}")
        if imgsz == 1280 and conf == 0.1:
            best = r

out = img.copy()
for b, c in zip(best.boxes.xyxy.cpu().numpy(), best.boxes.cls.cpu().numpy().astype(int)):
    color = (255, 160, 0) if c == reader._tag_id else (0, 0, 255)
    cv2.rectangle(out, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), color, 2)
cv2.imwrite("tag_probe_out.jpg", out)
print("saved tag_probe_out.jpg (neela = tag, laal = price area, imgsz 1280 conf 0.1)")