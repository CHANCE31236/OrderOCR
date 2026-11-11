from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
WINDOWS_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_RESERVED_FILENAME = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)", re.IGNORECASE)


def validate_product_code(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("The product code cannot be empty")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError("The product code contains invalid control characters")
    return value


def validate_image_path(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_file():
        raise ValueError(f"The image does not exist: {candidate}")
    if candidate.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        raise ValueError(f"Unsupported image format: {candidate.suffix}")
    return candidate


def safe_order_filename(order_number: str) -> str:
    if not isinstance(order_number, str) or not order_number.strip() or WINDOWS_INVALID_FILENAME.search(order_number):
        raise ValueError("The order number contains characters that are invalid in a Windows filename")
    if order_number.endswith((".", " ")):
        raise ValueError("The order number cannot end with a period or space")
    if WINDOWS_RESERVED_FILENAME.match(order_number):
        raise ValueError("The order number is a reserved Windows device name")
    return order_number


def duplicate_product_codes(codes: list[str]) -> list[str]:
    counts = Counter(codes)
    return [code for code, count in counts.items() if count > 1]
