import sys
from collections import Counter

import cv2
from ultralytics import YOLO

path = sys.argv[1]
prod = YOLO("weights/product.pt")
emp = YOLO("weights/empty.pt")
img = cv2.imread(path)
assert img is not None, "image nahi mili, path check karo"

for size in (320, 480, 640, 960, 1280):
    r = prod.predict(img, imgsz=size, conf=0.20, iou=0.5, max_det=1000, verbose=False)[0]
    out = img.copy()
    for x1, y1, x2, y2 in r.boxes.xyxy.int().tolist():
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 4)
    cv2.imwrite(f"sweep_{size}.jpg", cv2.resize(out, None, fx=0.5, fy=0.5))
    print(size, "->", len(r.boxes), "boxes")

r = emp.predict(img, imgsz=640, conf=0.15, verbose=False)[0]
print("shelf model @conf 0.15:", dict(Counter(emp.names[int(c)] for c in r.boxes.cls)))