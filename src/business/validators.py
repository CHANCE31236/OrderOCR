from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
WINDOWS_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def validate_product_code(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("货号不能为空")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError("货号包含无效控制字符")
    return value


def validate_image_path(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_file():
        raise ValueError(f"图片不存在：{candidate}")
    if candidate.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        raise ValueError(f"不支持的图片格式：{candidate.suffix}")
    return candidate


def safe_order_filename(order_number: str) -> str:
    if not order_number or WINDOWS_INVALID_FILENAME.search(order_number):
        raise ValueError("订单号包含 Windows 文件名不允许的字符")
    if order_number.endswith((".", " ")):
        raise ValueError("订单号不能以句点或空格结尾")
    return order_number


def duplicate_product_codes(codes: list[str]) -> list[str]:
    counts = Counter(codes)
    return [code for code, count in counts.items() if count > 1]

