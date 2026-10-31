import logging
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.config import Settings
from app.detectors.base import Box, Detection
from app.detectors.fusion import iou_one_to_many
from app.services.audit_service import build_issues
from app.services.camera_service import CameraError, _shrink, describe

logger = logging.getLogger(__name__)

_STREAM_FPS = 12.0  # pictures per second sent to the browser
_STREAM_SIDE = 960  # longest side of the streamed picture
_RECONNECT_WAIT_S = 3.0


def _pct(b: Box, width: int, height: int) -> list[float]:
    return [
        round(b.x1 / width * 100, 1),
        round(b.y1 / height * 100, 1),
        round(b.width / width * 100, 1),
        round(b.height / height * 100, 1),
    ]


def _stable_empties(history: deque, current: list[Box], need: int = 2, iou_thr: float = 0.4) -> list[Box]:
    """A fixed camera sees the same spot every time, so an empty slot must show up in at
    least `need` of the last few detections. One-frame flickers are dropped."""
    kept: list[Box] = []
    for box in current:
        arr = np.array([box.x1, box.y1, box.x2, box.y2], dtype=float)
        seen = 1
        for past in history:
            if past:
                others = np.array([[b.x1, b.y1, b.x2, b.y2] for b in past], dtype=float)
                if iou_one_to_many(arr, others).max() >= iou_thr:
                    seen += 1
        if seen >= need:
            kept.append(box)
    history.append(current)
    return kept


def _keep_known_prices(old: list[list], new: list[list]) -> list[list]:
    """A price tag does not move, so a tag that could not be read this time keeps the price
    read earlier at (almost) the same place."""
    merged = []
    for x, y, w, h, text in new:
        if not text:
            for ox, oy, ow, oh, otext in old:
                if otext and abs(ox + ow / 2 - (x + w / 2)) <= max(w, ow) and abs(oy + oh / 2 - (y + h / 2)) <= max(h, oh):
                    text = otext
                    break
        merged.append([x, y, w, h, text])
    return merged


@dataclass(frozen=True, slots=True)
class LiveResult:
    frame_id: int
    width: int
    height: int
    boxes: list[list[float]]  # products, [x, y, w, h] in % of the frame
    issues: list[dict]  # same shape as the issues of a saved report


class LiveCamera:
    """Reads one camera continuously. One thread keeps the latest picture, one runs the
    detector about once a second, one reads price tags now and then (a fixed camera sees the
    same tags every time). Stops by itself when nobody asks for it for a while."""

    def __init__(self, source: str, detector, settings: Settings, read_tags: Callable) -> None:
        self.id = uuid.uuid4().hex[:16]
        self._source = source
        self._detector = detector
        self._read_tags = read_tags
        self._s = settings
        try:
            self._is_file = Path(source).is_file()
        except (OSError, ValueError):
            self._is_file = False
        self._stop = threading.Event()
        self._first = threading.Event()
        self._lock = threading.Lock()
        self._frame_id = 0
        self._frame: np.ndarray | None = None
        self._stream_jpeg: bytes | None = None
        self._result: LiveResult | None = None
        self._tags: list[list] = []
        self.error: str | None = None
        self.last_access = time.monotonic()
        for target in (self._read_loop, self._detect_loop, self._tag_loop):
            threading.Thread(target=target, daemon=True, name=f"cam-{self.id}").start()

    @property
    def alive(self) -> bool:
        return not self._stop.is_set()

    def touch(self) -> None:
        self.last_access = time.monotonic()

    def stop(self) -> None:
        self._stop.set()

    def wait_first_frame(self, timeout: float) -> bool:
        return self._first.wait(timeout)

    def stream_frame(self) -> tuple[int, bytes] | None:
        with self._lock:
            return (self._frame_id, self._stream_jpeg) if self._stream_jpeg else None

    def result(self) -> LiveResult | None:
        with self._lock:
            return self._result

    def tags(self) -> list[list]:
        with self._lock:
            return list(self._tags)

    def full_jpeg(self) -> bytes | None:
        """The latest picture at full quality, for an audit."""
        with self._lock:
            frame = self._frame
        if frame is None:
            return None
        ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        return buffer.tobytes() if ok else None

    def _idle(self) -> bool:
        return time.monotonic() - self.last_access > self._s.camera_live_idle_s

    def _open(self) -> cv2.VideoCapture | None:
        ms = int(self._s.camera_timeout_s * 1000)
        cap = cv2.VideoCapture(
            self._source, cv2.CAP_FFMPEG, [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, ms, cv2.CAP_PROP_READ_TIMEOUT_MSEC, ms]
        )
        if cap.isOpened():
            return cap
        cap.release()
        return None

    def _publish(self, frame: np.ndarray) -> None:
        frame = _shrink(frame, self._s.video_frame_max_side)
        ok, buffer = cv2.imencode(".jpg", _shrink(frame, _STREAM_SIDE), [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if not ok:
            return
        with self._lock:
            self._frame_id += 1
            self._frame = frame
            self._stream_jpeg = buffer.tobytes()
        self.error = None
        self._first.set()

    def _read_loop(self) -> None:
        min_gap = 1.0 / _STREAM_FPS
        while not self._stop.is_set():
            cap = self._open()
            if cap is None:
                self.error = f"Could not open the camera ({describe(self._source)})."
                self._stop.wait(_RECONNECT_WAIT_S)
                continue
            file_delay = 1.0 / (cap.get(cv2.CAP_PROP_FPS) or 25.0) if self._is_file else 0.0
            last = 0.0
            rewinds = 0
            try:
                while not self._stop.is_set():
                    if self._idle():
                        self.stop()
                        return
                    if not cap.grab():
                        if self._is_file and rewinds < 3:  # a video file stands in for a camera: loop it
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            rewinds += 1
                            continue
                        break
                    rewinds = 0
                    if file_delay:
                        self._stop.wait(file_delay)
                    now = time.monotonic()
                    if now - last < min_gap:
                        continue
                    ok, frame = cap.retrieve()
                    if ok and frame is not None:
                        last = now
                        self._publish(frame)
            finally:
                cap.release()
            self.error = "Lost the camera picture, reconnecting."
            self._stop.wait(_RECONNECT_WAIT_S)

    def _detect_loop(self) -> None:
        last_id = 0
        history: deque = deque(maxlen=2)
        while not self._stop.is_set():
            if self._idle():
                self.stop()
                return
            with self._lock:
                frame_id, frame = self._frame_id, self._frame
            if frame is None or frame_id == last_id:
                self._stop.wait(0.2)
                continue
            last_id = frame_id
            started = time.monotonic()
            try:
                detection = self._detector.detect(frame)
                height, width = frame.shape[:2]
                stable = Detection(
                    detection.width, detection.height, detection.products,
                    _stable_empties(history, detection.empties),
                )
                issues = [issue.model_dump(mode="json", by_alias=True) for issue in build_issues(stable, self._s)]
            except Exception:
                logger.exception("live detection failed")
                self._stop.wait(2.0)
                continue
            result = LiveResult(frame_id, width, height, [_pct(b, width, height) for b in stable.products], issues)
            with self._lock:
                self._result = result
            self._stop.wait(max(0.0, self._s.camera_live_detect_every_s - (time.monotonic() - started)))

    def _tag_loop(self) -> None:
        min_conf = self._s.video_tag_min_conf
        while not self._stop.is_set():
            if self._idle():
                self.stop()
                return
            with self._lock:
                frame = self._frame
            if frame is not None:
                try:
                    readings = self._read_tags(frame, ocr=True, budget_s=self._s.camera_live_tag_budget_s)
                except Exception:
                    logger.exception("live tag reading failed")
                    readings = []
                height, width = frame.shape[:2]
                fresh = []
                for r in readings:
                    readable = sum(c.isdigit() for c in r.text) >= 2 and r.ocr_confidence >= min_conf
                    fresh.append([*_pct(r.box, width, height), r.text if readable else ""])
                with self._lock:
                    self._tags = _keep_known_prices(self._tags, fresh)
            self._stop.wait(self._s.camera_live_tags_every_s)


class CameraLiveManager:
    def __init__(self, detector, settings: Settings, read_tags: Callable) -> None:
        self._detector = detector
        self._s = settings
        self._read_tags = read_tags
        self._cams: dict[str, LiveCamera] = {}
        self._lock = threading.Lock()

    def _prune(self) -> None:
        for cid in [cid for cid, cam in self._cams.items() if not cam.alive]:
            del self._cams[cid]

    def start(self, source: str) -> LiveCamera:
        with self._lock:
            self._prune()
            if len(self._cams) >= self._s.camera_live_max:
                raise CameraError("Too many live cameras are running. Stop one first.", 429)
            cam = LiveCamera(source, self._detector, self._s, self._read_tags)
            self._cams[cam.id] = cam
            return cam

    def get(self, cid: str) -> LiveCamera | None:
        with self._lock:
            cam = self._cams.get(cid)
        if cam is not None and cam.alive:
            cam.touch()
            return cam
        return None

    def stop(self, cid: str) -> None:
        with self._lock:
            cam = self._cams.pop(cid, None)
        if cam is not None:
            cam.stop()

    def stop_all(self) -> None:
        with self._lock:
            cams, self._cams = list(self._cams.values()), {}
        for cam in cams:
            cam.stop()