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
    """严格按业务规则计算最终箱数，不读取“数量”列。"""
    try:
        status = CircleStatus(circle_status)
    except ValueError:
        return QuantityDecision(None, True, "圈圈状态无效，必须人工确认")

    if handwritten_override is not None and not _valid_non_negative_integer(handwritten_override):
        return QuantityDecision(None, True, "手写修正不是非负整数")
    if printed_box_count is not None and not _valid_non_negative_integer(printed_box_count):
        return QuantityDecision(None, True, "原箱数不是非负整数")

    if override_is_clearly_associated:
        if handwritten_override is None:
            return QuantityDecision(None, True, "检测到关联修正但无法确定手写数字")
        return QuantityDecision(handwritten_override, False, "采用明确关联的手写修正箱数")
    if status is CircleStatus.FULL_CIRCLE:
        if printed_box_count is None:
            return QuantityDecision(None, True, "原箱数无法确定")
        return QuantityDecision(printed_box_count, False, "原箱数被完整闭合圈包围")
    if status is CircleStatus.NO_CIRCLE:
        return QuantityDecision(0, False, "原箱数没有被完整闭合圈包围")
    return QuantityDecision(None, True, "圈圈是否闭合不确定，必须人工确认")

