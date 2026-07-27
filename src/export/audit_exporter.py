from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.business.validators import safe_order_filename


def export_audit_log(order_number: str, output_directory: str | Path, payload: dict[str, Any]) -> Path:
    safe_order_filename(order_number)
    folder = Path(output_directory) / "审核日志"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{order_number}_review.json"
    clean = dict(payload)
    for key in list(clean):
        if "api_key" in key.casefold() or key.casefold() == "authorization":
            clean.pop(key, None)
    clean.setdefault("exported_at", datetime.now(timezone.utc).isoformat())
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)
    return target

