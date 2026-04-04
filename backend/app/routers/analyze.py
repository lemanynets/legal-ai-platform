from __future__ import annotations

import asyncio
import hashlib
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.schemas import (
    AnalyzeBatchProcessRequest,
    AnalyzeProcessRequest,
    ContractAnalysisHistoryResponse,
    ContractAnalysisItem,
    GdprCheckRequest,
    GdprCheckResponse,
)
from app.services.audit import log_action
from app.services.contract_analyses import (
    analyze_contract_text,
    create_analysis_cache,
    create_contract_analysis,
    delete_contract_analysis,
    get_analysis_cache,
    get_contract_analysis,
    list_contract_analyses,
)
from app.services.realtime import publish_user_event
from app.services.subscriptions import (
    ensure_analysis_quota,
    get_or_create_subscription,
    mark_analysis_processed,
    to_payload,
)

router = APIRouter(prefix="/api/analyze", tags=["analyze"])

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", flags=re.IGNORECASE
)
_PHONE_RE = re.compile(r"\b(?:\+?\d[\d\-\s().]{7,}\d)\b")
_UA_ID_RE = re.compile(r"\b\d{10}\b")


def _to_item(row, usage: dict | None = None) -> ContractAnalysisItem:
    return ContractAnalysisItem(
        id=row.id,
        user_id=row.user_id,
        file_name=row.file_name,
        file_url=row.file_url,
        file_size=row.file_size,
        contract_type=row.contract_type,
        risk_level=row.risk_level,
        critical_risks=row.critical_risks or [],
        medium_risks=row.medium_risks or [],
        ok_points=row.ok_points or [],
        recommendations=row.recommendations or [],
        ai_model=row.ai_model,
        tokens_used=row.tokens_used,
        processing_time_ms=row.processing_time_ms,
        created_at=row.created_at.isoformat(),
        usage=usage or {},
    )


@router.post("/gdpr-check", response_model=GdprCheckResponse)
def gdpr_check(
    payload: GdprCheckRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GdprCheckResponse:
    text = str(payload.text or "").strip()
    issues: list[str] = []
    if _EMAIL_RE.search(text):
        issues.append("potential_email_detected")
    if _PHONE_RE.search(text):
        issues.append("potential_phone_detected")
    if _UA_ID_RE.search(text):
        issues.append("potential_tax_id_detected")

    compliant = len(issues) == 0
    report = (
        "No obvious personal data markers detected."
        if compliant
        else "Potential personal data markers detected. Review and redact before sharing."
    )

    log_action(
        db,
        user_id=user.user_id,
        action="analysis_gdpr_check",
        entity_type="contract_analysis",
        entity_id=None,
        metadata={"issues": issues, "compliant": compliant},
    )
    return GdprCheckResponse(report=report, compliant=compliant, issues=issues)


@router.post("/process", response_model=ContractAnalysisItem)
async def process_analysis(
    payload: AnalyzeProcessRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContractAnalysisItem:
    subscription = get_or_create_subscription(db, user)
    quota_ok, quota_message = ensure_analysis_quota(subscription)
    if not quota_ok:
        raise HTTPException(status_code=402, detail=quota_message)

    file_hash = hashlib.md5(payload.contract_text.encode("utf-8")).hexdigest()
    cached = get_analysis_cache(db, user.user_id, file_hash)
    if cached:
        analysis_payload = cached.analysis_payload
        ai_model = cached.ai_model
        tokens_used = cached.tokens_used
        processing_time_ms = cached.processing_time_ms
    else:
        (
            analysis_payload,
            ai_model,
            tokens_used,
            processing_time_ms,
        ) = await analyze_contract_text(payload.contract_text, mode=payload.mode)
        create_analysis_cache(
            db,
            user_id=user.user_id,
            file_hash=file_hash,
            analysis_payload=analysis_payload,
            ai_model=ai_model,
            tokens_used=tokens_used,
            processing_time_ms=processing_time_ms,
        )
    row = create_contract_analysis(
        db,
        user_id=user.user_id,
        file_name=payload.file_name,
        file_url=payload.file_url,
        file_size=payload.file_size,
        analysis_payload=analysis_payload,
        ai_model=ai_model,
        tokens_used=tokens_used,
        processing_time_ms=processing_time_ms,
    )
    updated_subscription = mark_analysis_processed(db, subscription)

    log_action(
        db,
        user_id=user.user_id,
        action="analysis_process",
        entity_type="contract_analysis",
        entity_id=row.id,
        metadata={
            "risk_level": row.risk_level,
            "ai_model": row.ai_model,
            "tokens_used": row.tokens_used,
        },
    )
    publish_user_event(
        user.user_id,
        "analysis.completed",
        {
            "analysis_id": row.id,
            "mode": payload.mode,
            "risk_level": row.risk_level,
            "cached": cached is not None,
        },
    )
    return _to_item(row, usage=to_payload(updated_subscription))


@router.post("/batch-process", response_model=list[ContractAnalysisItem])
async def batch_process_analysis(
    payload: AnalyzeBatchProcessRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ContractAnalysisItem]:
    subscription = get_or_create_subscription(db, user)
    total_items = len(payload.items)
    quota_needed = total_items
    quota_ok, quota_message = ensure_analysis_quota(subscription, quota_needed)
    if not quota_ok:
        raise HTTPException(status_code=402, detail=quota_message)

    async def process_single(item: AnalyzeProcessRequest) -> ContractAnalysisItem:
        file_hash = hashlib.md5(item.contract_text.encode("utf-8")).hexdigest()
        cached = get_analysis_cache(db, user.user_id, file_hash)
        if cached:
            analysis_payload = cached.analysis_payload
            ai_model = cached.ai_model
            tokens_used = cached.tokens_used
            processing_time_ms = cached.processing_time_ms
        else:
            (
                analysis_payload,
                ai_model,
                tokens_used,
                processing_time_ms,
            ) = await analyze_contract_text(item.contract_text, mode=item.mode)
            create_analysis_cache(
                db,
                user_id=user.user_id,
                file_hash=file_hash,
                analysis_payload=analysis_payload,
                ai_model=ai_model,
                tokens_used=tokens_used,
                processing_time_ms=processing_time_ms,
            )
        row = create_contract_analysis(
            db,
            user_id=user.user_id,
            file_name=item.file_name,
            file_url=item.file_url,
            file_size=item.file_size,
            analysis_payload=analysis_payload,
            ai_model=ai_model,
            tokens_used=tokens_used,
            processing_time_ms=processing_time_ms,
        )
        log_action(
            db,
            user_id=user.user_id,
            action="analysis_process",
            entity_type="contract_analysis",
            entity_id=row.id,
            metadata={
                "risk_level": row.risk_level,
                "ai_model": row.ai_model,
                "tokens_used": row.tokens_used,
            },
        )
        return _to_item(row)

    results = await asyncio.gather(*[process_single(item) for item in payload.items])
    updated_subscription = mark_analysis_processed(db, subscription, quota_needed)
    publish_user_event(
        user.user_id,
        "analysis.batch_completed",
        {
            "count": len(results),
            "mode": payload.items[0].mode if payload.items else "standard",
        },
    )
    # Update usage in results if needed, but for simplicity, return as is
    return results


@router.get("/history", response_model=ContractAnalysisHistoryResponse)
def analysis_history(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContractAnalysisHistoryResponse:
    subscription = get_or_create_subscription(db, user)
    rows = list_contract_analyses(db, user.user_id)
    items = [_to_item(row) for row in rows]
    return ContractAnalysisHistoryResponse(
        total=len(items), items=items, usage=to_payload(subscription)
    )


@router.get("/{analysis_id}", response_model=ContractAnalysisItem)
def analysis_get(
    analysis_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContractAnalysisItem:
    row = get_contract_analysis(db, user.user_id, analysis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    subscription = get_or_create_subscription(db, user)
    return _to_item(row, usage=to_payload(subscription))


@router.delete("/{analysis_id}")
def analysis_delete(
    analysis_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    ok = delete_contract_analysis(db, user.user_id, analysis_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    log_action(
        db,
        user_id=user.user_id,
        action="analysis_delete",
        entity_type="contract_analysis",
        entity_id=analysis_id,
    )
    return {"status": "deleted", "id": analysis_id}
