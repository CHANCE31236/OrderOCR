from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class CircleStatus(str, Enum):
    FULL_CIRCLE = "full_circle"
    NO_CIRCLE = "no_circle"
    UNCERTAIN = "uncertain"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, use_enum_values=True)


class RowObservation(StrictModel):
    row_number: NonNegativeInt
    product_code: str
    printed_box_count: NonNegativeInt | None
    printed_total_quantity: NonNegativeInt | None = None
    circle_status: CircleStatus
    handwritten_override: NonNegativeInt | None = None
    override_is_clearly_associated: bool = False
    calculated_final_box_count: NonNegativeInt | None = None
    product_code_confidence: Confidence
    circle_confidence: Confidence
    overall_confidence: Confidence
    needs_review: bool
    reason: str = Field(min_length=1, max_length=1000)
    source_image: str = ""
    row_crop: str = ""

    @field_validator("product_code")
    @classmethod
    def product_code_must_be_literal_and_nonempty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("货号不能为空")
        if any(ord(ch) < 32 for ch in value):
            raise ValueError("货号包含控制字符")
        return value


class PageExtraction(StrictModel):
    order_number: str
    page_number: NonNegativeInt | None
    total_pages: NonNegativeInt | None
    rows: list[RowObservation]
    page_confidence: Confidence = 0.0
    needs_review: bool = False
    reason: str = ""

    @field_validator("order_number")
    @classmethod
    def order_number_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("订单号不能为空")
        return value.strip()


class RowVerification(StrictModel):
    row_number: NonNegativeInt
    product_code: str
    printed_box_count: NonNegativeInt | None
    circle_status: CircleStatus
    handwritten_override: NonNegativeInt | None = None
    override_is_clearly_associated: bool = False
    proposed_final_box_count: NonNegativeInt | None = None
    product_code_confidence: Confidence
    circle_confidence: Confidence
    overall_confidence: Confidence
    needs_review: bool
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("product_code")
    @classmethod
    def product_code_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("货号不能为空")
        return value


class OrderNumberExtraction(StrictModel):
    order_number: str | None
    page_number: NonNegativeInt | None
    total_pages: NonNegativeInt | None
    confidence: Confidence
    needs_review: bool
    reason: str


class ReviewedRow(StrictModel):
    observation: RowObservation
    verification: RowVerification | None = None
    final_box_count: NonNegativeInt | None = None
    needs_review: bool = True
    manually_confirmed: bool = False
    status: str = "需要人工确认"
    review_reason: str = ""

