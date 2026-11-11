from __future__ import annotations

import json
from pathlib import Path

from src.ocr.schemas import PageExtraction
from src.ocr.vision_client import VisionClient
from src.utils.paths import resource_path


class PageExtractor:
    def __init__(self, client: VisionClient, model: str) -> None:
        self.client = client
        self.model = model
        self.prompt = resource_path("config", "prompts", "page_extraction_prompt.txt").read_text(encoding="utf-8")

    def extract(self, page_path: str | Path, image_hash: str, local_ocr: list[dict]) -> PageExtraction:
        prompt = self.prompt + "\n\nLocal OCR hints for positioning only; when they conflict, trust the image:\n" + json.dumps(local_ocr, ensure_ascii=False)
        result = self.client.structured_image_call(
            model=self.model,
            prompt=prompt,
            image_paths=[page_path],
            schema=PageExtraction,
            cache_key=f"page_{image_hash}_{self.model}",
            detail="high",
        )
        for row in result.rows:
            row.source_image = str(page_path)
        return result
