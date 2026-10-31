import mimetypes
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.services.video_service import VIDEO_LIVE_DIR

router = APIRouter(prefix="/v1")  # same prefix as the other routes
_AUDIT_ID = re.compile(r"^aud_[0-9a-f]{10}$")


def _folder(audit_id: str):
    if not _AUDIT_ID.fullmatch(audit_id):
        raise HTTPException(status_code=404, detail="Not found.")
    return get_settings().upload_dir / VIDEO_LIVE_DIR


@router.get("/audits/{audit_id}/timeline")
async def get_timeline(audit_id: str) -> FileResponse:
    path = _folder(audit_id) / f"{audit_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="No live view for this audit.")
    return FileResponse(path, media_type="application/json", headers={"Cache-Control": "no-store"})


@router.get("/audits/{audit_id}/video")
async def get_video(audit_id: str) -> FileResponse:
    folder = _folder(audit_id)
    for path in folder.glob(f"{audit_id}.*"):
        if path.suffix.lower() != ".json" and path.is_file():
            return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or "video/mp4")
    raise HTTPException(status_code=404, detail="No video for this audit.")