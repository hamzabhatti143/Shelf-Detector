from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditRow
from app.schemas import AuditReport


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, report: AuditReport, store_id: str, image_path: str | None) -> None:
        self._session.add(
            AuditRow(
                id=report.id,
                store_id=store_id,
                store_name=report.store_name,
                created_at=report.created_at,
                issue_count=len(report.issues),
                report=report.model_dump(mode="json", by_alias=True),
                image_path=image_path,
            )
        )
        await self._session.commit()

    async def get(self, audit_id: str) -> AuditRow | None:
        return await self._session.get(AuditRow, audit_id)

    async def list_recent(self, limit: int) -> Sequence[AuditRow]:
        result = await self._session.execute(
            select(AuditRow).order_by(AuditRow.created_at.desc()).limit(limit)
        )
        return result.scalars().all()

    async def since(self, cutoff: datetime) -> Sequence[AuditRow]:
        result = await self._session.execute(
            select(AuditRow).where(AuditRow.created_at >= cutoff)
        )
        return result.scalars().all()