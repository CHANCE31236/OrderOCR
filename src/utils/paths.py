from __future__ import annotations

import sys
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir, user_log_dir


APP_NAME = "OrderOCR"
APP_SLUG = "OrderOCR"


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def config_dir() -> Path:
    path = Path(user_config_dir(APP_SLUG, "OrderOCR"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    path = Path(user_data_dir(APP_SLUG, "OrderOCR"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = Path(user_log_dir(APP_SLUG, "OrderOCR"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_output_dir() -> Path:
    path = Path.home() / "Desktop" / "OrderExcel"
    path.mkdir(parents=True, exist_ok=True)
    return path
