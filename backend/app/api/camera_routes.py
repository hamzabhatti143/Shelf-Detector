import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_session
from app.schemas import AuditReport
from app.services.audit_service import AuditService
from app.services.camera_live import CameraLiveManager, LiveCamera
from app.services.camera_service import CameraError, describe, grab_jpeg, validate_source

router = APIRouter(prefix="/v1")  # same prefix as the other routes

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _service(request: Request) -> AuditService:
    return request.app.state.audit_service


def _manager(request: Request) -> CameraLiveManager:
    return request.app.state.camera_live


ServiceDep = Annotated[AuditService, Depends(_service)]
ManagerDep = Annotated[CameraLiveManager, Depends(_manager)]


class CameraRequest(BaseModel):
    url: str = Field(max_length=2000)


class CameraAuditRequest(CameraRequest):
    store_id: str


class LiveAuditRequest(BaseModel):
    store_id: str


def _http(exc: CameraError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


def _live(manager: CameraLiveManager, cid: str) -> LiveCamera:
    cam = manager.get(cid)
    if cam is None:
        raise HTTPException(status_code=404, detail="This live view has ended. Start it again.")
    return cam


@router.post("/cameras/test")
async def test_camera(body: CameraRequest, settings: SettingsDep) -> Response:
    """One picture from the camera, so the user can check the connection before auditing."""
    try:
        jpeg = await grab_jpeg(body.url, settings)
    except CameraError as exc:
        raise _http(exc) from None
    return Response(content=jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/camera-audits", response_model=AuditReport, status_code=status.HTTP_201_CREATED)
async def create_camera_audit(
    body: CameraAuditRequest, session: SessionDep, service: ServiceDep, settings: SettingsDep
) -> AuditReport:
    """A normal shelf audit on a fresh picture from the camera."""
    try:
        jpeg = await grab_jpeg(body.url, settings)
    except CameraError as exc:
        raise _http(exc) from None
    report = await service.create(session, jpeg, "image/jpeg", body.store_id)
    await session.commit()  # saved before the page asks for it
    return report


@router.post("/cameras/live", status_code=status.HTTP_201_CREATED)
async def start_live(body: CameraRequest, manager: ManagerDep, settings: SettingsDep) -> dict[str, str]:
    try:
        source = await run_in_threadpool(validate_source, body.url, settings)
        cam = manager.start(source)
    except CameraError as exc:
        raise _http(exc) from None
    if not await run_in_threadpool(cam.wait_first_frame, settings.camera_timeout_s * 2):
        manager.stop(cam.id)
        raise HTTPException(
            status_code=400,
            detail=f"Could not get a picture from the camera ({describe(source)}). "
            "Check the address and login, and that it is on the same network as this server.",
        )
    return {"id": cam.id}


@router.get("/cameras/live/{cid}/stream")
async def live_stream(cid: str, request: Request, manager: ManagerDep) -> StreamingResponse:
    cam = _live(manager, cid)

    async def frames():
        last = 0
        while cam.alive and not await request.is_disconnected():
            cam.touch()
            item = cam.stream_frame()
            if item is not None and item[0] != last:
                last = item[0]
                head = f"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: {len(item[1])}\r\n\r\n"
                yield head.encode() + item[1] + b"\r\n"
            await asyncio.sleep(0.04)

    return StreamingResponse(
        frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/cameras/live/{cid}/boxes")
async def live_boxes(cid: str, manager: ManagerDep) -> dict:
    cam = _live(manager, cid)
    result = cam.result()
    if result is None:
        return {"ready": False, "error": cam.error}
    return {
        "ready": True,
        "error": cam.error,
        "width": result.width,
        "height": result.height,
        "boxes": result.boxes,
        "issues": result.issues,
        "tags": cam.tags(),
    }


@router.post("/cameras/live/{cid}/audit", response_model=AuditReport, status_code=status.HTTP_201_CREATED)
async def audit_live(
    cid: str,
    body: LiveAuditRequest,
    manager: ManagerDep,
    session: SessionDep,
    service: ServiceDep,
) -> AuditReport:
    """An audit on the latest live picture (no second connection to the camera)."""
    jpeg = await run_in_threadpool(_live(manager, cid).full_jpeg)
    if jpeg is None:
        raise HTTPException(status_code=409, detail="No picture from the camera yet.")
    report = await service.create(session, jpeg, "image/jpeg", body.store_id)
    await session.commit()
    return report


@router.delete("/cameras/live/{cid}", status_code=status.HTTP_204_NO_CONTENT)
async def stop_live(cid: str, manager: ManagerDep) -> Response:
    manager.stop(cid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)