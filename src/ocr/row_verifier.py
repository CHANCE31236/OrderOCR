from __future__ import annotations

from pathlib import Path

from src.ocr.schemas import RowVerification
from src.ocr.vision_client import VisionClient
from src.utils.paths import resource_path


class RowVerifier:
    def __init__(self, client: VisionClient, model: str) -> None:
        self.client = client
        self.model = model
        self.prompt = resource_path("config", "prompts", "row_verification_prompt.txt").read_text(encoding="utf-8")

    def verify(
        self,
        *,
        page_path: str | Path,
        row_path: str | Path,
        columns_path: str | Path,
        cache_key: str,
        row_number: int,
    ) -> RowVerification:
        prompt = f"{self.prompt}\n\nIndependently verify row {row_number}. Do not copy the first recognition result."
        return self.client.structured_image_call(
            model=self.model,
            prompt=prompt,
            image_paths=[page_path, row_path, columns_path],
            schema=RowVerification,
            cache_key=cache_key,
            detail="high",
        )
