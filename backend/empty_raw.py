import sys
from pathlib import Path

import cv2

from app.config import get_settings
from app.detectors.factory import build_detector
from app.services.video_service import iter_timed_frames, video_plan

s = get_settings()
path = Path(sys.argv[1])
want = int(sys.argv[2]) if len(sys.argv) > 2 else 0  # which sampled frame
det = build_detector(s)
fps, step, _ = video_plan(path, s.video_live_fps, s.video_live_max_frames)
frame = None
for i, (t, f) in enumerate(iter_timed_frames(path, fps, step, s.video_live_max_frames, s.video_frame_max_side)):
    if i == want:
        frame = f
        break
if frame is None:
    raise SystemExit("no such frame")

r = det._empty.predict(frame, conf=0.01, imgsz=s.infer_imgsz, classes=det._empty_ids, verbose=False)[0]
boxes = sorted(zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()), key=lambda z: -z[1])[:15]
out = frame.copy()
print(f"frame {want} t={t:.1f}s {frame.shape[1]}x{frame.shape[0]} | empty.pt raw candidates (conf >= 0.01): {len(r.boxes)}")
for k, (b, c) in enumerate(boxes):
    print(f"  #{k + 1} conf {c:.2f} ({int(b[0])},{int(b[1])},{int(b[2])},{int(b[3])})")
    cv2.rectangle(out, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 0, 255), 2)
    cv2.putText(out, str(k + 1), (int(b[0]) + 3, int(b[1]) + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
cv2.imwrite("empty_raw.jpg", out)
print("saved empty_raw.jpg (red numbers = raw candidates, strongest first)")