from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.imaging.orientation import auto_orient, read_with_exif
from src.imaging.perspective import correct_perspective


@dataclass(slots=True)
class PreprocessedImage:
    original_color: np.ndarray
    corrected_color: np.ndarray
    enhanced_color: np.ndarray
    enhanced_gray: np.ndarray
    rotation_angle: int
    perspective_corrected: bool
    page_edge_missing: bool


def shadow_correct(gray: np.ndarray) -> np.ndarray:
    kernel = max(31, (min(gray.shape[:2]) // 20) | 1)
    background = cv2.GaussianBlur(gray, (kernel, kernel), 0)
    return cv2.divide(gray, background, scale=255)


def enhance(color: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    denoised = cv2.fastNlMeansDenoisingColored(color, None, 4, 4, 7, 21)
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    light, a, b = cv2.split(lab)
    light = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(light)
    enhanced_color = cv2.cvtColor(cv2.merge((light, a, b)), cv2.COLOR_LAB2BGR)
    gray = cv2.cvtColor(enhanced_color, cv2.COLOR_BGR2GRAY)
    gray = shadow_correct(gray)
    blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)
    gray = cv2.addWeighted(gray, 1.7, blurred, -0.7, 0)
    return enhanced_color, gray


def preprocess_image(path: str | Path, text_score=None) -> PreprocessedImage:
    original = read_with_exif(str(path))
    oriented, angle = auto_orient(original, text_score)
    corrected, found = correct_perspective(oriented)
    color, gray = enhance(corrected)
    page_edge_missing = not found
    return PreprocessedImage(original, corrected, color, gray, angle, found, page_edge_missing)


def write_image(path: str | Path, image: np.ndarray, quality: int = 94) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.lower() or ".jpg"
    params = [cv2.IMWRITE_JPEG_QUALITY, quality] if suffix in {".jpg", ".jpeg"} else []
    ok, encoded = cv2.imencode(suffix, image, params)
    if not ok:
        raise OSError(f"Could not encode the image: {target}")
    encoded.tofile(str(target))
    return target
