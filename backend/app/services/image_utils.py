import cv2
import numpy as np

from app.constants import SHARPNESS_MAX_SIDE
from app.errors import InvalidImageError


def decode_image(data: bytes) -> np.ndarray:
    array = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)  # honours EXIF rotation
    if image is None or image.size == 0:
        raise InvalidImageError()
    return image


def sharpness(image: np.ndarray) -> float:
    """Variance of the Laplacian on a normalised size. Low value means blurry."""
    height, width = image.shape[:2]
    scale = SHARPNESS_MAX_SIDE / max(height, width)
    if scale < 1:
        image = cv2.resize(image, (int(width * scale), int(height * scale)))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())