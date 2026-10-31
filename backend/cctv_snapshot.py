import os
import sys

# must be set before cv2 is imported: RTSP over TCP is far more reliable than UDP
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp|stimeout;8000000")

import cv2  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.detectors.factory import build_detector  # noqa: E402

url = sys.argv[1]
safe = url.split("@")[-1] if "@" in url else url  # never print the password
cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
if not cap.isOpened():
    raise SystemExit(f"could not open {safe}: wrong address/port/login, camera offline, or not on this network")

frame = None
for _ in range(15):  # the first frames are often stale or grey; keep the last good one
    ok, f = cap.read()
    if ok and f is not None:
        frame = f
cap.release()
if frame is None:
    raise SystemExit("connected but no frame arrived")

h, w = frame.shape[:2]
print(f"camera {safe}: got a {w}x{h} frame")
cv2.imwrite("cctv_frame.jpg", frame)

det = build_detector(get_settings()).detect(frame)
out = frame.copy()
for b in det.products:
    cv2.rectangle(out, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), (60, 220, 60), 2)
for b in det.empties:
    cv2.rectangle(out, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), (0, 0, 255), 3)
cv2.imwrite("cctv_detect.jpg", out)
print(f"products {len(det.products)} | empty slots {len(det.empties)} | saved cctv_frame.jpg and cctv_detect.jpg")