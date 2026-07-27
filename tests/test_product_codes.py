import pytest

from src.business.validators import validate_product_code
from src.ocr.schemas import RowObservation


@pytest.mark.parametrize("code", ["00001535", "DV1731-01", "ORCHIDEE RIZ LONG 5x4.5kg", "FT7850-1/107154", "aBc-0/O.1"])
def test_product_code_is_preserved_character_for_character(code):
    assert validate_product_code(code) == code
    row = RowObservation(
        row_number=1,
        product_code=code,
        printed_box_count=1,
        circle_status="full_circle",
        product_code_confidence=1.0,
        circle_confidence=1.0,
        overall_confidence=1.0,
        needs_review=False,
        reason="清晰",
    )
    assert row.product_code == code


@pytest.mark.parametrize("code", ["", "   ", "ABC\x00"])
def test_empty_or_control_character_product_codes_are_rejected(code):
    with pytest.raises(ValueError):
        validate_product_code(code)

