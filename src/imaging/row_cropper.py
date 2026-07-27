from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src.imaging.preprocessing import write_image
from src.imaging.table_detector import detect_table_bbox, horizontal_line_positions


def detect_row_boxes(gray: np.ndarray, minimum_height: int = 24) -> list[tuple[int, int, int, int]]:
    bbox = detect_table_bbox(gray)
    x, y, width, height = bbox or (0, 0, gray.shape[1], gray.shape[0])
    positions = [p for p in horizontal_line_positions(gray) if y <= p <= y + height]
    boxes: list[tuple[int, int, int, int]] = []
    for top, bottom in zip(positions, positions[1:]):
        if bottom - top >= minimum_height:
            boxes.append((x, top + 1, width, bottom - top - 1))
    return boxes


def crop_rows(color: np.ndarray, gray: np.ndarray, output_dir: str | Path, prefix: str) -> list[Path]:
    output = Path(output_dir)
    paths: list[Path] = []
    for index, (x, y, width, height) in enumerate(detect_row_boxes(gray), start=1):
        margin = max(2, height // 12)
        top, bottom = max(0, y - margin), min(color.shape[0], y + height + margin)
        crop = color[top:bottom, x : x + width]
        if crop.size:
            paths.append(write_image(output / f"{prefix}_row_{index}.jpg", crop))
    return paths


def crop_box_quantity_columns(row: np.ndarray) -> np.ndarray:
    """保留商品行右侧约 45%，通常覆盖“箱”和“数量”两列，供视觉模型放大核验。"""
    start = int(row.shape[1] * 0.55)
    right = row[:, start:]
    return cv2.resize(right, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

