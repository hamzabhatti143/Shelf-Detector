from dataclasses import dataclass

import numpy as np

from app.constants import EMPTY_DEDUP_IOU

from .base import Box, Detection
from .fusion import EmptyVerdict, filter_empties, fuse_scales, verify_empties
from .yolo import YoloDetector


@dataclass(frozen=True, slots=True)
class EnsembleDebug:
    per_scale_counts: dict[int, int]
    fused_products: int
    verdicts: list[EmptyVerdict]


def _boxes_with_conf(result) -> list[Box]:  # ultralytics Results
    xyxy = result.boxes.xyxy.cpu().numpy()
    conf = result.boxes.conf.cpu().numpy()
    return [
        Box(float(a), float(b), float(c), float(d), float(p))
        for (a, b, c, d), p in zip(xyxy, conf)
    ]


class EnsembleDetector(YoloDetector):
    """Same two models as YoloDetector, but with multi-scale product fusion and
    a second opinion (the product boxes) on every empty candidate."""

    name = "ensemble"

    def detect(self, image: np.ndarray) -> Detection:
        return self.detect_debug(image)[0]

    def detect_debug(self, image: np.ndarray) -> tuple[Detection, EnsembleDebug]:
        height, width = image.shape[:2]
        s = self._settings
        with self._lock:
            per_scale: list[list[Box]] = []
            for size in s.product_scales:
                result = self._product.predict(
                    image,
                    conf=s.scale_conf,
                    iou=s.product_iou,
                    imgsz=size,
                    max_det=s.product_max_det,
                    verbose=False,
                )[0]
                per_scale.append(_boxes_with_conf(result))
            empty_result = self._empty.predict(
                image,
                conf=s.empty_low_conf,
                imgsz=s.infer_imgsz,
                classes=self._empty_ids,
                verbose=False,
            )[0]

        products = fuse_scales(per_scale, s.fuse_iou, s.scale_min_votes, s.scale_solo_conf)
        verdicts = verify_empties(
            _boxes_with_conf(empty_result), products, s.empty_max_product_overlap, EMPTY_DEDUP_IOU
        )
        verdicts = filter_empties(verdicts, products, width, height)
        debug = EnsembleDebug(
            per_scale_counts={size: len(boxes) for size, boxes in zip(s.product_scales, per_scale)},
            fused_products=len(products),
            verdicts=verdicts,
        )
        empties = [v.box for v in verdicts if v.kept]
        return Detection(width=width, height=height, products=products, empties=empties), debug