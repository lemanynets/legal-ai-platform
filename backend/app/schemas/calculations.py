from __future__ import annotations
from datetime import date
from typing import Any
from pydantic import BaseModel, Field

class CourtFeeRequest(BaseModel):
    claim_amount_uah: float = Field(gt=0)
    rate: float = 0.015
    min_fee_uah: float = 1211.20


class PenaltyRequest(BaseModel):
    principal_uah: float = Field(gt=0)
    debt_start_date: date
    debt_end_date: date
    annual_rate: float = 0.03


class DeadlineRequest(BaseModel):
    start_date: date
    days: int = Field(gt=0, le=3650)


class LimitationRequest(BaseModel):
    violation_date: date
    years: int = Field(default=3, ge=1, le=20)


class FullCalculationRequest(BaseModel):
    claim_amount_uah: float = Field(gt=0)
    principal_uah: float = Field(gt=0)
    debt_start_date: date
    debt_end_date: date
    process_start_date: date
    process_days: int = Field(default=30, ge=1, le=3650)
    violation_date: date
    limitation_years: int = Field(default=3, ge=1, le=20)
    court_fee_rate: float = Field(default=0.015, gt=0, le=1)
    court_fee_min_uah: float = Field(default=1211.20, ge=0)
    annual_penalty_rate: float = Field(default=0.03, ge=0, le=1)
    save: bool = True
    title: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)


class FullCalculationResult(BaseModel):
    court_fee_uah: float
    penalty_uah: float
    process_deadline: date
    limitation_deadline: date
    total_claim_uah: float
    total_with_fee_uah: float


class FullCalculationResponse(BaseModel):
    status: str
    result: FullCalculationResult
    saved: bool
    calculation_id: str | None = None
    created_at: str | None = None


class CalculationHistoryItem(BaseModel):
    id: str
    user_id: str
    calculation_type: str
    title: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    created_at: str
    updated_at: str


class CalculationHistoryResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
    items: list[CalculationHistoryItem] = Field(default_factory=list)


class CalculationDetailResponse(BaseModel):
    item: CalculationHistoryItem
