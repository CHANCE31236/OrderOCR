from __future__ import annotations

from dataclasses import dataclass

from src.ocr.schemas import CircleStatus


@dataclass(frozen=True, slots=True)
class QuantityDecision:
    final_box_count: int | None
    needs_review: bool
    reason: str


def _valid_non_negative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def calculate_final_quantity(
    printed_box_count: int | None,
    circle_status: CircleStatus | str,
    handwritten_override: int | None = None,
    override_is_clearly_associated: bool = False,
) -> QuantityDecision:
    """Calculate the final box count without reading the total-quantity column."""
    try:
        status = CircleStatus(circle_status)
    except ValueError:
        return QuantityDecision(None, True, "The circle status is invalid and requires manual review")

    if handwritten_override is not None and not _valid_non_negative_integer(handwritten_override):
        return QuantityDecision(None, True, "The handwritten override is not a non-negative integer")
    if printed_box_count is not None and not _valid_non_negative_integer(printed_box_count):
        return QuantityDecision(None, True, "The printed box count is not a non-negative integer")

    if override_is_clearly_associated:
        if handwritten_override is None:
            return QuantityDecision(None, True, "An associated correction was detected, but its number is uncertain")
        return QuantityDecision(handwritten_override, False, "Used the clearly associated handwritten box-count override")
    if status is CircleStatus.FULL_CIRCLE:
        if printed_box_count is None:
            return QuantityDecision(None, True, "The printed box count is uncertain")
        return QuantityDecision(printed_box_count, False, "The printed box count is surrounded by a closed circle")
    if status is CircleStatus.NO_CIRCLE:
        return QuantityDecision(0, False, "The printed box count is not surrounded by a closed circle")
    return QuantityDecision(None, True, "Circle closure is uncertain and requires manual review")
