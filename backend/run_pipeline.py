import shutil
import statistics
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

from app.config import get_settings
from app.detectors.base import Box
from app.detectors.ensemble import EnsembleDetector
from app.detectors.fusion import iou_one_to_many
from app.services.audit_service import build_issues, group_rows, has_shelf_neighbors, match_empty

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
OUT_DIR = Path("pipeline_out")
MAX_SAVE_SIDE = 1600
MAX_VIDEO_SIDE = 1280
GREEN, RED, BLUE, PURPLE = (0, 200, 0), (0, 0, 255), (255, 0, 0), (200, 0, 200)
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
PRODUCT_THICKNESS_SCALE = 2
EMPTY_EXTRA_THICKNESS = 2

DEFAULT_STRIDE = 5
HISTORY = 3        # kitne sampled frames dekhe jayein (current + pichle HISTORY-1)
MIN_SEEN = 2       # kam az kam itne mein dikhna chahiye
TRACK_IOU = 0.3
PROGRESS_EVERY = 100
VALUE_FLAGS = {"--stride", "--seconds"}


def get_option(name: str, cast, default):
    if name in sys.argv:
        index = sys.argv.index(name)
        try:
            return cast(sys.argv[index + 1])
        except (IndexError, ValueError):
            print(f"{name} ki value galat hai, default {default} use ho raha hai")
    return default


def positional_args() -> list[str]:
    result, skip = [], False
    for arg in sys.argv[1:]:
        if skip:
            skip = False
        elif arg in VALUE_FLAGS:
            skip = True
        elif not arg.startswith("--"):
            result.append(arg)
    return result


def collect_media(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(p for p in target.iterdir() if p.suffix.lower() in IMAGE_EXTS | VIDEO_EXTS)


def rect(img, box, color, thickness) -> None:
    cv2.rectangle(img, (int(box.x1), int(box.y1)), (int(box.x2), int(box.y2)), color, thickness)


def thicknesses(width: int, height: int, products: list[Box]) -> tuple[int, int]:
    base = max(1, round(max(height, width) / 700))
    median_w = statistics.median(b.width for b in products) if products else 50
    # chhoti image par boxes dhundhle na ho jayein, isliye motai box ke size se bhi bandhi hai
    product_thick = max(1, min(base * PRODUCT_THICKNESS_SCALE, int(median_w // 5)))
    return product_thick, product_thick + EMPTY_EXTRA_THICKNESS


def classify_empties(detection, info, settings) -> list[tuple[Box, str, str]]:
    """Har empty candidate ke liye (box, status, reason). status: confirmed, possible, rejected."""
    rows = group_rows(detection.products)
    results: list[tuple[Box, str, str]] = []
    for verdict in info.verdicts:
        box = verdict.box
        if not verdict.kept:
            results.append((box, "rejected", verdict.reason))
            continue
        geometry_ok = bool(match_empty(box, rows)) or has_shelf_neighbors(box, detection.products)
        if settings.filter_headroom_empty and not geometry_ok and not settings.keep_unmatched_empty:
            results.append((box, "rejected", "no shelf neighbors (headroom?)"))
            continue
        if box.conf >= settings.empty_confirm_conf:
            results.append((box, "confirmed", "CONFIRMED"))
        else:
            results.append((box, "possible", "possible (low confidence)"))
    return results


# ---------------------------------------------------------------- photo

def run_one(path: Path, detector: EnsembleDetector, settings, debug: bool):
    img = cv2.imread(str(path))
    if img is None:
        print(f"{path.name}: image nahi padhi gayi")
        return None

    started = time.perf_counter()
    detection, info = detector.detect_debug(img)
    elapsed = time.perf_counter() - started
    classified = classify_empties(detection, info, settings)
    issues = build_issues(detection, settings)

    height, width = img.shape[:2]
    product_thick, empty_thick = thicknesses(width, height, detection.products)

    print(f"\n{path.name} ({width}x{height}) | detect time {elapsed:.1f}s")
    scales = " ".join(f"{size}:{n}" for size, n in info.per_scale_counts.items())
    print(f"  product passes: {scales} -> fused {info.fused_products}")
    print(f"  empty candidates (conf >= {settings.empty_low_conf}): {len(info.verdicts)}")

    for box in detection.products:
        rect(img, box, GREEN, product_thick)

    confirmed = possible = rejected = 0
    for number, (box, status, reason) in enumerate(classified, start=1):
        coords = f"({box.x1:.0f},{box.y1:.0f},{box.x2:.0f},{box.y2:.0f})"
        if status == "rejected":
            rejected += 1
            if debug:
                rect(img, box, BLUE, empty_thick)
            print(f"    #{number} conf {box.conf:.2f} {coords} -> rejected: {reason}")
            continue
        if status == "confirmed":
            confirmed += 1
        else:
            possible += 1
        rect(img, box, RED, empty_thick)
        print(f"    #{number} conf {box.conf:.2f} {coords} -> {reason}")
    print(f"  issues in report: {len(issues)}")

    scale = MAX_SAVE_SIDE / max(height, width)
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale)
    OUT_DIR.mkdir(exist_ok=True)
    cv2.imwrite(str(OUT_DIR / f"{path.stem}_out.jpg"), img)
    return path.name, info.fused_products, confirmed, possible, rejected


# ---------------------------------------------------------------- video

def stable_empties(current: list[Box], history: deque) -> list[Box]:
    """Wo boxes rakho jo pichle sampled frames mein bhi (kam az kam MIN_SEEN-1 mein) mile hon."""
    stable: list[Box] = []
    for box in current:
        arr = np.array([box.x1, box.y1, box.x2, box.y2], dtype=float)
        seen = 0
        for past in history:
            if not past:
                continue
            past_arr = np.array([[b.x1, b.y1, b.x2, b.y2] for b in past], dtype=float)
            if iou_one_to_many(arr, past_arr).max() >= TRACK_IOU:
                seen += 1
        if seen + 1 >= MIN_SEEN:
            stable.append(box)
    return stable


def to_h264(raw: Path, final: Path) -> bool:
    """ffmpeg ho to browser-friendly mp4 banao, warna raw file hi final bana do."""
    if shutil.which("ffmpeg") is not None:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
               "-vcodec", "libx264", "-pix_fmt", "yuv420p", str(final)]
        if subprocess.run(cmd).returncode == 0:
            raw.unlink()
            return True
    raw.replace(final)
    return False


def run_video(path: Path, detector: EnsembleDetector, settings, stride: int,
              seconds: float, debug: bool, smooth: bool) -> None:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        print(f"{path.name}: video nahi khuli")
        return
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    limit = int(seconds * fps) if seconds > 0 else None

    out_scale = min(1.0, MAX_VIDEO_SIDE / max(width, height))
    out_size = (int(width * out_scale), int(height * out_scale))
    OUT_DIR.mkdir(exist_ok=True)
    raw_path = OUT_DIR / f"{path.stem}_raw.mp4"
    final_path = OUT_DIR / f"{path.stem}_out.mp4"
    best_path = OUT_DIR / f"{path.stem}_best.jpg"
    writer = cv2.VideoWriter(str(raw_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, out_size)

    font = max(0.7, max(width, height) / 1500)
    font_thick = max(1, int(font * 2))

    print(f"\n{path.name} ({width}x{height}, {fps:.0f} fps, {total} frames) | stride {stride}"
          f"{f', pehle {seconds:g}s' if limit else ''} | smoothing {'on' if smooth else 'off'}")

    products: list[Box] = []
    drawn: list[Box] = []
    rejected_draw: list[Box] = []
    history: deque = deque(maxlen=HISTORY - 1)
    detect_times: list[float] = []
    stable_counts: list[int] = []
    best_count, best_frame = -1, None
    index = 0
    started_all = time.perf_counter()

    while True:
        ok, frame = cap.read()
        if not ok or (limit is not None and index >= limit):
            break

        sampled = index % stride == 0
        if sampled:
            t0 = time.perf_counter()
            detection, info = detector.detect_debug(frame)
            detect_times.append(time.perf_counter() - t0)
            classified = classify_empties(detection, info, settings)
            kept = [box for box, status, _ in classified if status != "rejected"]
            drawn = stable_empties(kept, history) if smooth else kept
            history.append(kept)
            products = detection.products
            rejected_draw = [box for box, status, _ in classified if status == "rejected"] if debug else []
            stable_counts.append(len(drawn))

        product_thick, empty_thick = thicknesses(width, height, products)
        for box in products:
            rect(frame, box, GREEN, product_thick)
        for box in rejected_draw:
            rect(frame, box, BLUE, empty_thick)
        for box in drawn:
            rect(frame, box, RED, empty_thick)
        label = f"products: {len(products)} | empty: {len(drawn)}"
        cv2.putText(frame, label, (20, int(40 * font)), cv2.FONT_HERSHEY_SIMPLEX, font, BLACK, font_thick + 3)
        cv2.putText(frame, label, (20, int(40 * font)), cv2.FONT_HERSHEY_SIMPLEX, font, WHITE, font_thick)

        out_frame = cv2.resize(frame, out_size) if out_scale < 1 else frame
        writer.write(out_frame)
        if sampled and len(drawn) > best_count:
            best_count, best_frame = len(drawn), out_frame.copy()

        index += 1
        if index % PROGRESS_EVERY == 0:
            print(f"  frame {index}/{total or '?'} | avg detect {statistics.mean(detect_times):.1f}s")

    cap.release()
    writer.release()
    if best_frame is not None:
        cv2.imwrite(str(best_path), best_frame)
    encoded = to_h264(raw_path, final_path)

    wall = time.perf_counter() - started_all
    print(f"\nframes read: {index} | detections: {len(detect_times)} | total time {wall:.0f}s")
    if detect_times:
        print(f"detect time per sampled frame: avg {statistics.mean(detect_times):.1f}s, "
              f"max {max(detect_times):.1f}s")
        print(f"empty boxes per sampled frame: max {max(stable_counts)}, "
              f"avg {statistics.mean(stable_counts):.1f}")
    print(f"video: {final_path}{'' if encoded else '  (ffmpeg nahi mila, mp4v format; VLC mein chalao)'}")
    if best_frame is not None:
        print(f"best frame: {best_path}")


# ---------------------------------------------------------------- main

def main() -> None:
    args = positional_args()
    if not args:
        print("usage: python run_pipeline.py <image|video|folder> [--debug] [--stride N] [--seconds S] [--no-smooth]")
        return
    debug = "--debug" in sys.argv
    smooth = "--no-smooth" not in sys.argv
    stride = max(1, get_option("--stride", int, DEFAULT_STRIDE))
    seconds = get_option("--seconds", float, 0.0)

    settings = get_settings()
    detector = EnsembleDetector(settings)

    summary = []
    for media in collect_media(Path(args[0])):
        if media.suffix.lower() in VIDEO_EXTS:
            run_video(media, detector, settings, stride, seconds, debug, smooth)
        else:
            result = run_one(media, detector, settings, debug)
            if result:
                summary.append(result)

    if summary:
        legend = "hara = product | laal = empty (confirmed + possible)"
        if debug:
            legend += " | neela/jamni = reject"
        print(f"\nlegend: {legend}")
        print(f"\n{'photo':28} {'products':>9} {'confirmed':>10} {'possible':>9} {'rejected':>9}")
        for name, n_prod, n_conf, n_poss, n_rej in summary:
            print(f"{name[:28]:28} {n_prod:>9} {n_conf:>10} {n_poss:>9} {n_rej:>9}")
    print(f"\nannotated files: {OUT_DIR}/")


if __name__ == "__main__":
    main()