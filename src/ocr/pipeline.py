from __future__ import annotations

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable

import cv2

from src.business.confidence import reconcile_row
from src.business.order_grouper import OrderGroup, group_orders
from src.business.validators import validate_image_path
from src.imaging.page_detector import blur_score
from src.imaging.preprocessing import PreprocessedImage, preprocess_image, write_image
from src.imaging.row_cropper import crop_box_quantity_columns, detect_row_boxes
from src.ocr.local_ocr import LocalOCR
from src.ocr.page_extractor import PageExtractor
from src.ocr.row_verifier import RowVerifier
from src.ocr.schemas import PageExtraction, ReviewedRow
from src.ocr.vision_client import VisionClient
from src.storage.database import Database
from src.utils.hashing import sha256_file
from src.utils.paths import cache_dir


class CancelledError(RuntimeError):
    pass


@dataclass(slots=True)
class ProcessedPage:
    source_path: str
    image_hash: str
    corrected_path: str
    local_ocr: list[dict]
    extraction: PageExtraction
    reviewed_rows: list[ReviewedRow]
    warnings: list[str] = field(default_factory=list)

    def audit_payload(self) -> dict:
        return {
            "original_image_filename": Path(self.source_path).name,
            "source_image": self.source_path,
            "image_sha256": self.image_hash,
            "recognized_at": datetime.now(timezone.utc).isoformat(),
            "order_number": self.extraction.order_number,
            "page_number": self.extraction.page_number,
            "total_pages": self.extraction.total_pages,
            "local_ocr": self.local_ocr,
            "first_vision_result": self.extraction.model_dump(mode="json"),
            "second_verification_results": [
                row.verification.model_dump(mode="json") if row.verification else None for row in self.reviewed_rows
            ],
            "python_rule_results": [
                {"row_number": row.observation.row_number, "final_box_count": row.final_box_count, "needs_review": row.needs_review, "reason": row.review_reason}
                for row in self.reviewed_rows
            ],
            "warnings": self.warnings,
        }


@dataclass(slots=True)
class PipelineResult:
    task_id: str
    pages: list[ProcessedPage]
    groups: dict[str, OrderGroup]
    errors: list[str]
    api_calls: int


class RecognitionPipeline:
    def __init__(self, settings_store, database: Database | None = None) -> None:
        self.settings_store = settings_store
        self.settings = settings_store.as_dict()
        self.database = database or Database()
        self.local_ocr = LocalOCR()
        self.cancel_event = threading.Event()
        self.run_event = threading.Event()
        self.run_event.set()

    def cancel(self) -> None:
        self.cancel_event.set()
        self.run_event.set()

    def pause(self) -> None:
        self.run_event.clear()

    def resume(self) -> None:
        self.run_event.set()

    def _checkpoint(self) -> None:
        if self.cancel_event.is_set():
            raise CancelledError("The task was cancelled")
        self.run_event.wait()
        if self.cancel_event.is_set():
            raise CancelledError("The task was cancelled")

    def run(
        self,
        image_paths: list[str],
        progress: Callable[[int, int, str, int], None] | None = None,
        task_id: str | None = None,
    ) -> PipelineResult:
        task_id = task_id or uuid.uuid4().hex
        unique: list[tuple[Path, str]] = []
        seen: set[str] = set()
        errors: list[str] = []
        for raw in image_paths:
            try:
                path = validate_image_path(raw)
                digest = sha256_file(path)
                if digest in seen:
                    errors.append(f"Skipped duplicate image: {path.name}")
                    continue
                seen.add(digest)
                unique.append((path, digest))
            except (ValueError, OSError) as exc:
                errors.append(str(exc))
        if not unique:
            raise ValueError("There are no valid images to recognize")

        key = self.settings_store.get_api_key()
        client = VisionClient(key or "", self.settings)
        extractor = PageExtractor(client, self.settings["vision_model"])
        verifier = RowVerifier(client, self.settings["verification_model"])
        self.database.save_task(task_id, "running", {"images": [str(p) for p, _ in unique], "errors": errors})
        processed: list[ProcessedPage] = []
        total = len(unique)
        try:
            for index, (path, digest) in enumerate(unique, start=1):
                self._checkpoint()
                if progress:
                    progress(index - 1, total, f"Preprocessing {path.name}", client.api_calls)
                try:
                    page = self._process_page(task_id, path, digest, client, extractor, verifier)
                    processed.append(page)
                    self.database.cache_page(digest, str(path), "completed", page.extraction.model_dump(mode="json"))
                except CancelledError:
                    raise
                except Exception as exc:  # A single-page failure must not stop the entire order.
                    errors.append(f"{path.name}: {exc}")
                    self.database.cache_page(digest, str(path), "failed", {"error": str(exc)})
                self.database.save_task(task_id, "running", {"images": [str(p) for p, _ in unique], "completed": index, "errors": errors})
                if progress:
                    progress(index, total, f"Completed page {index}/{total}", client.api_calls)
        except CancelledError:
            self.database.save_task(task_id, "cancelled", {"images": [str(p) for p, _ in unique], "errors": errors})
            raise

        groups = group_orders([page.extraction for page in processed])
        for page in processed:
            group = groups.get(page.extraction.order_number)
            if group and group.export_blocked:
                if group.missing_pages:
                    page.warnings.append("Missing page(s): " + ", ".join(map(str, group.missing_pages)))
                if group.duplicate_pages:
                    page.warnings.append("Duplicate page number(s): " + ", ".join(map(str, group.duplicate_pages)))
                if group.similar_order_warning:
                    page.warnings.append("Similar order number(s) require review: " + ", ".join(group.similar_order_warning))
                for row in page.reviewed_rows:
                    row.needs_review = True
                    row.status = "manual_review_required"
                    row.review_reason = "; ".join(filter(None, [row.review_reason, *page.warnings]))
        status = "completed" if processed else "failed"
        self.database.save_task(task_id, status, {"images": [str(p) for p, _ in unique], "errors": errors, "orders": list(groups)})
        return PipelineResult(task_id, processed, groups, errors, client.api_calls)

    def _process_page(self, task_id: str, path: Path, digest: str, client, extractor, verifier) -> ProcessedPage:
        task_cache = cache_dir() / "tasks" / task_id / digest[:16]
        task_cache.mkdir(parents=True, exist_ok=True)
        prepared = preprocess_image(path, self.local_ocr.text_score)
        corrected_path = write_image(task_cache / "corrected.jpg", prepared.enhanced_color)
        local = self.local_ocr.as_dicts(prepared.enhanced_gray)
        cached = self.database.load_page(digest)
        extraction = PageExtraction.model_validate(cached) if cached else extractor.extract(corrected_path, digest, local)
        crop_paths = self._make_row_crops(prepared, extraction, local, task_cache)
        minimum = float(self.settings.get("minimum_confidence", 0.9))
        verification_by_index: dict[int, object] = {}
        verification_errors: dict[int, str] = {}
        jobs: dict = {}
        workers = max(1, int(self.settings.get("max_concurrency", 2)))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="row-verify") as pool:
            for row_index, row in enumerate(extraction.rows):
                self._checkpoint()
                row_path, columns_path = crop_paths[row_index]
                row.row_crop = str(row_path)
                high_risk = any(token in row.product_code for token in ("0", "O", "1", "I", "l", "5", "S")) or row.circle_status == "uncertain"
                should_verify = bool(self.settings.get("verify_all_rows", True)) or row.overall_confidence < minimum or high_risk
                if should_verify:
                    future = pool.submit(
                        verifier.verify,
                        page_path=corrected_path,
                        row_path=row_path,
                        columns_path=columns_path,
                        cache_key=f"row_{digest}_{row.row_number}_{client.settings['verification_model']}",
                        row_number=row.row_number,
                    )
                    jobs[future] = row_index
            for future in as_completed(jobs):
                row_index = jobs[future]
                try:
                    verification_by_index[row_index] = future.result()
                except Exception as exc:
                    verification_errors[row_index] = str(exc)

        reviewed: list[ReviewedRow] = []
        for row_index, row in enumerate(extraction.rows):
            self._checkpoint()
            verification = verification_by_index.get(row_index)
            decision = reconcile_row(row, verification, minimum)
            if row_index in verification_errors:
                decision.needs_review = True
                decision.status = "manual_review_required"
                decision.review_reason += "; independent verification failed: " + verification_errors[row_index]
            if blur_score(prepared.corrected_color) < 60:
                decision.needs_review = True
                decision.status = "manual_review_required"
                decision.review_reason += "; the source image may be blurred"
            if prepared.page_edge_missing:
                decision.needs_review = True
                decision.status = "manual_review_required"
                decision.review_reason += "; a complete page boundary was not detected"
            reviewed.append(decision)
        return ProcessedPage(str(path), digest, str(corrected_path), local, extraction, reviewed)

    def _make_row_crops(
        self,
        prepared: PreprocessedImage,
        extraction: PageExtraction,
        local: list[dict],
        output: Path,
    ) -> list[tuple[Path, Path]]:
        boxes = detect_row_boxes(prepared.enhanced_gray)
        selected: list[tuple[int, int, int, int] | None] = []
        unused = set(range(len(boxes)))
        for row in extraction.rows:
            target_y = None
            best = 0.0
            for item in local:
                score = SequenceMatcher(None, row.product_code.casefold(), str(item["text"]).casefold()).ratio()
                if score > best and score >= 0.55:
                    ys = [point[1] for point in item["box"]]
                    target_y, best = sum(ys) / len(ys), score
            candidates = [i for i in unused if target_y is not None and boxes[i][1] <= target_y <= boxes[i][1] + boxes[i][3]]
            chosen = candidates[0] if candidates else (min(unused) if unused else None)
            selected.append(boxes[chosen] if chosen is not None else None)
            if chosen is not None:
                unused.discard(chosen)

        results: list[tuple[Path, Path]] = []
        count = max(1, len(extraction.rows))
        for index, box in enumerate(selected, start=1):
            if box is None:
                top = int(prepared.enhanced_color.shape[0] * (0.22 + 0.7 * (index - 1) / count))
                bottom = int(prepared.enhanced_color.shape[0] * (0.22 + 0.7 * index / count))
                crop = prepared.enhanced_color[top:bottom]
            else:
                x, y, width, height = box
                margin = max(3, height // 10)
                crop = prepared.enhanced_color[max(0, y - margin) : min(prepared.enhanced_color.shape[0], y + height + margin), x : x + width]
            row_path = write_image(output / f"row_{index}.jpg", crop)
            columns_path = write_image(output / f"row_{index}_box_quantity.jpg", crop_box_quantity_columns(crop))
            results.append((row_path, columns_path))
        return results
