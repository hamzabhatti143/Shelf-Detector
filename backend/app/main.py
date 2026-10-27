from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from app.services.price_tags import build_tag_reader
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
from app.services.video_service import VideoAuditService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    await init_db()
    audit_service = AuditService(build_detector(settings), settings)
    app.state.audit_service = audit_service
    app.state.video_service = VideoAuditService(audit_service, settings)
    yield
    await dispose_db()
    audit_service = AuditService(build_detector(settings), settings, build_tag_reader(settings))


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