from __future__ import annotations

import cv2
import numpy as np


def _order_points(points: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype=np.float32)
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).ravel()
    rect[0] = points[np.argmin(sums)]
    rect[2] = points[np.argmax(sums)]
    rect[1] = points[np.argmin(differences)]
    rect[3] = points[np.argmax(differences)]
    return rect


def detect_page_quad(image: np.ndarray, min_area_ratio: float = 0.25) -> np.ndarray | None:
    height, width = image.shape[:2]
    scale = min(1.0, 1400.0 / max(height, width))
    preview = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(preview, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 40, 130)
    edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)
    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    minimum = preview.shape[0] * preview.shape[1] * min_area_ratio
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:20]:
        if cv2.contourArea(contour) < minimum:
            break
        polygon = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
        if len(polygon) == 4 and cv2.isContourConvex(polygon):
            return _order_points(polygon.reshape(4, 2).astype(np.float32) / scale)
    return None


def four_point_transform(image: np.ndarray, points: np.ndarray) -> np.ndarray:
    top_left, top_right, bottom_right, bottom_left = _order_points(points)
    width = int(max(np.linalg.norm(bottom_right - bottom_left), np.linalg.norm(top_right - top_left)))
    height = int(max(np.linalg.norm(top_right - bottom_right), np.linalg.norm(top_left - bottom_left)))
    if width < 50 or height < 50:
        return image.copy()
    destination = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(_order_points(points), destination)
    return cv2.warpPerspective(image, matrix, (width, height), borderMode=cv2.BORDER_REPLICATE)


def correct_perspective(image: np.ndarray) -> tuple[np.ndarray, bool]:
    quad = detect_page_quad(image)
    return (four_point_transform(image, quad), True) if quad is not None else (image.copy(), False)

