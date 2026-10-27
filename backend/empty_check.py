import sys

import cv2
from ultralytics import YOLO

path = sys.argv[1]
emp = YOLO("weights/empty.pt")
empty_ids = [i for i, n in emp.names.items() if n == "empty"]
img = cv2.imread(path)
assert img is not None, "image nahi mili, path check karo"

for size in (480, 640, 960):
    for conf in (0.40, 0.25, 0.10):
        r = emp.predict(img, imgsz=size, conf=conf, classes=empty_ids, verbose=False)[0]
        print(f"imgsz={size} conf={conf} -> {len(r.boxes)} empty boxes")

r = emp.predict(img, imgsz=640, conf=0.10, classes=empty_ids, verbose=False)[0]
out = img.copy()
for x1, y1, x2, y2 in r.boxes.xyxy.int().tolist():
    cv2.rectangle(out, (x1, y1), (x2, y2), (0, 0, 255), 5)
cv2.imwrite("empty_check.jpg", cv2.resize(out, None, fx=0.5, fy=0.5))
print("saved: empty_check.jpg")