import sys

import cv2

from app.config import get_settings
from app.services import price_tags as pt

orig = pt.PriceTagReader._read_multi


def logged(self, image, box, join, margins):
    passes = []
    for m in margins:
        r = self._ocr.read_price(pt.crop_with_margin(image, box, m), join)
        passes.append((m, r[0], round(r[2], 2)))
    final = pt.consensus([(t, None, c) for _, t, c in passes])
    if not final[0]:
        print(
            f"EMPTY box=({int(box.x1)},{int(box.y1)},{int(box.x2)},{int(box.y2)}) "
            f"join={join} {box.width:.0f}x{box.height:.0f}px passes={passes}"
        )
    return orig(self, image, box, join, margins)


pt.PriceTagReader._read_multi = logged
reader = pt.PriceTagReader(get_settings())
img = cv2.imread(sys.argv[1])
reader.read(img)
res = reader._model.predict(img, conf=get_settings().pricetag_conf, imgsz=get_settings().pricetag_imgsz, verbose=False)[0]
for b, c, p in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.cls.cpu().numpy(), res.boxes.conf.cpu().numpy()):
    if 760 < b[0] < 830 and 160 < b[1] < 200:
        print("MODEL", reader._model.names[int(c)], [int(v) for v in b], round(float(p), 2))