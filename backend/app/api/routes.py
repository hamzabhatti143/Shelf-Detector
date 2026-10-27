from pathlib import Path
from typing import Annotated
from datetime import timezone
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.constants import (
    API_PREFIX,
    DEFAULT_LIST_LIMIT,
    ERR_TOO_LARGE,
    MAX_LIST_LIMIT,
    STORES,
    UPLOAD_CHUNK_BYTES,
)
from app.db import get_session
from app.errors import (
    AuditNotFoundError,
    ImageNotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaError,
)
from app.repository import AuditRepository
from app.schemas import (
    AuditReport,
    AuditSummary,
    DashboardStats,
    HealthStatus,
    StoreOption,
)
from app.services.audit_service import AuditService
from app.services.stats_service import build_dashboard_stats

router = APIRouter()
v1 = APIRouter(prefix=API_PREFIX)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_audit_service(request: Request) -> AuditService:
    return request.app.state.audit_service


ServiceDep = Annotated[AuditService, Depends(get_audit_service)]


async def _read_upload(file: UploadFile, max_bytes: int, max_mb: int) -> bytes:
    if not (file.content_type or "").startswith("image/"):
        raise UnsupportedMediaError()
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(UPLOAD_CHUNK_BYTES):
        total += len(chunk)
        if total > max_bytes:
            raise PayloadTooLargeError(ERR_TOO_LARGE.format(limit_mb=max_mb))
        chunks.append(chunk)
    return b"".join(chunks)


@router.get("/health", response_model=HealthStatus)
async def health(service: ServiceDep) -> HealthStatus:
    return HealthStatus(status="ok", detector=service.detector_name)


@v1.get("/stores", response_model=list[StoreOption])
async def list_stores() -> list[StoreOption]:
    return [StoreOption(id=store_id, name=name) for store_id, name in STORES.items()]


@v1.post("/audits", response_model=AuditReport, status_code=status.HTTP_201_CREATED)
async def create_audit(
    image: Annotated[UploadFile, File()],
    store_id: Annotated[str, Form()],
    session: SessionDep,
    service: ServiceDep,
    settings: SettingsDep,
) -> AuditReport:
    data = await _read_upload(image, settings.max_upload_bytes, settings.max_upload_mb)
    return await service.create(session, data, image.content_type, store_id)


@v1.get("/audits", response_model=list[AuditSummary])
async def list_audits(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=MAX_LIST_LIMIT)] = DEFAULT_LIST_LIMIT,
) -> list[AuditSummary]:
    rows = await AuditRepository(session).list_recent(limit)
    return [
        AuditSummary(
            id=row.id,
            store_name=row.store_name,
            created_at=row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc),
            issue_count=row.issue_count,
        )
        for row in rows
    ]


@v1.get("/audits/{audit_id}", response_model=AuditReport)
async def get_audit(audit_id: str, session: SessionDep) -> AuditReport:
    row = await AuditRepository(session).get(audit_id)
    if row is None:
        raise AuditNotFoundError()
    return AuditReport.model_validate(row.report)


@v1.get("/audits/{audit_id}/image")
async def get_audit_image(audit_id: str, session: SessionDep) -> FileResponse:
    row = await AuditRepository(session).get(audit_id)
    if row is None:
        raise AuditNotFoundError()
    if not row.image_path or not Path(row.image_path).exists():
        raise ImageNotFoundError()
    return FileResponse(row.image_path)


@v1.get("/stats", response_model=DashboardStats)
async def dashboard_stats(session: SessionDep) -> DashboardStats:
    return await build_dashboard_stats(session)


router.include_router(v1)