from __future__ import annotations

import re
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models.case import Case
from app.services.audit import log_action
from app.services.case_law_cache import search_case_law, upsert_case_law_records
from app.services.entitlements import ensure_feature_access
from app.services.opendatabot_client import OpendatabotError, opendatabot

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _normalize_decision_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"\d{4}-\d{2}-\d{2}", str(value).strip())
    return match.group(0) if match else None


def _build_decision_id(case_number: str, decision: dict[str, Any], index: int, stage_key: str | None = None) -> str:
    explicit = str(decision.get("id") or "").strip()
    if explicit:
        return explicit

    link = str(decision.get("url") or "").strip()
    if link:
        tail = [chunk for chunk in link.split("/") if chunk]
        if tail:
            return f"odb-{tail[-1]}"

    date_part = _normalize_decision_date(str(decision.get("date") or "")) or "undated"
    type_part = str(decision.get("type") or "decision").strip().lower().replace(" ", "-")
    return f"odb-{case_number}-{stage_key or 'general'}-{date_part}-{type_part}-{index + 1}"


def _build_case_law_records_from_case_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    case_number = str(payload.get("number") or "").strip()
    court_name = str(payload.get("court") or "").strip() or None
    proceeding_type = str(payload.get("proceeding_type") or "").strip()
    subject = str(payload.get("subject") or "").strip()
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    def push_record(decision: dict[str, Any], index: int, *, stage_key: str | None = None, stage_court_name: str | None = None, court_type: str | None = None) -> None:
        decision_id = _build_decision_id(case_number, decision, index, stage_key)
        if decision_id in seen:
            return
        seen.add(decision_id)
        records.append(
            {
                "source": "opendatabot",
                "decision_id": decision_id,
                "court_name": stage_court_name or court_name,
                "court_type": court_type,
                "decision_date": _normalize_decision_date(str(decision.get("date") or "")),
                "case_number": case_number or None,
                "subject_categories": [item for item in (proceeding_type, subject) if item],
                "legal_positions": {
                    "opendatabot_url": str(decision.get("url") or "").strip() or None,
                    "document_type": str(decision.get("type") or "").strip() or None,
                    "stage": stage_key,
                },
                "summary": str(decision.get("summary") or "").strip() or None,
            }
        )

    decisions = payload.get("decisions") or []
    if isinstance(decisions, list):
        for index, decision in enumerate(decisions):
            if isinstance(decision, dict):
                push_record(decision, index)

    stages = payload.get("stages") or {}
    if isinstance(stages, dict):
        for stage_key, stage_payload in stages.items():
            if not isinstance(stage_payload, dict):
                continue
            stage_decisions = stage_payload.get("decisions") or []
            stage_court_name = str(stage_payload.get("court_name") or "").strip() or None
            court_type = str(stage_key).strip().lower() or None
            if isinstance(stage_decisions, list):
                for index, decision in enumerate(stage_decisions):
                    if isinstance(decision, dict):
                        push_record(
                            decision,
                            index,
                            stage_key=str(stage_key),
                            stage_court_name=stage_court_name,
                            court_type=court_type,
                        )

    return records

class CaseCreate(BaseModel):
    title: str
    description: str | None = None
    case_number: str | None = None

@router.get("")
def get_cases(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    cases = db.query(Case).filter(Case.user_id == user.user_id).order_by(Case.created_at.desc()).all()
    return [c.to_dict() for c in cases]

@router.post("")
def create_case(
    payload: CaseCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    case = Case(
        user_id=user.user_id,
        title=payload.title,
        description=payload.description,
        case_number=payload.case_number
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case.to_dict()

@router.get("/{case_id}")
def get_case(
    case_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    case = db.query(Case).filter(Case.id == case_id, Case.user_id == user.user_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    res = case.to_dict()
    res["documents"] = [
        {
            "id": d.id,
            "document_type": d.document_type,
            "document_category": d.document_category,
            "created_at": d.created_at.isoformat()
        }
        for d in case.documents
    ]
    res["forum_posts"] = [
        {
            "id": p.id,
            "title": p.title,
            "created_at": p.created_at.isoformat()
        }
        for p in case.forum_posts
    ]
    case_law_items: list[dict[str, Any]] = []
    if case.case_number:
        result = search_case_law(
            db,
            query=case.case_number,
            page=1,
            page_size=8,
            sort_by="decision_date",
            sort_dir="desc",
        )
        case_law_items = [
            {
                "id": row.id,
                "source": row.source,
                "decision_id": row.decision_id,
                "court_name": row.court_name,
                "court_type": row.court_type,
                "decision_date": row.decision_date.isoformat() if row.decision_date else None,
                "case_number": row.case_number,
                "subject_categories": row.subject_categories or [],
                "legal_positions": row.legal_positions or {},
                "summary": row.summary,
                "reference_count": int(row.reference_count or 0),
            }
            for row in result.items
        ]
    res["case_law_items"] = case_law_items
    return res


@router.post("/{case_id}/sync-decisions")
def sync_case_decisions(
    case_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    case = db.query(Case).filter(Case.id == case_id, Case.user_id == user.user_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not case.case_number or not case.case_number.strip():
        raise HTTPException(status_code=422, detail="Case number is required to sync decisions")

    ensure_feature_access(db, current_user=user, feature="case_law_import")

    normalized_number = case.case_number.strip()
    try:
        payload = opendatabot.get_court_case(normalized_number)
        log_action(
            db,
            user_id=user.user_id,
            action="opendatabot_court_case_lookup",
            entity_type="opendatabot_court_case",
            entity_id=normalized_number,
            metadata={"status": "ok", "source": "case_sync"},
        )
        records = _build_case_law_records_from_case_payload(payload)
        stats = upsert_case_law_records(db, records)
        log_action(
            db,
            user_id=user.user_id,
            action="case_law_import",
            entity_type="case_law_cache",
            entity_id=case_id,
            metadata={
                "source": "case_sync",
                "case_number": normalized_number,
                "records_in": len(records),
                "created": stats.created,
                "updated": stats.updated,
            },
        )
        return {
            "status": "ok",
            "case_id": case_id,
            "case_number": normalized_number,
            "records_in": len(records),
            "created": stats.created,
            "updated": stats.updated,
            "total": stats.total,
        }
    except OpendatabotError as exc:
        detail = str(exc)
        log_action(
            db,
            user_id=user.user_id,
            action="opendatabot_court_case_lookup",
            entity_type="opendatabot_court_case",
            entity_id=normalized_number,
            metadata={"status": "error", "source": "case_sync", "detail": detail[:200]},
        )
        raise HTTPException(status_code=502, detail=detail)

class CaseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    case_number: str | None = None

@router.patch("/{case_id}")
def update_case(
    case_id: str,
    payload: CaseUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    case = db.query(Case).filter(Case.id == case_id, Case.user_id == user.user_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if payload.title is not None:
        case.title = payload.title
    if payload.description is not None:
        case.description = payload.description
    if payload.case_number is not None:
        case.case_number = payload.case_number
        
    db.commit()
    db.refresh(case)
    return case.to_dict()

@router.delete("/{case_id}")
def delete_case(
    case_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    case = db.query(Case).filter(Case.id == case_id, Case.user_id == user.user_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(case)
    db.commit()
    return {"status": "ok"}
