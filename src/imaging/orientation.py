from __future__ import annotations

from collections.abc import Callable

import cv2
import numpy as np
from PIL import Image, ImageOps


def read_with_exif(path: str) -> np.ndarray:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def rotate_quarter_turn(image: np.ndarray, angle: int) -> np.ndarray:
    normalized = angle % 360
    if normalized == 0:
        return image.copy()
    if normalized == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if normalized == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if normalized == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    raise ValueError("只支持 0/90/180/270 度旋转")


def auto_orient(image: np.ndarray, text_score: Callable[[np.ndarray], float] | None = None) -> tuple[np.ndarray, int]:
    """用 OCR 可读性选择方向；无 OCR 时仅保持 EXIF 校正后的方向。"""
    if text_score is None:
        return image.copy(), 0
    candidates = [(angle, rotate_quarter_turn(image, angle)) for angle in (0, 90, 180, 270)]
    angle, best = max(candidates, key=lambda item: text_score(item[1]))
    return best, angle

