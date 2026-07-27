from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler

from src.utils.paths import log_dir


SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{10,}")


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = SECRET_PATTERN.sub("[API密钥已隐藏]", str(record.msg))
        record.args = tuple(SECRET_PATTERN.sub("[API密钥已隐藏]", str(v)) for v in record.args)
        return True


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("orderocr")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_dir() / "orderocr.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler.addFilter(RedactingFilter())
    logger.addHandler(handler)
    return logger

