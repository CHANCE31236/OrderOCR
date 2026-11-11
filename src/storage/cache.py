from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from src.utils.paths import cache_dir


class JsonCache:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or cache_dir()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, namespace: str, key: str) -> Path:
        safe = "".join(c for c in key if c.isalnum() or c in "-_")
        folder = self.root / namespace
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{safe}.json"

    def get(self, namespace: str, key: str) -> dict[str, Any] | None:
        path = self._path(namespace, key)
        try:
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        except (OSError, json.JSONDecodeError):
            return None

    def put(self, namespace: str, key: str, value: dict[str, Any]) -> Path:
        path = self._path(namespace, key)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
        return path

    def clear(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

