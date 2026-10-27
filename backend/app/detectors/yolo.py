import threading

import numpy as np

from app.config import Settings
from app.constants import ERR_NO_EMPTY_CLASS, ERR_WEIGHTS_MISSING

from .base import Box, Detection

EMPTY_CLASS_NAME = "empty"


def _to_boxes(result) -> list[Box]:  # ultralytics Results
    coords = result.boxes.xyxy.cpu().numpy()
    return [Box(float(x1), float(y1), float(x2), float(y2)) for x1, y1, x2, y2 in coords]


class YoloDetector:
    """Two models: SKU-110K for products, the shelf model for empty slots."""

    name = "yolo"

    def __init__(self, settings: Settings) -> None:
        from ultralytics import YOLO  # lazy import keeps mock mode light

        for path in (settings.product_weights, settings.empty_weights):
            if not path.exists():
                raise FileNotFoundError(ERR_WEIGHTS_MISSING.format(path=path))

        self._settings = settings
        self._product = YOLO(str(settings.product_weights))
        self._empty = YOLO(str(settings.empty_weights))
        # The shelf model also has a 'product' class, so predict only 'empty'.
        empty_ids = [i for i, n in self._empty.names.items() if n == EMPTY_CLASS_NAME]
        if not empty_ids:
            raise ValueError(ERR_NO_EMPTY_CLASS)
        self._empty_ids = empty_ids
        self._lock = threading.Lock()  # one prediction at a time per process

    def detect(self, image: np.ndarray) -> Detection:
        height, width = image.shape[:2]
        s = self._settings
        with self._lock:
            product = self._product.predict(
                image,
                conf=s.product_conf,
                iou=s.product_iou,
                imgsz=s.infer_imgsz,
                max_det=s.product_max_det,
                verbose=False,
            )[0]
            empty = self._empty.predict(
                image,
                conf=s.empty_conf,
                imgsz=s.infer_imgsz,
                classes=self._empty_ids,
                verbose=False,
            )[0]
        return Detection(
            width=width,
            height=height,
            products=_to_boxes(product),
            empties=_to_boxes(empty),
        )