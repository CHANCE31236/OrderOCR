from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import keyring
from dotenv import dotenv_values

from src.utils.paths import config_dir, default_output_dir, resource_path


SERVICE_NAME = "OrderOCR.OpenAI"
KEY_USERNAME = "OPENAI_API_KEY"


class SettingsStore:
    def __init__(self) -> None:
        self.path = config_dir() / "settings.json"
        self._settings = self._load()

    def _defaults(self) -> dict[str, Any]:
        template = resource_path("config", "settings.json")
        if template.exists():
            return json.loads(template.read_text(encoding="utf-8"))
        return {
            "vision_model": "",
            "verification_model": "",
            "minimum_confidence": 0.9,
            "save_row_crops": True,
            "output_directory": str(default_output_dir()),
            "api_retry_count": 4,
            "max_concurrency": 2,
            "language": "en",
            "api_timeout_seconds": 90,
            "verify_all_rows": True,
            "auto_delete_task_images": False,
        }

    def _load(self) -> dict[str, Any]:
        settings = self._defaults()
        if self.path.exists():
            try:
                settings.update(json.loads(self.path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                pass
        env_model = os.getenv("OPENAI_VISION_MODEL")
        if env_model:
            settings["vision_model"] = env_model
        if not settings.get("output_directory"):
            settings["output_directory"] = str(default_output_dir())
        return settings

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self._settings)

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def update(self, values: dict[str, Any]) -> None:
        allowed = set(self._defaults())
        self._settings.update({k: v for k, v in values.items() if k in allowed})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._settings, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_api_key(self) -> str | None:
        if value := os.getenv("OPENAI_API_KEY"):
            return value.strip()
        for env_path in (Path.cwd() / ".env", resource_path(".env")):
            if env_path.exists():
                value = dotenv_values(env_path).get("OPENAI_API_KEY")
                if value and not str(value).startswith("enter_"):
                    return str(value).strip()
        try:
            return keyring.get_password(SERVICE_NAME, KEY_USERNAME)
        except keyring.errors.KeyringError:
            return None

    def set_api_key(self, value: str) -> None:
        value = value.strip()
        if not value:
            try:
                keyring.delete_password(SERVICE_NAME, KEY_USERNAME)
            except (keyring.errors.KeyringError, keyring.errors.PasswordDeleteError):
                pass
            return
        keyring.set_password(SERVICE_NAME, KEY_USERNAME, value)
