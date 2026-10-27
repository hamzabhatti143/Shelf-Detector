import sys

from ultralytics import YOLO

model = YOLO("weights/pricetag.pt")
r = model.predict(sys.argv[1], imgsz=1280, conf=0.01, verbose=False)[0]
rows = sorted(zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist()), key=lambda x: -x[1])
for box, conf, cls in rows[:15]:
    print(f"{model.names[int(cls)]:16} {conf:.2f} {[round(v) for v in box]}")