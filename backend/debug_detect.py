import statistics
import sys

import cv2

from app.config import get_settings
from app.detectors.factory import build_detector
from app.services.audit_service import build_issues, group_rows, has_shelf_neighbors, match_empty

path = sys.argv[1]
settings = get_settings()
detector = build_detector(settings)

img = cv2.imread(path)
assert img is not None, "image nahi mili, path check karo"
d = detector.detect(img)
rows = group_rows(d.products)

print("image:", d.width, "x", d.height)
print("products:", len(d.products), "| shelf rows found:", len(rows))
if d.products:
    print(f"median product: {statistics.median(b.width for b in d.products):.0f} x "
          f"{statistics.median(b.height for b in d.products):.0f} px")
print("raw empty boxes:", len(d.empties))

kept_flags = []
for e in d.empties:
    r = match_empty(e, rows)
    local = has_shelf_neighbors(e, d.products)
    kept_flags.append(bool(r) or local)
    print(f"  empty ({e.x1:.0f},{e.y1:.0f},{e.x2:.0f},{e.y2:.0f}) size {e.width:.0f}x{e.height:.0f}"
          f" | row: {'shelf ' + str(r.index) if r else 'no'} | local neighbors: {local}")
print("issues kept:", len(build_issues(d, settings)))

for b in d.products:
    cv2.rectangle(img, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), (0, 255, 0), 1)
for e, keep in zip(d.empties, kept_flags):
    color = (0, 0, 255) if keep else (255, 0, 0)   # laal = rakha gaya, neela = filter ne hataya
    cv2.rectangle(img, (int(e.x1), int(e.y1)), (int(e.x2), int(e.y2)), color, 3)
cv2.imwrite("debug_out.jpg", img)
print("saved: debug_out.jpg")