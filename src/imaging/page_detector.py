from __future__ import annotations

import cv2
import numpy as np

from src.imaging.perspective import detect_page_quad


def page_boundary_status(image: np.ndarray) -> tuple[bool, str]:
    quad = detect_page_quad(image)
    if quad is None:
        return False, "A complete page boundary was not detected"
    height, width = image.shape[:2]
    margin = max(4, int(min(height, width) * 0.005))
    touches = bool(
        np.any(quad[:, 0] <= margin)
        or np.any(quad[:, 0] >= width - margin)
        or np.any(quad[:, 1] <= margin)
        or np.any(quad[:, 1] >= height - margin)
    )
    return (not touches, "The page boundary is complete" if not touches else "Part of the page edge may be missing")


def blur_score(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())
