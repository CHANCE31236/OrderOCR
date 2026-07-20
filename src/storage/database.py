from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils.paths import data_dir


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "tasks.sqlite3"
        self._lock = threading.RLock()
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, status TEXT NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS page_cache (
                    image_hash TEXT PRIMARY KEY, image_path TEXT NOT NULL,
                    status TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_task(self, task_id: str, status: str, payload: dict[str, Any]) -> None:
        now = self._now()
        with self._lock, self.connect() as conn:
            conn.execute(
                """INSERT INTO tasks(id,status,created_at,updated_at,payload) VALUES(?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET status=excluded.status,updated_at=excluded.updated_at,payload=excluded.payload""",
                (task_id, status, now, now, json.dumps(payload, ensure_ascii=False)),
            )

    def incomplete_tasks(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM tasks WHERE status NOT IN ('completed','cancelled') ORDER BY updated_at DESC").fetchall()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]

    def cache_page(self, image_hash: str, image_path: str, status: str, payload: dict[str, Any]) -> None:
        with self._lock, self.connect() as conn:
            conn.execute(
                """INSERT INTO page_cache(image_hash,image_path,status,payload,updated_at) VALUES(?,?,?,?,?)
                ON CONFLICT(image_hash) DO UPDATE SET image_path=excluded.image_path,status=excluded.status,payload=excluded.payload,updated_at=excluded.updated_at""",
                (image_hash, image_path, status, json.dumps(payload, ensure_ascii=False), self._now()),
            )

    def load_page(self, image_hash: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT payload FROM page_cache WHERE image_hash=? AND status='completed'", (image_hash,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def audit(self, task_id: str, event_type: str, payload: dict[str, Any]) -> None:
        with self._lock, self.connect() as conn:
            conn.execute(
                "INSERT INTO audit_events(task_id,event_type,payload,created_at) VALUES(?,?,?,?)",
                (task_id, event_type, json.dumps(payload, ensure_ascii=False), self._now()),
            )

    def audit_events(self, task_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM audit_events WHERE task_id=? ORDER BY id", (task_id,)).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]

