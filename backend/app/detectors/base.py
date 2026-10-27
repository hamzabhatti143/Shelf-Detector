from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


@dataclass(frozen=True, slots=True)
class Box:
    """Pixel coordinates, xyxy. conf is the detector's confidence (1.0 when unknown)."""

    x1: float
    y1: float
    x2: float
    y2: float
    conf: float = 1.0

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2


@dataclass(frozen=True, slots=True)
class Detection:
    width: int
    height: int
    products: list[Box] = field(default_factory=list)
    empties: list[Box] = field(default_factory=list)


class Detector(Protocol):
    name: str

    def detect(self, image: np.ndarray) -> Detection:
        """image: BGR uint8 array (H, W, 3)."""
        ...