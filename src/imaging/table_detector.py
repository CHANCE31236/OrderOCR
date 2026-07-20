from __future__ import annotations

import cv2
import numpy as np


def table_line_masks(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, gray.shape[1] // 25), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, gray.shape[0] // 30)))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    return horizontal, vertical


def horizontal_line_positions(gray: np.ndarray) -> list[int]:
    horizontal, _ = table_line_masks(gray)
    projection = np.count_nonzero(horizontal, axis=1)
    threshold = max(30, int(gray.shape[1] * 0.25))
    indices = np.where(projection >= threshold)[0]
    if not len(indices):
        return []
    groups: list[list[int]] = [[int(indices[0])]]
    for value in indices[1:]:
        if int(value) - groups[-1][-1] <= 3:
            groups[-1].append(int(value))
        else:
            groups.append([int(value)])
    return [int(sum(group) / len(group)) for group in groups]


def detect_table_bbox(gray: np.ndarray) -> tuple[int, int, int, int] | None:
    horizontal, vertical = table_line_masks(gray)
    combined = cv2.bitwise_or(horizontal, vertical)
    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = [cv2.boundingRect(c) for c in contours]
    candidates = [box for box in candidates if box[2] > gray.shape[1] * 0.4 and box[3] > gray.shape[0] * 0.15]
    return max(candidates, key=lambda box: box[2] * box[3]) if candidates else None

