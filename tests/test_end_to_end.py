from pathlib import Path

import cv2
import numpy as np
import pytest
from openpyxl import load_workbook

import src.ocr.pipeline as pipeline_module
from src.export.excel_exporter import export_order_excel
from src.ocr.pipeline import RecognitionPipeline
from src.ocr.schemas import PageExtraction, RowObservation, RowVerification
from src.storage.database import Database


class FakeSettings:
    values = {
        "vision_model": "test-vision",
        "verification_model": "test-verification",
        "minimum_confidence": 0.9,
        "api_retry_count": 1,
        "api_timeout_seconds": 1,
        "verify_all_rows": True,
    }

    def as_dict(self):
        return dict(self.values)

    def get_api_key(self):
        return "sk-test-not-real"


class FakeOCR:
    def text_score(self, _image):
        return 0.0

    def as_dicts(self, _image):
        return [{"text": "00001535", "confidence": 0.99, "box": [[50, 200], [250, 200], [250, 240], [50, 240]]}]


class FakeVisionClient:
    def __init__(self, _key, settings):
        self.settings = settings
        self.api_calls = 2


class FakeExtractor:
    def __init__(self, *_args):
        pass

    def extract(self, _page_path, _digest, _local):
        row = RowObservation(
            row_number=1,
            product_code="00001535",
            printed_box_count=5,
            printed_total_quantity=150,
            circle_status="full_circle",
            calculated_final_box_count=5,
            product_code_confidence=0.99,
            circle_confidence=0.99,
            overall_confidence=0.99,
            needs_review=False,
            reason="5 is surrounded by a closed circle",
        )
        return PageExtraction(order_number="Vs20260713-12", page_number=1, total_pages=1, rows=[row], page_confidence=0.99)


class FakeVerifier:
    def __init__(self, *_args):
        pass

    def verify(self, **_kwargs):
        return RowVerification(
            row_number=1,
            product_code="00001535",
            printed_box_count=5,
            circle_status="full_circle",
            proposed_final_box_count=5,
            product_code_confidence=0.99,
            circle_confidence=0.99,
            overall_confidence=0.99,
            needs_review=False,
            reason="Independent verification confirms a closed circle",
        )


class TwoRowExtractor(FakeExtractor):
    def extract(self, _page_path, _digest, _local):
        page = super().extract(_page_path, _digest, _local)
        second = page.rows[0].model_copy(deep=True)
        second.row_number = 2
        second.product_code = "DV1731-01"
        page.rows.append(second)
        return page


class OneRowFailsVerifier(FakeVerifier):
    def verify(self, **kwargs):
        if kwargs["row_number"] == 2:
            raise RuntimeError("Simulated single-row timeout")
        return super().verify(**kwargs)


@pytest.mark.parametrize("needs_review, confidence", [(True, 0.99), (False, 0.5)])
def test_page_uncertainty_requires_review_before_export(tmp_path: Path, monkeypatch, needs_review, confidence):
    class UncertainPageExtractor(FakeExtractor):
        def extract(self, *args):
            page = super().extract(*args)
            page.needs_review = needs_review
            page.page_confidence = confidence
            page.reason = "The order heading is uncertain"
            return page

    image_path = tmp_path / "page.jpg"
    cv2.imencode(".jpg", np.full((900, 650, 3), 255, np.uint8))[1].tofile(str(image_path))
    monkeypatch.setattr(pipeline_module, "VisionClient", FakeVisionClient)
    monkeypatch.setattr(pipeline_module, "PageExtractor", UncertainPageExtractor)
    monkeypatch.setattr(pipeline_module, "RowVerifier", FakeVerifier)
    monkeypatch.setattr(pipeline_module, "cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setattr(pipeline_module, "blur_score", lambda _image: 100)
    monkeypatch.setattr(pipeline_module, "preprocess_image", lambda *_args: pipeline_module.PreprocessedImage(
        original_color=np.full((900, 650, 3), 255, np.uint8),
        corrected_color=np.full((900, 650, 3), 255, np.uint8),
        enhanced_color=np.full((900, 650, 3), 255, np.uint8),
        enhanced_gray=np.full((900, 650), 255, np.uint8),
        rotation_angle=0,
        perspective_corrected=True,
        page_edge_missing=False,
    ))
    pipeline = RecognitionPipeline(FakeSettings(), Database(tmp_path / "tasks.sqlite3"))
    pipeline.local_ocr = FakeOCR()
    result = pipeline.run([str(image_path)])
    row = result.pages[0].reviewed_rows[0]
    assert row.needs_review is True
    assert row.status == "manual_review_required"
    assert "page extraction requires manual review" in row.review_reason
    from src.export.excel_exporter import ExportBlockedError
    with pytest.raises(ExportBlockedError, match="manual confirmation"):
        export_order_excel(result.pages[0].extraction.order_number, [row], tmp_path / "excel")


def test_mocked_photo_to_excel_end_to_end(tmp_path: Path, monkeypatch):
    image = np.full((900, 650, 3), 255, np.uint8)
    cv2.rectangle(image, (20, 20), (630, 880), (0, 0, 0), 3)
    cv2.putText(image, "00001535   5   150", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    image_path = tmp_path / "order.jpg"
    cv2.imencode(".jpg", image)[1].tofile(str(image_path))

    monkeypatch.setattr(pipeline_module, "VisionClient", FakeVisionClient)
    monkeypatch.setattr(pipeline_module, "PageExtractor", FakeExtractor)
    monkeypatch.setattr(pipeline_module, "RowVerifier", FakeVerifier)
    monkeypatch.setattr(pipeline_module, "cache_dir", lambda: tmp_path / "cache")
    pipeline = RecognitionPipeline(FakeSettings(), Database(tmp_path / "tasks.sqlite3"))
    pipeline.local_ocr = FakeOCR()

    result = pipeline.run([str(image_path)])
    assert list(result.groups) == ["Vs20260713-12"]
    reviewed = result.pages[0].reviewed_rows[0]
    assert reviewed.observation.product_code == "00001535"
    assert reviewed.final_box_count == 5
    assert reviewed.observation.printed_total_quantity == 150
    reviewed.manually_confirmed = True
    reviewed.needs_review = False

    excel = export_order_excel("Vs20260713-12", [reviewed], tmp_path / "excel")
    sheet = load_workbook(excel).active
    assert sheet["A2"].value == "00001535"
    assert sheet["B2"].value == 5


def test_one_row_api_failure_does_not_abort_page(tmp_path: Path, monkeypatch):
    image = np.full((900, 650, 3), 255, np.uint8)
    image_path = tmp_path / "two_rows.jpg"
    cv2.imencode(".jpg", image)[1].tofile(str(image_path))
    monkeypatch.setattr(pipeline_module, "VisionClient", FakeVisionClient)
    monkeypatch.setattr(pipeline_module, "PageExtractor", TwoRowExtractor)
    monkeypatch.setattr(pipeline_module, "RowVerifier", OneRowFailsVerifier)
    monkeypatch.setattr(pipeline_module, "cache_dir", lambda: tmp_path / "cache")
    pipeline = RecognitionPipeline(FakeSettings(), Database(tmp_path / "tasks.sqlite3"))
    pipeline.local_ocr = FakeOCR()
    result = pipeline.run([str(image_path)])
    assert len(result.pages) == 1
    assert len(result.pages[0].reviewed_rows) == 2
    failed = result.pages[0].reviewed_rows[1]
    assert failed.needs_review is True
    assert "independent verification failed" in failed.review_reason
