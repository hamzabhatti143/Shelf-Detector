import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

import numpy as np
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.constants import (
    API_PREFIX,
    CONTENT_TYPE_EXT,
    DEFAULT_IMAGE_EXT,
    EMPTY_BOTTOM_TOLERANCE,
    EMPTY_ROW_OVERLAP_MIN,
    ERR_UNKNOWN_STORE,
    ISSUE_DETAIL_EMPTY,
    ISSUE_NOTE_POSSIBLE,
    ISSUE_PREFIX_POSSIBLE,
    ISSUE_TITLE_EMPTY,
    LARGE_GAP_FACINGS,
    MIN_ROW_PRODUCTS,
    NEIGHBOR_BOTTOM_TOLERANCE,
    NEIGHBOR_MIN_OVERLAP,
    NEIGHBOR_REACH,
    ROW_TOLERANCE_FACTOR,
    STORES,
    UNIT_PLURAL,
    UNIT_SINGULAR,
    IssueType,
    Severity,
)
from app.detectors.base import Box, Detection, Detector
from app.errors import ImageTooBlurryError, UnknownStoreError
from app.repository import AuditRepository
from app.schemas import AuditReport, BoundingBox, PriceTagInfo, ShelfIssue
from app.services.image_utils import decode_image, sharpness
from app.services.price_tags import PriceTagReading, TagReader

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ShelfRow:
    index: int  # 1 = top shelf
    top: float
    bottom: float
    median_h: float
    median_w: float
    cy: float


def group_rows(products: list[Box]) -> list[ShelfRow]:
    """Cluster product boxes into shelf rows by vertical centre."""
    clusters: list[list[Box]] = []
    for box in sorted(products, key=lambda b: b.cy):
        if clusters:
            current = clusters[-1]
            tolerance = ROW_TOLERANCE_FACTOR * median(b.height for b in current)
            if abs(box.cy - mean(b.cy for b in current)) <= tolerance:
                current.append(box)
                continue
        clusters.append([box])

    rows: list[ShelfRow] = []
    for cluster in clusters:
        if len(cluster) < MIN_ROW_PRODUCTS:
            continue
        rows.append(
            ShelfRow(
                index=len(rows) + 1,
                top=median(b.y1 for b in cluster),
                bottom=median(b.y2 for b in cluster),
                median_h=median(b.height for b in cluster),
                median_w=median(b.width for b in cluster),
                cy=mean(b.cy for b in cluster),
            )
        )
    return rows


def match_empty(empty: Box, rows: list[ShelfRow]) -> ShelfRow | None:
    """A real empty slot sits on a shelf board between products, so it overlaps a
    product row vertically and its bottom lines up with that row's bottom.
    Headroom above products fails both checks."""
    if empty.height <= 0:
        return None
    best: ShelfRow | None = None
    best_ratio = 0.0
    for row in rows:
        overlap = min(empty.y2, row.bottom) - max(empty.y1, row.top)
        ratio = overlap / empty.height
        aligned = abs(empty.y2 - row.bottom) <= EMPTY_BOTTOM_TOLERANCE * row.median_h
        if ratio >= EMPTY_ROW_OVERLAP_MIN and aligned and ratio > best_ratio:
            best, best_ratio = row, ratio
    return best


def has_shelf_neighbors(empty: Box, products: list[Box]) -> bool:
    """True when a product sits just left or right of the gap at the same shelf level.
    Local check, so it also works on tilted shelves where global rows fail."""
    if not products or empty.height <= 0:
        return False
    unit = median(b.width for b in products)
    reach = NEIGHBOR_REACH * max(empty.width, unit)
    for b in products:
        if b.height <= 0:
            continue
        overlap = min(empty.y2, b.y2) - max(empty.y1, b.y1)
        if overlap < NEIGHBOR_MIN_OVERLAP * min(empty.height, b.height):
            continue
        if abs(empty.y2 - b.y2) > NEIGHBOR_BOTTOM_TOLERANCE * b.height:
            continue
        gap = max(b.x1 - empty.x2, empty.x1 - b.x2)
        if -0.25 * unit <= gap <= reach:
            return True
    return False


def _nearest_row_index(empty: Box, rows: list[ShelfRow]) -> int:
    if not rows:
        return 1
    return min(rows, key=lambda r: abs(r.cy - empty.cy)).index


def _pct(value: float) -> float:
    return round(min(max(value * 100.0, 0.0), 100.0), 2)


def to_percent_box(box: Box, width: int, height: int) -> BoundingBox:
    x, y = _pct(box.x1 / width), _pct(box.y1 / height)
    return BoundingBox(
        x=x,
        y=y,
        w=min(_pct(box.width / width), round(100.0 - x, 2)),
        h=min(_pct(box.height / height), round(100.0 - y, 2)),
    )


def build_issues(detection: Detection, settings: Settings) -> list[ShelfIssue]:
    rows = group_rows(detection.products)
    global_width = median(b.width for b in detection.products) if detection.products else 0.0

    kept: list[tuple[Box, ShelfRow | None]] = []
    for empty in detection.empties:
        row = match_empty(empty, rows)
        local = has_shelf_neighbors(empty, detection.products)
        if settings.filter_headroom_empty and row is None and not local and not settings.keep_unmatched_empty:
            continue
        kept.append((empty, row))

    ranked = sorted(
        kept,
        key=lambda item: (
            item[1].index if item[1] else _nearest_row_index(item[0], rows),
            item[0].x1,
        ),
    )

    issues: list[ShelfIssue] = []
    for number, (empty, row) in enumerate(ranked, start=1):
        unit_width = row.median_w if row else global_width
        facings = max(1, round(empty.width / unit_width)) if unit_width > 0 else 1
        unit = UNIT_SINGULAR if facings == 1 else UNIT_PLURAL
        shelf = row.index if row else _nearest_row_index(empty, rows)

        confirmed = empty.conf >= settings.empty_confirm_conf
        if not confirmed:
            severity = Severity.LOW
        elif facings >= LARGE_GAP_FACINGS:
            severity = Severity.HIGH
        else:
            severity = Severity.MEDIUM
        title = ISSUE_TITLE_EMPTY.format(facings=facings, unit=unit)
        detail = ISSUE_DETAIL_EMPTY.format(facings=facings, unit=unit, shelf=shelf)
        if not confirmed:
            title = ISSUE_PREFIX_POSSIBLE + title
            detail += ISSUE_NOTE_POSSIBLE

        issues.append(
            ShelfIssue(
                id=f"i{number}",
                type=IssueType.OUT_OF_STOCK,
                severity=severity,
                title=title,
                detail=detail,
                shelf=shelf,
                box=to_percent_box(empty, detection.width, detection.height),
            )
        )
    return issues


class AuditService:
    def __init__(
        self,
        detector: Detector,
        settings: Settings,
        tag_reader: TagReader | None = None,
    ) -> None:
        self._detector = detector
        self._settings = settings
        self._tag_reader = tag_reader

    @property
    def detector(self) -> Detector:
        return self._detector

    @property
    def detector_name(self) -> str:
        return self._detector.name

    @staticmethod
    def store_name_for(store_id: str) -> str:
        store_name = STORES.get(store_id)
        if store_name is None:
            raise UnknownStoreError(ERR_UNKNOWN_STORE.format(store_id=store_id))
        return store_name

    def read_tags(self, image: np.ndarray, *, ocr: bool = True, budget_s: float | None = None) -> list[PriceTagReading]:
        """A failing OCR step must never break the audit itself."""
        if self._tag_reader is None:
            return []
        try:
            return self._tag_reader.read(image, ocr=ocr, budget_s=budget_s)
        except Exception:
            logger.exception("price tag reading failed")
            return []

    async def create(
        self,
        session: AsyncSession,
        image_bytes: bytes,
        content_type: str | None,
        store_id: str,
    ) -> AuditReport:
        self.store_name_for(store_id)

        image = await run_in_threadpool(decode_image, image_bytes)
        if self._settings.min_sharpness > 0:
            score = await run_in_threadpool(sharpness, image)
            if score < self._settings.min_sharpness:
                raise ImageTooBlurryError()

        started = time.perf_counter()
        detection = await run_in_threadpool(self._detector.detect, image)
        price_tags = await run_in_threadpool(self.read_tags, image)
        elapsed = time.perf_counter() - started
        return await self.finalize(
            session, image_bytes, content_type, store_id, detection, elapsed, price_tags=price_tags
        )

    async def finalize(
        self,
        session: AsyncSession,
        image_bytes: bytes,
        content_type: str | None,
        store_id: str,
        detection: Detection,
        elapsed: float,
        frames_analyzed: int | None = None,
        price_tags: list[PriceTagReading] | None = None,
    ) -> AuditReport:
        store_name = self.store_name_for(store_id)
        issues = build_issues(detection, self._settings)

        audit_id = f"aud_{uuid.uuid4().hex[:10]}"
        image_path = await self._store_image(audit_id, image_bytes, content_type)
        report = AuditReport(
            id=audit_id,
            store_name=store_name,
            created_at=datetime.now(timezone.utc),
            duration_sec=round(elapsed, 1),
            products_detected=len(detection.products),
            issues=issues,
            is_demo=self._detector.name == "mock",
            image_url=f"{API_PREFIX}/audits/{audit_id}/image",
            frames_analyzed=frames_analyzed,
            product_boxes=[
                to_percent_box(box, detection.width, detection.height) for box in detection.products
            ],
            price_tags=[
                PriceTagInfo(
                    box=to_percent_box(tag.box, detection.width, detection.height),
                    text=tag.text,
                    price=tag.price,
                    confidence=round(tag.box.conf, 2),
                )
                for tag in (price_tags or [])
            ],
        )
        await AuditRepository(session).add(report, store_id, str(image_path))
        return report

    async def _store_image(self, audit_id: str, data: bytes, content_type: str | None) -> Path:
        ext = CONTENT_TYPE_EXT.get(content_type or "", DEFAULT_IMAGE_EXT)
        path = self._settings.upload_dir / f"{audit_id}{ext}"
        await run_in_threadpool(path.write_bytes, data)
        return path