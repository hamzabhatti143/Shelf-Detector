import sys
from pathlib import Path

import cv2
from ultralytics import YOLO

folder = Path(sys.argv[1])
prod = YOLO("weights/product.pt")
emp = YOLO("weights/empty.pt")
empty_ids = [i for i, n in emp.names.items() if n == "empty"]
sizes = (480, 640, 960, 1280)

photos = sorted(list(folder.glob("*.jp*g")) + list(folder.glob("*.png")))
print("photo".ljust(28), *[f"{s:>10}" for s in sizes])
for p in photos:
    img = cv2.imread(str(p))
    if img is None:
        continue
    row = []
    for s in sizes:
        n_p = len(prod.predict(img, imgsz=s, conf=0.30, iou=0.5, max_det=1000, verbose=False)[0].boxes)
        n_e = len(emp.predict(img, imgsz=s, conf=0.40, classes=empty_ids, verbose=False)[0].boxes)
        row.append(f"{n_p}p/{n_e}e")
    print(p.name[:28].ljust(28), *[f"{r:>10}" for r in row])