from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.schemas import (
    CalculationDetailResponse,
    CalculationHistoryResponse,
    CourtFeeRequest,
    DeadlineRequest,
    FullCalculationRequest,
    FullCalculationResponse,
    FullCalculationResult,
    LimitationRequest,
    PenaltyRequest,
)
from app.services.audit import log_action
from app.services.calculation_runs import create_calculation_run, get_calculation_run, list_calculation_runs
from app.services.calculators import (
    calculate_court_fee,
    calculate_deadline,
    calculate_limitation_deadline,
    calculate_penalty,
)
from app.services.subscriptions import get_or_create_user

router = APIRouter(prefix="/api/calculate", tags=["calculate"])


@router.post("/court-fee")
def court_fee(payload: CourtFeeRequest) -> dict[str, float]:
    fee = calculate_court_fee(
        claim_amount_uah=payload.claim_amount_uah,
        rate=payload.rate,
        min_fee_uah=payload.min_fee_uah,
    )
    return {"court_fee_uah": fee}


@router.post("/penalty")
def penalty(payload: PenaltyRequest) -> dict[str, float]:
    value = calculate_penalty(
        principal_uah=payload.principal_uah,
        debt_start_date=payload.debt_start_date,
        debt_end_date=payload.debt_end_date,
        annual_rate=payload.annual_rate,
    )
    return {"penalty_uah": value}


@router.post("/deadline")
def deadline(payload: DeadlineRequest) -> dict[str, date]:
    return {"deadline": calculate_deadline(payload.start_date, payload.days)}


@router.post("/limitation")
def limitation(payload: LimitationRequest) -> dict[str, date]:
    return {"limitation_deadline": calculate_limitation_deadline(payload.violation_date, payload.years)}


def _serialize_calculation_row(row) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "calculation_type": row.calculation_type,
        "title": row.title,
        "input_payload": row.input_payload or {},
        "output_payload": row.output_payload or {},
        "notes": row.notes,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


@router.post("/full", response_model=FullCalculationResponse)
def full_calculation(
    payload: FullCalculationRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FullCalculationResponse:
    get_or_create_user(db, user)
    court_fee = calculate_court_fee(
        claim_amount_uah=payload.claim_amount_uah,
        rate=payload.court_fee_rate,
        min_fee_uah=payload.court_fee_min_uah,
    )
    penalty = calculate_penalty(
        principal_uah=payload.principal_uah,
        debt_start_date=payload.debt_start_date,
        debt_end_date=payload.debt_end_date,
        annual_rate=payload.annual_penalty_rate,
    )
    process_deadline = calculate_deadline(payload.process_start_date, payload.process_days)
    limitation_deadline = calculate_limitation_deadline(payload.violation_date, payload.limitation_years)
    total_claim_uah = round(float(payload.claim_amount_uah) + float(penalty), 2)
    total_with_fee_uah = round(total_claim_uah + float(court_fee), 2)

    result = FullCalculationResult(
        court_fee_uah=court_fee,
        penalty_uah=penalty,
        process_deadline=process_deadline,
        limitation_deadline=limitation_deadline,
        total_claim_uah=total_claim_uah,
        total_with_fee_uah=total_with_fee_uah,
    )

    input_payload = {
        "claim_amount_uah": payload.claim_amount_uah,
        "principal_uah": payload.principal_uah,
        "debt_start_date": payload.debt_start_date.isoformat(),
        "debt_end_date": payload.debt_end_date.isoformat(),
        "process_start_date": payload.process_start_date.isoformat(),
        "process_days": payload.process_days,
        "violation_date": payload.violation_date.isoformat(),
        "limitation_years": payload.limitation_years,
        "court_fee_rate": payload.court_fee_rate,
        "court_fee_min_uah": payload.court_fee_min_uah,
        "annual_penalty_rate": payload.annual_penalty_rate,
    }
    output_payload = {
        "court_fee_uah": result.court_fee_uah,
        "penalty_uah": result.penalty_uah,
        "process_deadline": result.process_deadline.isoformat(),
        "limitation_deadline": result.limitation_deadline.isoformat(),
        "total_claim_uah": result.total_claim_uah,
        "total_with_fee_uah": result.total_with_fee_uah,
    }

    calculation_id: str | None = None
    created_at: str | None = None
    if payload.save:
        saved = create_calculation_run(
            db,
            user_id=user.user_id,
            calculation_type="full_claim",
            title=payload.title,
            input_payload=input_payload,
            output_payload=output_payload,
            notes=payload.notes,
        )
        calculation_id = saved.id
        created_at = saved.created_at.isoformat()

    log_action(
        db,
        user_id=user.user_id,
        action="calculate_full",
        entity_type="calculation_run",
        entity_id=calculation_id,
        metadata={
            "save": payload.save,
            "court_fee_uah": result.court_fee_uah,
            "penalty_uah": result.penalty_uah,
            "total_with_fee_uah": result.total_with_fee_uah,
        },
    )

    return FullCalculationResponse(
        status="ok",
        result=result,
        saved=bool(calculation_id),
        calculation_id=calculation_id,
        created_at=created_at,
    )


@router.get("/history", response_model=CalculationHistoryResponse)
def calculation_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    calculation_type: str | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CalculationHistoryResponse:
    get_or_create_user(db, user)
    rows, total, normalized_page, pages = list_calculation_runs(
        db,
        user_id=user.user_id,
        calculation_type=calculation_type,
        page=page,
        page_size=page_size,
    )
    log_action(
        db,
        user_id=user.user_id,
        action="calculate_history",
        entity_type="calculation_run",
        entity_id=None,
        metadata={
            "page": normalized_page,
            "page_size": page_size,
            "calculation_type": calculation_type,
            "returned": len(rows),
            "total": total,
        },
    )
    return CalculationHistoryResponse(
        total=total,
        page=normalized_page,
        page_size=page_size,
        pages=pages,
        items=[_serialize_calculation_row(item) for item in rows],
    )


@router.get("/{calculation_id}", response_model=CalculationDetailResponse)
def calculation_detail(
    calculation_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CalculationDetailResponse:
    get_or_create_user(db, user)
    row = get_calculation_run(db, user_id=user.user_id, calculation_id=calculation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Calculation not found")
    log_action(
        db,
        user_id=user.user_id,
        action="calculate_detail",
        entity_type="calculation_run",
        entity_id=row.id,
        metadata={"calculation_type": row.calculation_type},
    )
    return CalculationDetailResponse(item=_serialize_calculation_row(row))
