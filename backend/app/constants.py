from enum import StrEnum
from typing import Final

APP_TITLE: Final = "ShelfSight API"
APP_VERSION: Final = "0.1.0"
API_PREFIX: Final = "/v1"

DEFAULT_LIST_LIMIT: Final = 25
MAX_LIST_LIMIT: Final = 200
UPLOAD_CHUNK_BYTES: Final = 1024 * 1024
SHARPNESS_MAX_SIDE: Final = 1024
STATS_WINDOW_DAYS: Final = 7

# Mirrors STORE_OPTIONS in the Next.js lib/config.ts
STORES: Final[dict[str, str]] = {
    "clifton": "Al-Noor Mart, Clifton",
    "gulshan": "Al-Noor Mart, Gulshan",
    "dha": "Al-Noor Mart, DHA Phase 6",
}

CONTENT_TYPE_EXT: Final[dict[str, str]] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
DEFAULT_IMAGE_EXT: Final = ".jpg"


class IssueType(StrEnum):
    OUT_OF_STOCK = "out_of_stock"
    WRONG_PLACEMENT = "wrong_placement"
    PRICE_MISMATCH = "price_mismatch"


class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Shelf-analysis heuristics (tune on real photos)
MIN_ROW_PRODUCTS: Final = 2
ROW_TOLERANCE_FACTOR: Final = 0.5
EMPTY_ROW_OVERLAP_MIN: Final = 0.5
EMPTY_BOTTOM_TOLERANCE: Final = 0.35
LARGE_GAP_FACINGS: Final = 2

# Issue text
ISSUE_TITLE_EMPTY: Final = "Empty slot, about {facings} {unit} missing"
ISSUE_DETAIL_EMPTY: Final = (
    "A gap of roughly {facings} product {unit} was found on shelf {shelf}. "
    "Check stock and restock if needed."
)
UNIT_SINGULAR: Final = "facing"
UNIT_PLURAL: Final = "facings"

# Errors
ERR_INVALID_IMAGE: Final = "The uploaded file could not be read as an image."
ERR_NOT_IMAGE: Final = "Please upload an image file."
ERR_TOO_LARGE: Final = "Image is larger than {limit_mb} MB."
ERR_BLURRY: Final = "The photo is too blurry. Please retake it."
ERR_UNKNOWN_STORE: Final = "Unknown store_id: {store_id}."
ERR_AUDIT_NOT_FOUND: Final = "Audit not found."
ERR_IMAGE_NOT_FOUND: Final = "No image stored for this audit."
ERR_WEIGHTS_MISSING: Final = "Model weights not found: {path}"
ERR_NO_EMPTY_CLASS: Final = "The empty-shelf model has no class named 'empty'."

# Dashboard labels (match the frontend's sample data)
STAT_AUDITS: Final = "Audits this week"
STAT_AUDITS_HINT: Final = "Last 7 days"
STAT_STOCKOUTS: Final = "Stock-outs found"
STAT_STOCKOUTS_HINT: Final = "Across {stores} stores"
STAT_PRICE: Final = "Price mismatches"
STAT_PRICE_HINT: Final = "Tag vs system price"
STAT_TIME: Final = "Avg. audit time"
STAT_TIME_HINT: Final = "Photo to report"
NEIGHBOR_REACH: Final = 3.0
NEIGHBOR_BOTTOM_TOLERANCE: Final = 0.5
NEIGHBOR_MIN_OVERLAP: Final = 0.5
EMPTY_DEDUP_IOU: Final = 0.45
REASON_KEPT: Final = "kept"
REASON_DUPLICATE: Final = "duplicate of a stronger box"
REASON_COVERED: Final = "covered {pct:.0f}% by products"
ISSUE_PREFIX_POSSIBLE: Final = "Possible: "
ISSUE_NOTE_POSSIBLE: Final = " Low confidence, please check the shelf."
class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


VIDEO_CONTENT_TYPE_EXT: Final[dict[str, str]] = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "video/x-matroska": ".mkv",
}
DEFAULT_VIDEO_EXT: Final = ".mp4"
VIDEO_TMP_DIR: Final = "tmp"
MAX_JOBS_KEPT: Final = 50
VIDEO_FALLBACK_STEP: Final = 15

ERR_NOT_VIDEO: Final = "Please upload a video file."
ERR_INVALID_VIDEO: Final = "The uploaded file could not be read as a video."
ERR_VIDEO_TOO_LARGE: Final = "Video is larger than {limit_mb} MB."
ERR_JOB_NOT_FOUND: Final = "Video job not found."
ERR_JOB_FAILED: Final = "Video analysis failed. Please try again."
OCR_ALLOWLIST: Final = "0123456789.,$"
OCR_MIN_CROP_HEIGHT: Final = 96
OCR_CROP_PAD: Final = 10
TAG_CROP_MARGIN: Final = 0.05
PRICE_MIN: Final = 0.0
PRICE_MAX: Final = 1_000_000.0
PRICETAG_CLASS_TAG: Final = "price-tags"
PRICETAG_CLASS_PRICE: Final = "price-tag-price"
PRICE_INSIDE_TAG_MIN: Final = 0.6
SUPERSCRIPT_MAX_HEIGHT_RATIO: Final = 0.8
ERR_NO_PRICETAG_CLASS: Final = "The price-tag model has no class named '{name}'. Classes found: {names}"