from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.database import get_db
from app.models import AuditLog, CaseLawCache
from app.services.audit import log_action
from app.services.opendatabot_client import OpendatabotError, opendatabot

router = APIRouter(prefix="/api/opendatabot", tags=["opendatabot"])

USAGE_ACTIONS = {
    "opendatabot_company_lookup",
    "opendatabot_court_case_lookup",
    "opendatabot_court_decisions_search",
}

CACHE_SOURCE_COMPANY = "opendatabot_company_payload"
CACHE_SOURCE_COURT_CASE = "opendatabot_court_case_payload"


def _load_cached_payload(db: Session, *, source: str, key: str) -> dict[str, Any] | None:
    row = db.execute(
        select(CaseLawCache).where(
            CaseLawCache.source == source,
            CaseLawCache.decision_id == key,
        )
    ).scalar_one_or_none()
    if not row or not isinstance(row.legal_positions, dict):
        return None
    payload = row.legal_positions.get("payload")
    if isinstance(payload, dict):
        return payload
    return None


def _store_cached_payload(
    db: Session,
    *,
    source: str,
    key: str,
    payload: dict[str, Any],
    case_number: str | None = None,
) -> None:
    row = db.execute(
        select(CaseLawCache).where(
            CaseLawCache.source == source,
            CaseLawCache.decision_id == key,
        )
    ).scalar_one_or_none()
    if row is None:
        row = CaseLawCache(
            source=source,
            decision_id=key,
            case_number=case_number,
            legal_positions={"payload": payload},
            subject_categories=["opendatabot_cache"],
            summary="Cached OpenDataBot response payload",
        )
    else:
        row.case_number = case_number
        row.legal_positions = {"payload": payload}
        row.subject_categories = ["opendatabot_cache"]
        row.summary = "Cached OpenDataBot response payload"
    db.add(row)
    db.commit()


def _usage_payload(db: Session) -> dict[str, Any]:
    used = int(
        db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.action.in_(tuple(USAGE_ACTIONS)))).scalar_one()
        or 0
    )
    limit = int(settings.opendatabot_request_limit or 20)
    remaining = max(limit - used, 0)
    return {
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "expires_at": settings.opendatabot_expires_at or None,
        "api_url": settings.opendatabot_api_url,
    }


@router.get("/usage")
def get_opendatabot_usage(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return _usage_payload(db)


@router.get("/company/{code}")
def get_company_details(
    code: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    normalized_code = code.strip()
    cached_payload = _load_cached_payload(db, source=CACHE_SOURCE_COMPANY, key=normalized_code)
    if cached_payload is not None:
        log_action(
            db,
            user_id=user.user_id,
            action="opendatabot_company_cache_hit",
            entity_type="opendatabot_company",
            entity_id=normalized_code,
            metadata={"status": "ok", "cache_hit": True},
        )
        return cached_payload

    try:
        details = opendatabot.get_company_details(normalized_code)
        if not details:
            raise HTTPException(status_code=404, detail="Company not found")
        _store_cached_payload(
            db,
            source=CACHE_SOURCE_COMPANY,
            key=normalized_code,
            payload=details,
        )
        log_action(
            db,
            user_id=user.user_id,
            action="opendatabot_company_lookup",
            entity_type="opendatabot_company",
            entity_id=normalized_code,
            metadata={"status": "ok"},
        )
        return details
    except HTTPException:
        raise
    except Exception as exc:
        log_action(
            db,
            user_id=user.user_id,
            action="opendatabot_company_lookup",
            entity_type="opendatabot_company",
            entity_id=normalized_code,
            metadata={"status": "error", "detail": str(exc)[:200]},
        )
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/court-cases/{number:path}")
def get_court_case(
    number: str,
    judgment_code: int | None = Query(default=None, ge=1, le=5),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not number or not number.strip():
        raise HTTPException(status_code=422, detail="Номер справи не може бути порожнім.")

    normalized_number = number.strip()
    cache_key = f"{normalized_number}::{judgment_code or 0}"
    cached_payload = _load_cached_payload(db, source=CACHE_SOURCE_COURT_CASE, key=cache_key)
    if cached_payload is not None:
        log_action(
            db,
            user_id=user.user_id,
            action="opendatabot_court_case_cache_hit",
            entity_type="opendatabot_court_case",
            entity_id=normalized_number,
            metadata={"status": "ok", "cache_hit": True, "judgment_code": judgment_code},
        )
        return cached_payload

    try:
        payload = opendatabot.get_court_case(normalized_number, judgment_code=judgment_code)
        _store_cached_payload(
            db,
            source=CACHE_SOURCE_COURT_CASE,
            key=cache_key,
            payload=payload,
            case_number=normalized_number,
        )
        log_action(
            db,
            user_id=user.user_id,
            action="opendatabot_court_case_lookup",
            entity_type="opendatabot_court_case",
            entity_id=normalized_number,
            metadata={"status": "ok", "judgment_code": judgment_code},
        )
        return payload
    except OpendatabotError as exc:
        detail = str(exc)
        lowered = detail.lower()
        log_action(
            db,
            user_id=user.user_id,
            action="opendatabot_court_case_lookup",
            entity_type="opendatabot_court_case",
            entity_id=normalized_number,
            metadata={"status": "error", "judgment_code": judgment_code, "detail": detail[:200]},
        )
        if "не знайдено" in lowered:
            raise HTTPException(status_code=404, detail=detail)
        if "неунікальний" in lowered:
            raise HTTPException(status_code=400, detail=detail)
        if "ключ" in lowered or "api-key" in lowered:
            raise HTTPException(status_code=401, detail=detail)
        if "ліміт" in lowered or "429" in lowered:
            raise HTTPException(status_code=429, detail=detail)
        raise HTTPException(status_code=502, detail=detail)
    except Exception as exc:
        log_action(
            db,
            user_id=user.user_id,
            action="opendatabot_court_case_lookup",
            entity_type="opendatabot_court_case",
            entity_id=normalized_number,
            metadata={"status": "error", "judgment_code": judgment_code, "detail": str(exc)[:200]},
        )
        raise HTTPException(status_code=500, detail=f"Внутрішня помилка: {exc}")


@router.get("/court-decisions/search")
def search_court_decisions(
    q: str = Query(..., description="Пошуковий запит (номер справи або ключові слова)"),
    limit: int = Query(default=20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        items = opendatabot.search_court_decisions(q, limit=limit)
        log_action(
            db,
            user_id=user.user_id,
            action="opendatabot_court_decisions_search",
            entity_type="opendatabot_court_search",
            entity_id=q[:36],
            metadata={"status": "ok", "query": q, "limit": limit, "items": len(items)},
        )
        return {"items": items, "total": len(items), "query": q, "usage": _usage_payload(db)}
    except Exception as exc:
        log_action(
            db,
            user_id=user.user_id,
            action="opendatabot_court_decisions_search",
            entity_type="opendatabot_court_search",
            entity_id=q[:36],
            metadata={"status": "error", "query": q, "limit": limit, "detail": str(exc)[:200]},
        )
        raise HTTPException(status_code=500, detail=str(exc))
