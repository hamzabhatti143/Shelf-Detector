import json
import logging
import shutil
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from app.services.price_tags import PriceTagReading
import cv2
import numpy as np
from fastapi.concurrency import run_in_threadpool

from app.config import Settings
from app.constants import (
    ERR_JOB_FAILED,
    MAX_JOBS_KEPT,
    VIDEO_FALLBACK_STEP,
    JobStatus,
)
from app.db import SessionLocal
from app.detectors.base import Box, Detection
from app.detectors.fusion import iou_one_to_many
from app.errors import AppError, InvalidVideoError
from app.services.audit_service import AuditService, build_issues

logger = logging.getLogger(__name__)

VIDEO_LIVE_DIR = "videos"  # under upload_dir: <audit id>.<video ext> + <audit id>.json (timeline)


@dataclass
class VideoJobState:
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    audit_id: str | None = None
    error: str | None = None


class JobStore:
    """In-memory only. Jobs vanish on restart, fine for the MVP."""

    def __init__(self) -> None:
        self._jobs: dict[str, VideoJobState] = {}

    def create(self) -> VideoJobState:
        state = VideoJobState(job_id=f"job_{uuid.uuid4().hex[:10]}")
        self._jobs[state.job_id] = state
        while len(self._jobs) > MAX_JOBS_KEPT:
            self._jobs.pop(next(iter(self._jobs)))
        return state

    def get(self, job_id: str) -> VideoJobState | None:
        return self._jobs.get(job_id)


def _shrink(frame: np.ndarray, max_side: int) -> np.ndarray:
    height, width = frame.shape[:2]
    scale = max_side / max(height, width)
    if scale >= 1:
        return frame
    return cv2.resize(frame, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)


def sample_frames(path: Path, max_frames: int, max_side: int) -> list[np.ndarray]:
    """Evenly spaced frames. Reads sequentially (no seeking), which is more reliable."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step = max(1, total // max_frames) if total > 0 else VIDEO_FALLBACK_STEP
    frames: list[np.ndarray] = []
    index = 0
    try:
        while len(frames) < max_frames:
            if not cap.grab():
                break
            if index % step == step // 2:
                ok, frame = cap.retrieve()
                if ok and frame is not None:
                    frames.append(_shrink(frame, max_side))
            index += 1
    finally:
        cap.release()
    return frames


def video_plan(path: Path, target_fps: float, max_frames: int) -> tuple[float, int, int]:
    """(video fps, frame step, expected number of sampled frames). Expected 0 = unreadable."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return 30.0, 1, 0
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    finally:
        cap.release()
    if not 1.0 <= fps <= 240.0:
        fps = 30.0
    step = max(1, round(fps / max(target_fps, 0.1)))
    if total > 0:
        step = max(step, -(-total // max_frames))  # never more than max_frames samples
        expected = min(max_frames, max(1, total // step))
    else:
        expected = max_frames
    return fps, step, expected

_MOTION_W = 320  # camera motion is tracked on a downscaled copy
_MOTION_HZ = 10.0

def _small_gray(frame: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]
    small = cv2.resize(frame, (_MOTION_W, max(1, round(h * _MOTION_W / w))), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)


def _camera_step(prev: np.ndarray, cur: np.ndarray) -> np.ndarray:
    """3x3 similarity (shift, zoom, small rotation) taking points of `prev` to `cur`; identity when unsure."""
    identity = np.eye(3)
    pts = cv2.goodFeaturesToTrack(prev, maxCorners=250, qualityLevel=0.01, minDistance=6)
    if pts is None or len(pts) < 8:
        return identity
    nxt, status, _ = cv2.calcOpticalFlowPyrLK(prev, cur, pts, None, winSize=(21, 21), maxLevel=3)
    ok = status.ravel() == 1
    if ok.sum() < 8:
        return identity
    m, _ = cv2.estimateAffinePartial2D(pts[ok], nxt[ok], method=cv2.RANSAC, ransacReprojThreshold=3.0)
    return identity if m is None else np.vstack([m, [0.0, 0.0, 1.0]])


def iter_timed_frames(
    path: Path,
    fps: float,
    step: int,
    max_frames: int,
    max_side: int,
    motion: list[list[float]] | None = None,
) -> Iterator[tuple[float, np.ndarray]]:
    """Yields (seconds, frame) one at a time, so frames never pile up in memory.
    When `motion` is given it is filled with [seconds, a, b, tx, ty]: the camera's cumulative
    movement (z' = (a + bi) z + (tx + ty i), in pixels of a 320 px wide copy) about 10 times a second."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return
    motion_step = max(1, round(fps / _MOTION_HZ))
    produced = 0
    index = 0
    prev_gray: np.ndarray | None = None
    cumulative = np.eye(3)
    try:
        while produced < max_frames:
            if not cap.grab():
                break
            want_frame = index % step == step // 2
            want_motion = motion is not None and index % motion_step == 0
            if want_frame or want_motion:
                ok, frame = cap.retrieve()
                if ok and frame is not None:
                    if want_motion and motion is not None:
                        gray = _small_gray(frame)
                        if prev_gray is not None:
                            cumulative = _camera_step(prev_gray, gray) @ cumulative
                        prev_gray = gray
                        motion.append(
                            [
                                round(index / fps, 3),
                                round(float(cumulative[0, 0]), 5),
                                round(float(cumulative[1, 0]), 5),
                                round(float(cumulative[0, 2]), 2),
                                round(float(cumulative[1, 2]), 2),
                            ]
                        )
                    if want_frame:
                        yield index / fps, _shrink(frame, max_side)
                        produced += 1
            index += 1
    finally:
        cap.release()


def stable_empties(per_frame: list[list[Box]], iou_thr: float, min_seen: int) -> list[list[Box]]:
    """Keep an empty box only if a similar box shows up in enough sampled frames.
    One-frame flickers are dropped. This assumes the camera stays roughly still."""
    needed = max(1, min(min_seen, len(per_frame)))
    arrays = [
        np.array([[b.x1, b.y1, b.x2, b.y2] for b in boxes], dtype=float).reshape(-1, 4)
        for boxes in per_frame
    ]
    result: list[list[Box]] = []
    for i, boxes in enumerate(per_frame):
        kept: list[Box] = []
        for box, arr in zip(boxes, arrays[i]):
            seen = 1 + sum(
                1
                for j, other in enumerate(arrays)
                if j != i and other.size and iou_one_to_many(arr, other).max() >= iou_thr
            )
            if seen >= needed:
                kept.append(box)
        result.append(kept)
    return result


def pick_best_frame(detections: list[Detection], settings: Settings) -> tuple[int, Detection]:
    stable = stable_empties(
        [d.empties for d in detections], settings.video_track_iou, settings.video_min_seen
    )
    best_index = 0
    best_score = (-1, -1)
    best_detection = detections[0]
    for index, (detection, empties) in enumerate(zip(detections, stable)):
        candidate = Detection(detection.width, detection.height, detection.products, empties)
        score = (len(build_issues(candidate, settings)), len(detection.products))
        if score > best_score:
            best_index, best_score, best_detection = index, score, candidate
    return best_index, best_detection


def _prune(folder: Path, keep: int) -> None:
    """Keep only the newest `keep` live videos, so the disk does not fill up."""
    stamps = sorted(folder.glob("aud_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in stamps[max(keep, 1):]:
        for leftover in folder.glob(f"{old.stem}.*"):
            leftover.unlink(missing_ok=True)


class VideoAuditService:
    def __init__(self, audit_service: AuditService, settings: Settings) -> None:
        self._audit = audit_service
        self._settings = settings
        self.jobs = JobStore()

    def _keep_live_assets(
        self,
        audit_id: str,
        video_path: Path,
        interval: float,
        times: list[float],
        detections: list[Detection],
        frame_tags: list[list[PriceTagReading]],
        ocr_flags: list[bool],
        motion: list[list[float]],
    ) -> None:
        """Save the video and a per-frame timeline (boxes in % of the frame) for the live view."""
        folder = self._settings.upload_dir / VIDEO_LIVE_DIR
        folder.mkdir(parents=True, exist_ok=True)
        width, height = detections[0].width, detections[0].height

        def pct(b: Box) -> list[float]:
            return [
                round(b.x1 / width * 100, 1),
                round(b.y1 / height * 100, 1),
                round(b.width / width * 100, 1),
                round(b.height / height * 100, 1),
            ]

        def live_text(r: PriceTagReading) -> str:
            digits = sum(c.isdigit() for c in r.text)
            return r.text if digits >= 2 and r.ocr_confidence >= self._settings.video_tag_min_conf else ""

        frames = [
            {
                "t": round(t, 2),
                "boxes": [pct(b) for b in d.products],
                "tags": [[*pct(r.box), live_text(r)] for r in tags],
                "empties": [pct(b) for b in d.empties],
                "ocr": ocr,
            }
            for t, d, tags, ocr in zip(times, detections, frame_tags, ocr_flags)
        ]
        timeline = {
            "width": width,
            "height": height,
            "duration": round(times[-1] + interval, 2),
            "frames": frames,
            "motion": {"w": _MOTION_W, "h": max(1, round(height * _MOTION_W / width)), "samples": motion},
        }
        (folder / f"{audit_id}.json").write_text(json.dumps(timeline), encoding="utf-8")
        shutil.move(str(video_path), str(folder / f"{audit_id}{video_path.suffix.lower()}"))
        _prune(folder, self._settings.video_keep)

    async def process(self, job_id: str, video_path: Path, store_id: str) -> None:
        job = self.jobs.get(job_id)
        if job is None:
            return
        s = self._settings
        frames_iter: Iterator[tuple[float, np.ndarray]] | None = None
        try:
            job.status = JobStatus.PROCESSING
            fps, step, expected = await run_in_threadpool(
                video_plan, video_path, s.video_live_fps, s.video_live_max_frames
            )
            if expected == 0:
                raise InvalidVideoError()
            motion: list[list[float]] = []  # camera movement, filled while the frames are read
            frames_iter = iter_timed_frames(
                video_path, fps, step, s.video_live_max_frames, s.video_frame_max_side, motion
            )

            started = time.perf_counter()
            times: list[float] = []
            jpegs: list[bytes] = []  # frames kept as JPEG, so memory stays small
            detections: list[Detection] = []
            frame_tags: list[list[PriceTagReading]] = []
            ocr_flags: list[bool] = []
            while True:
                item = await run_in_threadpool(next, frames_iter, None)
                if item is None:
                    break
                seconds, frame = item
                detections.append(await run_in_threadpool(self._audit.detector.detect, frame))

                ocr_now = s.video_live_tags and len(times) % max(1, s.video_tag_ocr_every) == 0
                tags_here: list[PriceTagReading] = []
                if s.video_live_tags:
                    tags_here = await run_in_threadpool(
                        lambda f=frame, o=ocr_now: self._audit.read_tags(
                            f, ocr=o, budget_s=s.video_tag_ocr_budget_s
                        )
                    )
                frame_tags.append(tags_here)
                ocr_flags.append(ocr_now)

                ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                if not ok:
                    raise InvalidVideoError()
                times.append(seconds)
                jpegs.append(buffer.tobytes())
                job.progress = min(0.95, len(times) / (expected + 1))
            if not detections:
                raise InvalidVideoError()

            index, detection = pick_best_frame(detections, s)
            best = cv2.imdecode(np.frombuffer(jpegs[index], np.uint8), cv2.IMREAD_COLOR)
            price_tags = await run_in_threadpool(self._audit.read_tags, best)  # full OCR on the best frame
            elapsed = time.perf_counter() - started

            async with SessionLocal() as session:
                report = await self._audit.finalize(
                    session, jpegs[index], "image/jpeg", store_id, detection, elapsed,
                    frames_analyzed=len(detections),
                    price_tags=price_tags,
                )
            try:
                await run_in_threadpool(
                    self._keep_live_assets, report.id, video_path, step / fps,
                    times, detections, frame_tags, ocr_flags, motion,
                )
            except Exception:  # the audit itself is fine; only the live view is missing
                logger.exception("could not keep live assets for %s", report.id)
            job.audit_id = report.id
            job.progress = 1.0
            job.status = JobStatus.DONE
        except AppError as exc:
            job.status, job.error = JobStatus.FAILED, exc.message
        except Exception:
            logger.exception("video job %s failed", job_id)
            job.status, job.error = JobStatus.FAILED, ERR_JOB_FAILED
        finally:
            if frames_iter is not None:
                frames_iter.close()
            await run_in_threadpool(lambda: video_path.unlink(missing_ok=True))