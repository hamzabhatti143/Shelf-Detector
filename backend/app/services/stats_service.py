from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    STAT_AUDITS,
    STAT_AUDITS_HINT,
    STAT_PRICE,
    STAT_PRICE_HINT,
    STAT_STOCKOUTS,
    STAT_STOCKOUTS_HINT,
    STAT_TIME,
    STAT_TIME_HINT,
    STATS_WINDOW_DAYS,
    IssueType,
)
from app.repository import AuditRepository
from app.schemas import AuditReport, DashboardStats, IssueBreakdownItem, StatItem


async def build_dashboard_stats(session: AsyncSession) -> DashboardStats:
    cutoff = datetime.now(timezone.utc) - timedelta(days=STATS_WINDOW_DAYS)
    rows = await AuditRepository(session).since(cutoff)
    reports = [AuditReport.model_validate(row.report) for row in rows]

    counts = Counter(issue.type for report in reports for issue in report.issues)
    stores = len({row.store_id for row in rows})
    avg_time = sum(r.duration_sec for r in reports) / len(reports) if reports else 0.0

    stats = [
        StatItem(label=STAT_AUDITS, value=str(len(reports)), hint=STAT_AUDITS_HINT),
        StatItem(
            label=STAT_STOCKOUTS,
            value=str(counts[IssueType.OUT_OF_STOCK]),
            hint=STAT_STOCKOUTS_HINT.format(stores=stores),
        ),
        StatItem(label=STAT_PRICE, value=str(counts[IssueType.PRICE_MISMATCH]), hint=STAT_PRICE_HINT),
        StatItem(label=STAT_TIME, value=f"{avg_time:.0f}s", hint=STAT_TIME_HINT),
    ]
    breakdown = [IssueBreakdownItem(type=t, count=counts[t]) for t in IssueType]
    return DashboardStats(stats=stats, breakdown=breakdown)