from __future__ import annotations

from src.business.quantity_rules import calculate_final_quantity
from src.ocr.schemas import ReviewedRow, RowObservation, RowVerification


def reconcile_row(first: RowObservation, second: RowVerification | None, minimum_confidence: float) -> ReviewedRow:
    decision = calculate_final_quantity(
        first.printed_box_count,
        first.circle_status,
        first.handwritten_override,
        first.override_is_clearly_associated,
    )
    reasons: list[str] = [decision.reason]
    needs_review = first.needs_review or decision.needs_review or first.overall_confidence < minimum_confidence

    if second is not None:
        fields_match = (
            first.product_code == second.product_code
            and first.printed_box_count == second.printed_box_count
            and str(first.circle_status) == str(second.circle_status)
            and first.handwritten_override == second.handwritten_override
            and first.override_is_clearly_associated == second.override_is_clearly_associated
        )
        second_decision = calculate_final_quantity(
            second.printed_box_count,
            second.circle_status,
            second.handwritten_override,
            second.override_is_clearly_associated,
        )
        if not fields_match or second_decision.final_box_count != decision.final_box_count:
            needs_review = True
            reasons.append("两次识别结果不一致")
        if second.needs_review or second.overall_confidence < minimum_confidence:
            needs_review = True
            reasons.append("二次复核置信度不足")

    if needs_review:
        status = "需要人工确认" if decision.needs_review or (second is not None and "两次识别结果不一致" in reasons) else "建议检查"
    else:
        status = "已自动确认"
    return ReviewedRow(
        observation=first,
        verification=second,
        final_box_count=decision.final_box_count,
        needs_review=needs_review,
        manually_confirmed=False,
        status=status,
        review_reason="；".join(dict.fromkeys(reasons)),
    )

