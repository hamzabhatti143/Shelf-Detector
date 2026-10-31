import sys
from pathlib import Path

import cv2

from app.config import get_settings
from app.detectors.factory import build_detector
from app.services.video_service import iter_timed_frames, video_plan

s = get_settings()
path = Path(sys.argv[1])
every = int(sys.argv[2]) if len(sys.argv) > 2 else 3
det = build_detector(s)
if not hasattr(det, "detect_debug"):
    raise SystemExit("DETECTOR must be 'ensemble' (set it in .env)")
fps, step, _ = video_plan(path, s.video_live_fps, s.video_live_max_frames)
out = Path("empty_check")
out.mkdir(exist_ok=True)
for f in out.glob("*.jpg"):
    f.unlink()

for i, (t, frame) in enumerate(iter_timed_frames(path, fps, step, s.video_live_max_frames, s.video_frame_max_side)):
    if i % every:
        continue
    d, dbg = det.detect_debug(frame)
    img = frame.copy()
    for b in d.products:
        cv2.rectangle(img, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), (60, 220, 60), 1)
    print(f"frame {i:02d} t={t:.1f}s | products {len(d.products)} | empty candidates {len(dbg.verdicts)}")
    for v in dbg.verdicts:
        b = v.box
        color = (0, 0, 255) if v.kept else (0, 140, 255)  # red = kept, orange = rejected
        cv2.rectangle(img, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), color, 3)
        cv2.putText(img, f"{b.conf:.2f}", (int(b.x1) + 4, int(b.y1) + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        print(f"   conf {b.conf:.2f} ({int(b.x1)},{int(b.y1)},{int(b.x2)},{int(b.y2)}) -> {'KEPT' if v.kept else v.reason}")
    cv2.imwrite(str(out / f"{i:02d}_t{t:.1f}s.jpg"), img)
print("saved in empty_check/ (red = kept empty, orange = rejected, number = confidence)")