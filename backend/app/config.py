from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./shelfsight.db"
    detector: Literal["mock", "yolo", "ensemble"] = "mock"

    # ensemble pipeline
    product_scales: list[int] = [480, 640, 960]
    scale_conf: float = 0.25
    scale_min_votes: int = 2
    scale_solo_conf: float = 0.55
    fuse_iou: float = 0.55
    empty_low_conf: float = 0.10
    empty_confirm_conf: float = 0.40
    empty_max_product_overlap: float = 0.30
    
    product_weights: Path = Path("weights/product.pt")
    empty_weights: Path = Path("weights/empty.pt")
    product_conf: float = 0.30
    product_iou: float = 0.5
    product_max_det: int = 1000
    empty_conf: float = 0.40
    infer_imgsz: int = 640

    max_upload_mb: int = 10
    min_sharpness: float = 0.0  # 0 = blur check off
    filter_headroom_empty: bool = True
    keep_unmatched_empty: bool = False

    upload_dir: Path = Path("uploads")
    cors_origins: list[str] = ["http://localhost:3000"]

    max_video_mb: int = 100
    video_max_frames: int = 12
    video_frame_max_side: int = 1600
    video_min_seen: int = 2
    video_track_iou: float = 0.3

    price_tags: bool = False
    pricetag_weights: Path = Path("weights/pricetag.pt")
    pricetag_conf: float = 0.30
    pricetag_imgsz: int = 960
    pricetag_max_det: int = 200
    pricetag_max_reads: int = 60
    ocr_languages: list[str] = ["en"]
    ocr_min_conf: float = 0.30
    ocr_gpu: bool = False
    ocr_allowlist: str = "0123456789.,\u066b\u066c٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹$€£¥₹"

    @property
    def max_video_bytes(self) -> int:
        return self.max_video_mb * 1024 * 1024

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()