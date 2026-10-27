from app.config import Settings

from .base import Detector
from .mock import MockDetector

def build_detector(settings: Settings) -> Detector:
    if settings.detector == "ensemble":
        from .ensemble import EnsembleDetector

        return EnsembleDetector(settings)
    if settings.detector == "yolo":
        from .yolo import YoloDetector

        return YoloDetector(settings)
    return MockDetector()