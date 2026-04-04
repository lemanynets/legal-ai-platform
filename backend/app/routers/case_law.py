from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.schemas import (
    CaseLawDigestGenerateRequest,
    CaseLawDigestHistoryResponse,
    CaseLawImportRequest,
    CaseLawImportResponse,
    CaseLawDigestResponse,
    CaseLawSearchResponse,
    CaseLawSyncRequest,
    CaseLawSyncResponse,
    CaseLawSyncStatusResponse,
)
from app.services.audit import log_action
from app.services.case_law_cache import (
    get_case_law_digest,
    get_case_law_sync_status,
    search_case_law,
    sync_case_law_sources,
    upsert_case_law_records,
)
from app.services.case_law_digests import (
    build_digest_snippet_from_case_law_row,
    get_case_law_digest_by_id,
    list_case_law_digests,
    save_case_law_digest,
    to_digest_item_payload,
)
from app.services.entitlements import ensure_feature_access

router = APIRouter(prefix="/api/case-law", tags=["case-law"])


@router.get("/search", response_model=CaseLawSearchResponse)
def search_endpoint(
    query: str | None = Query(default=None),
    court_type: str | None = Query(default=None),
    only_supreme: bool = Query(default=False),
    source: str | None = Query(default=None, description="Comma separated sources"),
    tags: str | None = Query(default=None, description="Comma separated tags"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    fresh_days: int | None = Query(default=None, ge=1, le=3650),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="decision_date"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseLawSearchResponse:
    tag_items = [item.strip() for item in (tags or "").split(",") if item.strip()]
    source_items = [item.strip().lower() for item in (source or "").split(",") if item.strip()]
    result = search_case_law(
        db,
        query=query,
        court_type=court_type,
        only_supreme=only_supreme,
        sources=source_items,
        tags=tag_items,
        date_from=date_from,
        date_to=date_to,
        fresh_days=fresh_days,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    items = [
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
    log_action(
        db,
        user_id=user.user_id,
        action="case_law_search",
        entity_type="case_law_cache",
        entity_id=None,
        metadata={
            "query": query,
            "court_type": court_type,
            "only_supreme": only_supreme,
            "source": source_items,
            "tags": tag_items,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "fresh_days": fresh_days,
            "page": result.page,
            "page_size": result.page_size,
            "sort_by": result.sort_by,
            "sort_dir": result.sort_dir,
            "found": len(items),
            "total": result.total,
        },
    )
    return CaseLawSearchResponse(
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        pages=result.pages,
        sort_by=result.sort_by,
        sort_dir=result.sort_dir,
        items=items,
    )


def _serialize_digest_from_rows(
    *,
    digest,
    generated_at: str,
    digest_id: str | None = None,
    saved: bool = False,
    title: str | None = None,
) -> CaseLawDigestResponse:
    return CaseLawDigestResponse(
        digest_id=digest_id,
        saved=saved,
        title=title,
        days=digest.days,
        limit=digest.limit,
        total=digest.total,
        only_supreme=digest.only_supreme,
        court_type=digest.court_type,
        source=digest.sources,
        generated_at=generated_at,
        items=[
            {
                "id": row.id,
                "source": row.source,
                "decision_id": row.decision_id,
                "court_name": row.court_name,
                "court_type": row.court_type,
                "decision_date": row.decision_date.isoformat() if row.decision_date else None,
                "case_number": row.case_number,
                "subject_categories": row.subject_categories or [],
                "summary": row.summary,
                "legal_positions": row.legal_positions or {},
                "prompt_snippet": build_digest_snippet_from_case_law_row(row),
            }
            for row in digest.items
        ],
    )


@router.get("/digest", response_model=CaseLawDigestResponse)
def digest_endpoint(
    days: int = Query(default=7, ge=1, le=3650),
    limit: int = Query(default=20, ge=1, le=100),
    court_type: str | None = Query(default=None),
    source: str | None = Query(default=None, description="Comma separated sources"),
    only_supreme: bool = Query(default=True),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseLawDigestResponse:
    source_items = [item.strip().lower() for item in (source or "").split(",") if item.strip()]
    digest = get_case_law_digest(
        db,
        days=days,
        limit=limit,
        court_type=court_type,
        sources=source_items,
        only_supreme=only_supreme,
    )
    log_action(
        db,
        user_id=user.user_id,
        action="case_law_digest",
        entity_type="case_law_cache",
        entity_id=None,
        metadata={
            "days": digest.days,
            "limit": digest.limit,
            "court_type": digest.court_type,
            "source": digest.sources,
            "only_supreme": digest.only_supreme,
            "total": digest.total,
            "returned": len(digest.items),
        },
    )
    return _serialize_digest_from_rows(
        digest=digest,
        generated_at=datetime.now(timezone.utc).isoformat(),
        saved=False,
    )


@router.post("/digest/generate", response_model=CaseLawDigestResponse)
def digest_generate_endpoint(
    payload: CaseLawDigestGenerateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseLawDigestResponse:
    if payload.save:
        ensure_feature_access(db, current_user=user, feature="case_law_saved_digests")
    digest = get_case_law_digest(
        db,
        days=payload.days,
        limit=payload.limit,
        court_type=payload.court_type,
        sources=payload.source,
        only_supreme=payload.only_supreme,
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    saved_digest_id: str | None = None
    if payload.save:
        saved = save_case_law_digest(
            db,
            user_id=user.user_id,
            rows=digest.items,
            days=digest.days,
            limit=digest.limit,
            only_supreme=digest.only_supreme,
            court_type=digest.court_type,
            sources=digest.sources,
            total=digest.total,
            generated_at=generated_at,
            title=payload.title,
        )
        saved_digest_id = saved.id
    log_action(
        db,
        user_id=user.user_id,
        action="case_law_digest_generate",
        entity_type="case_law_digest",
        entity_id=saved_digest_id,
        metadata={
            "days": digest.days,
            "limit": digest.limit,
            "court_type": digest.court_type,
            "source": digest.sources,
            "only_supreme": digest.only_supreme,
            "total": digest.total,
            "returned": len(digest.items),
            "saved": payload.save,
            "title": (payload.title or "").strip() or None,
        },
    )
    return _serialize_digest_from_rows(
        digest=digest,
        generated_at=generated_at,
        digest_id=saved_digest_id,
        saved=bool(saved_digest_id),
        title=(payload.title or "").strip() or None,
    )


@router.get("/digest/history", response_model=CaseLawDigestHistoryResponse)
def digest_history_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseLawDigestHistoryResponse:
    ensure_feature_access(db, current_user=user, feature="case_law_saved_digests")
    rows, total, normalized_page, pages = list_case_law_digests(
        db,
        user_id=user.user_id,
        page=page,
        page_size=page_size,
    )
    log_action(
        db,
        user_id=user.user_id,
        action="case_law_digest_history",
        entity_type="case_law_digest",
        entity_id=None,
        metadata={"page": normalized_page, "page_size": page_size, "returned": len(rows), "total": total},
    )
    return CaseLawDigestHistoryResponse(
        total=total,
        page=normalized_page,
        page_size=page_size,
        pages=pages,
        items=[
            {
                "id": row.id,
                "title": row.title,
                "days": int(row.days or 0),
                "limit": int(row.limit or 0),
                "total": int(row.total or 0),
                "item_count": int(row.item_count or 0),
                "only_supreme": bool(row.only_supreme),
                "court_type": row.court_type,
                "source": row.sources_json or [],
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    )


@router.get("/digest/history/{digest_id}", response_model=CaseLawDigestResponse)
def digest_history_detail_endpoint(
    digest_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseLawDigestResponse:
    ensure_feature_access(db, current_user=user, feature="case_law_saved_digests")
    row = get_case_law_digest_by_id(db, user_id=user.user_id, digest_id=digest_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Digest not found")
    log_action(
        db,
        user_id=user.user_id,
        action="case_law_digest_detail",
        entity_type="case_law_digest",
        entity_id=row.id,
        metadata={"item_count": len(row.items)},
    )
    return CaseLawDigestResponse(
        digest_id=row.id,
        saved=True,
        title=row.title,
        days=int(row.days or 0),
        limit=int(row.limit or 0),
        total=int(row.total or 0),
        only_supreme=bool(row.only_supreme),
        court_type=row.court_type,
        source=row.sources_json or [],
        generated_at=row.created_at.isoformat(),
        items=[to_digest_item_payload(item) for item in row.items],
    )


@router.post("/import", response_model=CaseLawImportResponse)
def import_endpoint(
    payload: CaseLawImportRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseLawImportResponse:
    ensure_feature_access(db, current_user=user, feature="case_law_import")
    records = [item.model_dump() for item in payload.records]
    stats = upsert_case_law_records(db, records)
    log_action(
        db,
        user_id=user.user_id,
        action="case_law_import",
        entity_type="case_law_cache",
        entity_id=None,
        metadata={"records_in": len(records), "created": stats.created, "updated": stats.updated},
    )
    return CaseLawImportResponse(created=stats.created, updated=stats.updated, total=stats.total)


@router.post("/sync", response_model=CaseLawSyncResponse)
def sync_endpoint(
    payload: CaseLawSyncRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseLawSyncResponse:
    ensure_feature_access(db, current_user=user, feature="case_law_sync")
    stats = sync_case_law_sources(
        db,
        query=payload.query,
        limit=payload.limit,
        sources=payload.sources,
        allow_seed_fallback=payload.allow_seed_fallback,
    )
    log_action(
        db,
        user_id=user.user_id,
        action="case_law_sync",
        entity_type="case_law_cache",
        entity_id=None,
        metadata={
            "query": payload.query,
            "limit": payload.limit,
            "created": stats.created,
            "updated": stats.updated,
            "total": stats.total,
            "sources": stats.used_sources,
            "seed_fallback_used": stats.seed_fallback_used,
            "fetched_counts": stats.fetched_counts,
        },
    )
    return CaseLawSyncResponse(
        status="ok",
        created=stats.created,
        updated=stats.updated,
        total=stats.total,
        sources=stats.used_sources,
        seed_fallback_used=stats.seed_fallback_used,
        fetched_counts=stats.fetched_counts,
    )


@router.get("/sync/status", response_model=CaseLawSyncStatusResponse)
def sync_status_endpoint(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseLawSyncStatusResponse:
    ensure_feature_access(db, current_user=user, feature="case_law_monitoring")
    status = get_case_law_sync_status(db, user_id=user.user_id)
    log_action(
        db,
        user_id=user.user_id,
        action="case_law_sync_status",
        entity_type="case_law_cache",
        entity_id=None,
        metadata={"total_records": status.total_records, "has_last_sync": bool(status.last_sync_at)},
    )
    return CaseLawSyncStatusResponse(
        total_records=status.total_records,
        sources=status.sources,
        latest_decision_date=status.latest_decision_date.isoformat() if status.latest_decision_date else None,
        oldest_decision_date=status.oldest_decision_date.isoformat() if status.oldest_decision_date else None,
        last_sync_at=status.last_sync_at.isoformat() if status.last_sync_at else None,
        last_sync_action=status.last_sync_action,
        last_sync_query=status.last_sync_query,
        last_sync_limit=status.last_sync_limit,
        last_sync_created=status.last_sync_created,
        last_sync_updated=status.last_sync_updated,
        last_sync_total=status.last_sync_total,
        last_sync_sources=status.last_sync_sources,
        last_sync_seed_fallback_used=status.last_sync_seed_fallback_used,
    )
