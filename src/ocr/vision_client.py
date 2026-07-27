from __future__ import annotations

import base64
import time
import threading
from pathlib import Path
from typing import TypeVar

import cv2
import numpy as np
from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from src.storage.cache import JsonCache


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class VisionError(RuntimeError):
    pass


def _read_image(path: str | Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise VisionError(f"图片损坏或无法读取：{path}")
    return image


def image_data_url(path: str | Path, max_side: int = 2600, quality: int = 94) -> str:
    image = _read_image(path)
    height, width = image.shape[:2]
    if max(height, width) > max_side:
        scale = max_side / max(height, width)
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise VisionError(f"图片编码失败：{path}")
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")


class VisionClient:
    def __init__(self, api_key: str, settings: dict, cache: JsonCache | None = None) -> None:
        if not api_key:
            raise VisionError("未配置 OPENAI_API_KEY")
        self.settings = settings
        self.client = OpenAI(api_key=api_key, timeout=float(settings.get("api_timeout_seconds", 90)))
        self.cache = cache or JsonCache()
        self.api_calls = 0
        self._calls_lock = threading.Lock()

    def structured_image_call(
        self,
        *,
        model: str,
        prompt: str,
        image_paths: list[str | Path],
        schema: type[SchemaT],
        cache_key: str,
        detail: str = "high",
    ) -> SchemaT:
        cached = self.cache.get("vision", cache_key)
        if cached is not None:
            return schema.model_validate(cached)

        content: list[dict] = [{"type": "input_text", "text": prompt}]
        for path in image_paths:
            content.append({"type": "input_image", "image_url": image_data_url(path), "detail": detail})
        attempts = max(1, int(self.settings.get("api_retry_count", 4)))
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                with self._calls_lock:
                    self.api_calls += 1
                responses = self.client.responses
                if hasattr(responses, "parse"):
                    response = responses.parse(
                        model=model,
                        input=[{"role": "user", "content": content}],
                        text_format=schema,
                    )
                    parsed = response.output_parsed
                    if parsed is None:
                        raise VisionError("模型拒绝或未返回结构化结果")
                    result = parsed if isinstance(parsed, schema) else schema.model_validate(parsed)
                else:
                    response = responses.create(
                        model=model,
                        input=[{"role": "user", "content": content}],
                        text={"format": {"type": "json_schema", "name": schema.__name__, "schema": schema.model_json_schema(), "strict": True}},
                    )
                    result = schema.model_validate_json(response.output_text)
                self.cache.put("vision", cache_key, result.model_dump(mode="json"))
                return result
            except (RateLimitError, APITimeoutError, APIConnectionError, ValidationError, VisionError) as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    time.sleep(min(16.0, 2.0**attempt))
        raise VisionError(f"视觉 API 调用失败（已重试 {attempts} 次）：{last_error}") from last_error
