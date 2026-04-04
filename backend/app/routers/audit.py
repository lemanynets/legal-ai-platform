from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import AuditLog
from app.schemas import AuditHistoryResponse, AuditIntegrityResponse
from app.services.access_control import ensure_user_role
from app.services.audit import log_action, verify_audit_integrity_chain


router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/history", response_model=AuditHistoryResponse)
def audit_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    query: str | None = Query(default=None),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuditHistoryResponse:
    filters = [AuditLog.user_id == user.user_id]
    normalized_action = (action or "").strip()
    if normalized_action:
        filters.append(AuditLog.action == normalized_action)

    normalized_entity_type = (entity_type or "").strip()
    if normalized_entity_type:
        filters.append(AuditLog.entity_type == normalized_entity_type)

    normalized_query = (query or "").strip()
    if normalized_query:
        like_value = f"%{normalized_query}%"
        filters.append(
            or_(
                AuditLog.action.ilike(like_value),
                AuditLog.entity_type.ilike(like_value),
                AuditLog.entity_id.ilike(like_value),
            )
        )

    total = int(db.execute(select(func.count()).select_from(AuditLog).where(*filters)).scalar_one() or 0)
    pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    normalized_page = max(1, min(page, pages))
    direction = asc if sort_dir == "asc" else desc

    rows = list(
        db.execute(
            select(AuditLog)
            .where(*filters)
            .order_by(direction(AuditLog.created_at), desc(AuditLog.id))
            .offset((normalized_page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    return AuditHistoryResponse(
        user_id=user.user_id,
        total=total,
        page=normalized_page,
        page_size=page_size,
        pages=pages,
        action=normalized_action or None,
        entity_type=normalized_entity_type or None,
        query=normalized_query or None,
        items=[
            {
                "id": row.id,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "metadata": row.metadata_json or {},
                "integrity_scope": row.integrity_scope,
                "integrity_prev_hash": row.integrity_prev_hash,
                "integrity_hash": row.integrity_hash,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    )


@router.get("/integrity", response_model=AuditIntegrityResponse)
def audit_integrity_check(
    max_rows: int = Query(default=2000, ge=10, le=20000),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuditIntegrityResponse:
    ensure_user_role(
        db,
        current_user=user,
        allowed_roles={"owner", "admin", "analyst"},
        reason="audit integrity check",
    )
    result = verify_audit_integrity_chain(
        db,
        user_id=user.user_id,
        limit=max_rows,
    )
    log_action(
        db,
        user_id=user.user_id,
        action="audit_integrity_check",
        entity_type="audit_log",
        metadata={
            "scope": result.get("scope"),
            "status": result.get("status"),
            "rows_total": result.get("rows_total"),
            "rows_checked": result.get("rows_checked"),
            "truncated": result.get("truncated"),
            "issues_count": len(result.get("issues") or []),
        },
    )
    return AuditIntegrityResponse(**result)
