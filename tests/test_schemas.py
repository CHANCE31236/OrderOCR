import pytest
from pydantic import ValidationError

from src.business.confidence import reconcile_row
from src.ocr.schemas import PageExtraction, RowObservation, RowVerification


def observation(code="00001535", **changes):
    values = dict(
        row_number=1,
        product_code=code,
        printed_box_count=10,
        printed_total_quantity=40,
        circle_status="full_circle",
        handwritten_override=None,
        override_is_clearly_associated=False,
        calculated_final_box_count=10,
        product_code_confidence=0.99,
        circle_confidence=0.98,
        overall_confidence=0.98,
        needs_review=False,
        reason="Printed box count 10 is surrounded by a closed circle",
    )
    values.update(changes)
    return RowObservation(**values)


def test_schema_rejects_negative_box_count():
    with pytest.raises(ValidationError):
        observation(printed_box_count=-1)


def test_schema_rejects_decimal_box_count():
    with pytest.raises(ValidationError):
        observation(printed_box_count=1.5)


def test_schema_rejects_extra_model_fields():
    with pytest.raises(ValidationError):
        observation(guess="not allowed")


def test_first_and_second_product_code_conflict_needs_review():
    first = observation("00001535")
    second = RowVerification(
        row_number=1,
        product_code="0000153S",
        printed_box_count=10,
        circle_status="full_circle",
        product_code_confidence=0.95,
        circle_confidence=0.98,
        overall_confidence=0.95,
        needs_review=False,
        reason="Independent verification",
    )
    reviewed = reconcile_row(first, second, 0.9)
    assert reviewed.needs_review is True
    assert reviewed.status == "manual_review_required"
    assert "do not match" in reviewed.review_reason


def test_page_schema_requires_order_number():
    with pytest.raises(ValidationError):
        PageExtraction(order_number=" ", page_number=1, total_pages=1, rows=[])
