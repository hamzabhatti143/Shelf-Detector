import asyncio
import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlsplit

import cv2
import numpy as np
from fastapi.concurrency import run_in_threadpool

from app.config import Settings

_SCHEMES = {"rtsp", "rtsps", "http", "https"}
_FRAMES_TO_READ = 15  # the first frames of a stream are often stale or grey; keep the last good one


class CameraError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def describe(source: str) -> str:
    """The camera address without its login, safe to show and log."""
    parts = urlsplit(source)
    if parts.hostname:
        try:
            return parts.hostname + (f":{parts.port}" if parts.port else "")
        except ValueError:
            return parts.hostname
    return Path(source).name


def _check_host(host: str) -> None:
    """Store cameras live on the local network, so private addresses are fine. Loopback and
    link-local (cloud metadata lives there) are refused, so this field cannot be used to poke
    at the server itself."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise CameraError("Could not find that camera address. Check the IP or name.") from None
    for info in infos:
        ip = ipaddress.ip_address(str(info[4][0]).split("%")[0])
        if ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast:
            raise CameraError("That address is not allowed. Use the camera's address on your network.")


def validate_source(url: str, settings: Settings) -> str:
    source = url.strip()
    if not source or len(source) > 2000:
        raise CameraError("Enter the camera address.")
    if settings.camera_allow_files:
        try:
            if Path(source).is_file():
                return source
        except (OSError, ValueError):
            pass
    parts = urlsplit(source)
    if parts.scheme.lower() not in _SCHEMES or not parts.hostname:
        raise CameraError("Use an rtsp:// or http:// camera address.")
    _check_host(parts.hostname)
    return source


def _grab(source: str, timeout_ms: int) -> np.ndarray:
    cap = cv2.VideoCapture(
        source,
        cv2.CAP_FFMPEG,
        [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms, cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms],
    )
    if not cap.isOpened():
        raise CameraError(
            f"Could not open the camera ({describe(source)}). Check the address and login, "
            "and that the camera is on the same network as this server."
        )
    frame = None
    try:
        for _ in range(_FRAMES_TO_READ):
            ok, current = cap.read()
            if ok and current is not None:
                frame = current
            elif frame is not None:
                break
    finally:
        cap.release()
    if frame is None:
        raise CameraError("Connected to the camera, but no picture arrived.")
    return frame


def _shrink(frame: np.ndarray, max_side: int) -> np.ndarray:
    height, width = frame.shape[:2]
    scale = max_side / max(height, width)
    if scale >= 1:
        return frame
    return cv2.resize(frame, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)


async def grab_jpeg(url: str, settings: Settings) -> bytes:
    """One current picture from the camera, as JPEG bytes."""
    source = await run_in_threadpool(validate_source, url, settings)
    timeout_ms = int(settings.camera_timeout_s * 1000)
    try:
        frame = await asyncio.wait_for(
            run_in_threadpool(_grab, source, timeout_ms), timeout=settings.camera_timeout_s * 2 + 5
        )
    except asyncio.TimeoutError:
        raise CameraError("The camera did not answer in time.", 504) from None
    frame = _shrink(frame, settings.video_frame_max_side)
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        raise CameraError("Could not process the picture.", 500)
    return buffer.tobytes()