from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.constants import IssueType, JobStatus, Severity


class CamelModel(BaseModel):
    """Serialises to camelCase to match the Next.js types in lib/types.ts."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class BoundingBox(CamelModel):
    x: float  # all values are percentages (0-100) of image width/height
    y: float
    w: float
    h: float


class ShelfIssue(CamelModel):
    id: str
    type: IssueType
    severity: Severity
    title: str
    detail: str
    shelf: int
    box: BoundingBox

class PriceTagInfo(CamelModel):
    box: BoundingBox
    text: str
    price: float | None
    confidence: float

class AuditReport(CamelModel):
    id: str
    store_name: str
    created_at: datetime
    duration_sec: float
    products_detected: int
    issues: list[ShelfIssue]
    is_demo: bool
    image_url: str | None = None
    frames_analyzed: int | None = None
    product_boxes: list[BoundingBox] = Field(default_factory=list)
    price_tags: list[PriceTagInfo] = Field(default_factory=list)


class AuditSummary(CamelModel):
    id: str
    store_name: str
    created_at: datetime
    issue_count: int


class StatItem(CamelModel):
    label: str
    value: str
    hint: str


class IssueBreakdownItem(CamelModel):
    type: IssueType
    count: int


class DashboardStats(CamelModel):
    stats: list[StatItem]
    breakdown: list[IssueBreakdownItem]


class StoreOption(CamelModel):
    id: str
    name: str


class HealthStatus(CamelModel):
    status: str
    detector: str

class VideoJob(CamelModel):
    job_id: str
    status: JobStatus
    progress: float
    audit_id: str | None = None
    error: str | None = None