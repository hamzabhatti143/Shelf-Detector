import sys
from pathlib import Path

import cv2
import numpy as np

from app.config import get_settings
from app.detectors.factory import build_detector
from app.services.video_service import sample_frames

s = get_settings()
path = Path(sys.argv[1])
cap = cv2.VideoCapture(str(path))
fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
print(
    "video:", int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), "x", int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    "| fps", round(cap.get(cv2.CAP_PROP_FPS), 1), "| frames", int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
    "| codec", "".join(chr((fourcc >> 8 * i) & 255) for i in range(4)),
    "| orientation meta", cap.get(cv2.CAP_PROP_ORIENTATION_META), "| auto", cap.get(cv2.CAP_PROP_ORIENTATION_AUTO),
)
cap.release()

out = Path("probe_frames")
out.mkdir(exist_ok=True)
frames = sample_frames(path, s.video_max_frames, s.video_frame_max_side)
print("sampled frames:", len(frames))
detector = build_detector(s)


def flat_rows(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float((gray.std(axis=1) < 3).mean())  # share of rows that are one flat colour


for i, f in enumerate(frames):
    h, w = f.shape[:2]
    cv2.imwrite(str(out / f"{i:02d}.jpg"), f)
    d = detector.detect(f)
    on_flat = 0
    for b in d.products:
        crop = f[max(0, int(b.y1)):int(b.y2), max(0, int(b.x1)):int(b.x2)]
        if crop.size and cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).std() < 3:
            on_flat += 1
    print(
        f"frame {i:02d}: {w}x{h} | flat rows {flat_rows(f) * 100:.0f}% | products {len(d.products)}"
        f" (on flat colour: {on_flat}) | max box bottom {max([b.y2 for b in d.products] or [0]) / h * 100:.0f}% of height"
    )
print("frames saved in probe_frames/ (open one: is the bottom gray?)")