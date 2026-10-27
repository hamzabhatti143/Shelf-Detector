import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

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


class VideoAuditService:
    def __init__(self, audit_service: AuditService, settings: Settings) -> None:
        self._audit = audit_service
        self._settings = settings
        self.jobs = JobStore()

    async def process(self, job_id: str, video_path: Path, store_id: str) -> None:
        job = self.jobs.get(job_id)
        if job is None:
            return
        s = self._settings
        try:
            job.status = JobStatus.PROCESSING
            frames = await run_in_threadpool(
                sample_frames, video_path, s.video_max_frames, s.video_frame_max_side
            )
            if not frames:
                raise InvalidVideoError()

            started = time.perf_counter()
            detections: list[Detection] = []
            for i, frame in enumerate(frames):
                detections.append(await run_in_threadpool(self._audit.detector.detect, frame))
                job.progress = (i + 1) / (len(frames) + 1)

            index, detection = pick_best_frame(detections, s)
            price_tags = await run_in_threadpool(self._audit.read_tags, frames[index])
            ok, buffer = cv2.imencode(".jpg", frames[index])
            if not ok:
                raise InvalidVideoError()
            elapsed = time.perf_counter() - started

            async with SessionLocal() as session:
                report = await self._audit.finalize(
                    session, buffer.tobytes(), "image/jpeg", store_id, detection, elapsed,
                    frames_analyzed=len(frames),
                    price_tags=price_tags,
                )
            job.audit_id = report.id
            job.progress = 1.0
            job.status = JobStatus.DONE
        except AppError as exc:
            job.status, job.error = JobStatus.FAILED, exc.message
        except Exception:
            logger.exception("video job %s failed", job_id)
            job.status, job.error = JobStatus.FAILED, ERR_JOB_FAILED
        finally:
            await run_in_threadpool(lambda: video_path.unlink(missing_ok=True))