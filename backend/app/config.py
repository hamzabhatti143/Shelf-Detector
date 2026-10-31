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
    price_crop_margins: list[float] = [0.25, 0.15, 0.4]
    tag_crop_margins: list[float] = [0.05, 0.15, 0.3]
    scale_min_votes: int = 2
    ocr_workers: int = 4
    ocr_accept_conf: float = 0.95
    ocr_threads: int = 1
    video_live_fps: float = 2.0
    video_live_max_frames: int = 40
    video_keep: int = 20  # newest live videos kept on disk
    pricetag_time_budget_s: float = 6.0
    drop_small_background: bool = True
    video_live_tags: bool = True
    video_tag_ocr_every: int = 3  # OCR prices on every Nth sampled frame
    video_tag_ocr_budget_s: float = 2.0  # OCR time cap per such frame
    contained_cover: float = 0.85  # drop a box this much inside a bigger one; 1.1 turns it off
    small_bg_area_ratio: float = 0.20
    ocr_det_min_side: int = 320
    video_tag_min_conf: float = 0.6
    camera_timeout_s: float = 8.0
    camera_allow_files: bool = False  # dev only: lets the camera field take a video file path on the server
    ocr_engine: Literal["rapidocr", "easyocr"] = "rapidocr"
    scale_solo_conf: float = 0.55
    camera_live_detect_every_s: float = 1.0
    camera_live_idle_s: float = 30.0  # a live camera stops by itself when nobody is watching
    camera_live_max: int = 2
    camera_live_tags_every_s: float = 20.0
    camera_live_tag_budget_s: float = 10.0
    video_tag_min_conf: float = 0.6  # agar pehle se hai to dobara mat daalo
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