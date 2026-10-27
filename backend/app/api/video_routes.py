import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile

from app.api.routes import get_audit_service
from app.config import Settings, get_settings
from app.constants import (
    API_PREFIX,
    DEFAULT_VIDEO_EXT,
    ERR_VIDEO_TOO_LARGE,
    UPLOAD_CHUNK_BYTES,
    VIDEO_CONTENT_TYPE_EXT,
    VIDEO_TMP_DIR,
)
from app.errors import JobNotFoundError, PayloadTooLargeError, UnsupportedVideoError
from app.schemas import VideoJob
from app.services.audit_service import AuditService
from app.services.video_service import VideoAuditService, VideoJobState

VIDEO_EXTENSIONS = frozenset(VIDEO_CONTENT_TYPE_EXT.values())
router = APIRouter(prefix=API_PREFIX)


def get_video_service(request: Request) -> VideoAuditService:
    return request.app.state.video_service


VideoServiceDep = Annotated[VideoAuditService, Depends(get_video_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _to_schema(job: VideoJobState) -> VideoJob:
    return VideoJob(
        job_id=job.job_id,
        status=job.status,
        progress=round(job.progress, 3),
        audit_id=job.audit_id,
        error=job.error,
    )


async def _save_upload(file: UploadFile, dest: Path, max_bytes: int, max_mb: int) -> None:
    """Stream to disk in chunks so a 100 MB video never sits in memory."""
    total = 0
    try:
        with dest.open("wb") as out:
            while chunk := await file.read(UPLOAD_CHUNK_BYTES):
                total += len(chunk)
                if total > max_bytes:
                    raise PayloadTooLargeError(ERR_VIDEO_TOO_LARGE.format(limit_mb=max_mb))
                out.write(chunk)
    except Exception:
        dest.unlink(missing_ok=True)
        raise


@router.post("/video-audits", response_model=VideoJob, status_code=202)
async def create_video_audit(
    background_tasks: BackgroundTasks,
    video: Annotated[UploadFile, File()],
    store_id: Annotated[str, Form()],
    audit_service: AuditServiceDep,
    video_service: VideoServiceDep,
    settings: SettingsDep,
) -> VideoJob:
    audit_service.store_name_for(store_id)
    suffix = Path(video.filename or "").suffix.lower()
    content_type = video.content_type or ""
    if not (content_type.startswith("video/") or suffix in VIDEO_EXTENSIONS):
        raise UnsupportedVideoError()

    tmp_dir = settings.upload_dir / VIDEO_TMP_DIR
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ext = VIDEO_CONTENT_TYPE_EXT.get(content_type) or (suffix if suffix in VIDEO_EXTENSIONS else DEFAULT_VIDEO_EXT)
    path = tmp_dir / f"{uuid.uuid4().hex}{ext}"
    await _save_upload(video, path, settings.max_video_bytes, settings.max_video_mb)

    job = video_service.jobs.create()
    background_tasks.add_task(video_service.process, job.job_id, path, store_id)
    return _to_schema(job)


@router.get("/video-audits/{job_id}", response_model=VideoJob)
async def get_video_audit(job_id: str, video_service: VideoServiceDep) -> VideoJob:
    job = video_service.jobs.get(job_id)
    if job is None:
        raise JobNotFoundError()
    return _to_schema(job)