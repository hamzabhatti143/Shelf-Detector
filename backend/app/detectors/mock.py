import numpy as np

from .base import Box, Detection

ROW_TOPS = (0.08, 0.38, 0.68)
ROW_HEIGHT = 0.22
PRODUCT_WIDTH = 0.07
PRODUCT_STEP = 0.085
X_START = 0.02
X_END = 0.98
# row index -> (x1, x2) of an empty gap, as fractions of image width
GAPS: dict[int, tuple[float, float]] = {0: (0.14, 0.30), 1: (0.40, 0.50)}
# Headroom false alarm above the first row. The pipeline must filter it out.
HEADROOM = (0.50, 0.0, 0.70, 0.05)


class MockDetector:
    name = "mock"

    def detect(self, image: np.ndarray) -> Detection:
        height, width = image.shape[:2]
        products: list[Box] = []
        empties: list[Box] = []

        for row, top in enumerate(ROW_TOPS):
            y1, y2 = top * height, (top + ROW_HEIGHT) * height
            gap = GAPS.get(row)
            x = X_START
            while x + PRODUCT_WIDTH <= X_END:
                blocked = gap is not None and x < gap[1] and x + PRODUCT_WIDTH > gap[0]
                if not blocked:
                    products.append(Box(x * width, y1, (x + PRODUCT_WIDTH) * width, y2))
                x += PRODUCT_STEP
            if gap is not None:
                empties.append(Box(gap[0] * width, y1, gap[1] * width, y2))

        hx1, hy1, hx2, hy2 = HEADROOM
        empties.append(Box(hx1 * width, hy1 * height, hx2 * width, hy2 * height))
        return Detection(width=width, height=height, products=products, empties=empties)