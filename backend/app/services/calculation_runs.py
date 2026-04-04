from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import CalculationRun


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_calculation_run(
    db: Session,
    *,
    user_id: str,
    calculation_type: str,
    title: str | None,
    input_payload: dict,
    output_payload: dict,
    notes: str | None = None,
) -> CalculationRun:
    row = CalculationRun(
        user_id=user_id,
        calculation_type=(calculation_type or "full_claim").strip().lower(),
        title=(title or "").strip() or None,
        input_payload=input_payload,
        output_payload=output_payload,
        notes=(notes or "").strip() or None,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_calculation_runs(
    db: Session,
    *,
    user_id: str,
    calculation_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[CalculationRun], int, int, int]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))
    stmt = select(CalculationRun).where(CalculationRun.user_id == user_id)

    normalized_type = (calculation_type or "").strip().lower()
    if normalized_type:
        stmt = stmt.where(CalculationRun.calculation_type == normalized_type)

    total = int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one() or 0)
    pages = max(1, math.ceil(total / safe_page_size)) if total > 0 else 1
    if safe_page > pages:
        safe_page = pages

    rows = list(
        db.execute(
            stmt.order_by(desc(CalculationRun.created_at), desc(CalculationRun.id))
            .offset((safe_page - 1) * safe_page_size)
            .limit(safe_page_size)
        )
        .scalars()
        .all()
    )
    return rows, total, safe_page, pages


def get_calculation_run(db: Session, *, user_id: str, calculation_id: str) -> CalculationRun | None:
    return db.execute(
        select(CalculationRun)
        .where(CalculationRun.id == calculation_id, CalculationRun.user_id == user_id)
        .limit(1)
    ).scalar_one_or_none()
