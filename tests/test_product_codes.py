import pytest

from src.business.validators import safe_order_filename, validate_product_code
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
        reason="Clear",
    )
    assert row.product_code == code


@pytest.mark.parametrize("code", ["", "   ", "ABC\x00"])
def test_empty_or_control_character_product_codes_are_rejected(code):
    with pytest.raises(ValueError):
        validate_product_code(code)


@pytest.mark.parametrize("name", ["CON", "con.txt", "NUL", "AUX", "PRN", "COM1", "LPT9", "COM¹", " ", "A/1", "A."])
def test_invalid_windows_order_filenames_are_rejected(name):
    with pytest.raises(ValueError):
        safe_order_filename(name)


@pytest.mark.parametrize("name", ["Vs20260713-12", "CONTRACT-1", "COM10", "订单-1"])
def test_valid_order_filenames_are_preserved(name):
    assert safe_order_filename(name) == name
