from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.services.camera_live import CameraLiveManager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.api.video_routes import router as video_router
from app.config import get_settings
from app.constants import APP_TITLE, APP_VERSION
from app.db import dispose_db, init_db
from app.detectors.factory import build_detector
from app.errors import AppError
from app.services.audit_service import AuditService
from app.services.price_tags import build_tag_reader
from app.services.video_service import VideoAuditService
from app.api.video_live_routes import router as video_live_router
from app.api.camera_routes import router as camera_router
import os

# RTSP over TCP is far more reliable than UDP; must be set before OpenCV opens its first capture
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp|stimeout;8000000")

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    await init_db()
    audit_service = AuditService(
        build_detector(settings), settings, build_tag_reader(settings)
    )
    app.state.audit_service = audit_service
    app.state.video_service = VideoAuditService(audit_service, settings)
    app.state.camera_live = CameraLiveManager(audit_service.detector, settings, audit_service.read_tags)
    yield
    app.state.camera_live.stop_all()
    await dispose_db()


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(router)
app.include_router(video_router)
app.include_router(video_live_router)
app.include_router(camera_router)