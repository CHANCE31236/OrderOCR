import pytest

from src.business.quantity_rules import calculate_final_quantity


def test_full_circle_keeps_printed_box_count():
    result = calculate_final_quantity(10, "full_circle", None, False)
    assert result.final_box_count == 10
    assert result.needs_review is False


def test_no_circle_means_zero_even_with_stray_marks():
    result = calculate_final_quantity(2, "no_circle", None, False)
    assert result.final_box_count == 0
    assert result.needs_review is False


def test_clear_handwriting_has_highest_priority():
    result = calculate_final_quantity(10, "full_circle", 6, True)
    assert result.final_box_count == 6


def test_uncertain_circle_blocks_automatic_export():
    result = calculate_final_quantity(2, "uncertain", None, False)
    assert result.final_box_count is None
    assert result.needs_review is True


def test_quantity_column_is_not_an_argument_and_cannot_override_box_count():
    printed_total_quantity = 150
    result = calculate_final_quantity(5, "full_circle", None, False)
    assert printed_total_quantity == 150
    assert result.final_box_count == 5


@pytest.mark.parametrize("value", [-1, 1.5, True])
def test_invalid_counts_are_never_accepted(value):
    assert calculate_final_quantity(value, "full_circle").needs_review is True


def test_associated_override_without_readable_number_needs_review():
    result = calculate_final_quantity(10, "full_circle", None, True)
    assert result.final_box_count is None
    assert result.needs_review

