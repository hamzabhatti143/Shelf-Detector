import sys
from pathlib import Path

import cv2

from app.config import get_settings
from app.detectors.factory import build_detector
from app.services.audit_service import AuditService
from app.services.price_tags import build_tag_reader
from app.services.video_service import iter_timed_frames, video_plan

s = get_settings()
path = Path(sys.argv[1])
every = int(sys.argv[2]) if len(sys.argv) > 2 else 5  # annotate every Nth sampled frame
fps, step, expected = video_plan(path, s.video_live_fps, s.video_live_max_frames)
print(f"video fps {fps:.1f} | step {step} frames = every {step / fps:.2f}s | frames {expected}")

audit = AuditService(build_detector(s), s, build_tag_reader(s))
out = Path("still_check")
out.mkdir(exist_ok=True)
for f in out.glob("*.jpg"):
    f.unlink()

for i, (t, frame) in enumerate(iter_timed_frames(path, fps, step, s.video_live_max_frames, s.video_frame_max_side)):
    if i % every:
        continue
    det = audit.detector.detect(frame)
    tags = audit.read_tags(frame, ocr=False)
    img = frame.copy()
    for b in det.products:
        cv2.rectangle(img, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), (60, 220, 60), 2)
    for r in tags:
        cv2.rectangle(img, (int(r.box.x1), int(r.box.y1)), (int(r.box.x2), int(r.box.y2)), (255, 160, 0), 2)
    cv2.imwrite(str(out / f"{i:02d}_t{t:.1f}s.jpg"), img)
    print(f"frame {i:02d} t={t:.1f}s | {frame.shape[1]}x{frame.shape[0]} | products {len(det.products)} | tags {len(tags)}")
print("saved in still_check/ (green = product, blue = tag)")