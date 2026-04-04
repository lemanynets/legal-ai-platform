from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.schemas import (
    RegistryCheckDueRequest,
    RegistryCheckDueResponse,
    RegistryMonitorEventsResponse,
    RegistryMonitoringStatusResponse,
    RegistryWatchCheckRequest,
    RegistryWatchCheckResponse,
    RegistryWatchCreateRequest,
    RegistryWatchCreateResponse,
    RegistryWatchDeleteResponse,
    RegistryWatchListResponse,
)
from app.services.audit import log_action
from app.services.entitlements import ensure_feature_access
from app.services.realtime import publish_user_event
from app.services.registry_monitoring import (
    check_due_watch_items,
    create_watch_item,
    delete_watch_item,
    get_monitoring_status,
    list_monitor_events,
    list_watch_items,
    run_watch_check,
)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def _serialize_watch_item(row) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "source": row.source,
        "registry_type": row.registry_type,
        "identifier": row.identifier,
        "entity_name": row.entity_name,
        "status": row.status,
        "check_interval_hours": int(row.check_interval_hours or 24),
        "last_checked_at": row.last_checked_at.isoformat() if row.last_checked_at else None,
        "next_check_at": row.next_check_at.isoformat() if row.next_check_at else None,
        "last_change_at": row.last_change_at.isoformat() if row.last_change_at else None,
        "latest_snapshot": row.latest_snapshot or None,
        "notes": row.notes,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _serialize_event(row) -> dict:
    return {
        "id": row.id,
        "watch_item_id": row.watch_item_id,
        "user_id": row.user_id,
        "event_type": row.event_type,
        "severity": row.severity,
        "title": row.title,
        "details": row.details or {},
        "observed_at": row.observed_at.isoformat(),
        "created_at": row.created_at.isoformat(),
    }


@router.post("/watch-items", response_model=RegistryWatchCreateResponse)
def create_watch_item_endpoint(
    payload: RegistryWatchCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RegistryWatchCreateResponse:
    ensure_feature_access(db, current_user=user, feature="registry_monitoring")
    row, event = create_watch_item(
        db,
        user_id=user.user_id,
        source=payload.source,
        registry_type=payload.registry_type,
        identifier=payload.identifier,
        entity_name=payload.entity_name,
        check_interval_hours=payload.check_interval_hours,
        notes=payload.notes,
    )
    log_action(
        db,
        user_id=user.user_id,
        action="registry_watch_create",
        entity_type="registry_watch_item",
        entity_id=row.id,
        metadata={
            "source": row.source,
            "registry_type": row.registry_type,
            "identifier": row.identifier,
            "event_id": event.id,
        },
    )
    publish_user_event(
        user.user_id,
        "monitoring.watch_created",
        {
            "watch_item_id": row.id,
            "identifier": row.identifier,
            "event_id": event.id,
        },
    )
    return RegistryWatchCreateResponse(status="created", item=_serialize_watch_item(row))


@router.get("/watch-items", response_model=RegistryWatchListResponse)
def list_watch_items_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    registry_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    query: str | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RegistryWatchListResponse:
    ensure_feature_access(db, current_user=user, feature="registry_monitoring")
    rows, total, normalized_page, pages = list_watch_items(
        db,
        user_id=user.user_id,
        page=page,
        page_size=page_size,
        registry_type=registry_type,
        status=status,
        query=query,
    )
    log_action(
        db,
        user_id=user.user_id,
        action="registry_watch_list",
        entity_type="registry_watch_item",
        entity_id=None,
        metadata={
            "page": normalized_page,
            "page_size": page_size,
            "registry_type": registry_type,
            "status": status,
            "query": query,
            "returned": len(rows),
            "total": total,
        },
    )
    return RegistryWatchListResponse(
        total=total,
        page=normalized_page,
        page_size=page_size,
        pages=pages,
        items=[_serialize_watch_item(item) for item in rows],
    )


@router.delete("/watch-items/{watch_item_id}", response_model=RegistryWatchDeleteResponse)
def delete_watch_item_endpoint(
    watch_item_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RegistryWatchDeleteResponse:
    ensure_feature_access(db, current_user=user, feature="registry_monitoring")
    row = delete_watch_item(db, user_id=user.user_id, watch_item_id=watch_item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Watch item not found")
    log_action(
        db,
        user_id=user.user_id,
        action="registry_watch_delete",
        entity_type="registry_watch_item",
        entity_id=watch_item_id,
        metadata={"id": watch_item_id},
    )
    return RegistryWatchDeleteResponse(status="deleted", id=watch_item_id)


@router.post("/watch-items/{watch_item_id}/check", response_model=RegistryWatchCheckResponse)
def run_watch_item_check_endpoint(
    watch_item_id: str,
    payload: RegistryWatchCheckRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RegistryWatchCheckResponse:
    ensure_feature_access(db, current_user=user, feature="registry_monitoring")
    safe_payload = payload or RegistryWatchCheckRequest()
    checked = run_watch_check(
        db,
        user_id=user.user_id,
        watch_item_id=watch_item_id,
        observed_status=safe_payload.observed_status,
        summary=safe_payload.summary,
        details=safe_payload.details,
    )
    if checked is None:
        raise HTTPException(status_code=404, detail="Watch item not found")
    row, event = checked
    log_action(
        db,
        user_id=user.user_id,
        action="registry_watch_check",
        entity_type="registry_watch_item",
        entity_id=row.id,
        metadata={
            "status": row.status,
            "event_id": event.id,
            "event_type": event.event_type,
            "severity": event.severity,
        },
    )
    publish_user_event(
        user.user_id,
        "monitoring.watch_checked",
        {
            "watch_item_id": row.id,
            "event_id": event.id,
            "event_type": event.event_type,
            "severity": event.severity,
        },
    )
    return RegistryWatchCheckResponse(
        status="checked",
        item=_serialize_watch_item(row),
        event_id=event.id,
        event_type=event.event_type,
    )


@router.get("/events", response_model=RegistryMonitorEventsResponse)
def list_events_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    watch_item_id: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RegistryMonitorEventsResponse:
    ensure_feature_access(db, current_user=user, feature="registry_monitoring")
    rows, total, normalized_page, pages = list_monitor_events(
        db,
        user_id=user.user_id,
        page=page,
        page_size=page_size,
        watch_item_id=watch_item_id,
        severity=severity,
        event_type=event_type,
    )
    log_action(
        db,
        user_id=user.user_id,
        action="registry_events_list",
        entity_type="registry_monitor_event",
        entity_id=None,
        metadata={
            "page": normalized_page,
            "page_size": page_size,
            "watch_item_id": watch_item_id,
            "severity": severity,
            "event_type": event_type,
            "returned": len(rows),
            "total": total,
        },
    )
    return RegistryMonitorEventsResponse(
        total=total,
        page=normalized_page,
        page_size=page_size,
        pages=pages,
        items=[_serialize_event(item) for item in rows],
    )


@router.get("/status", response_model=RegistryMonitoringStatusResponse)
def monitoring_status_endpoint(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RegistryMonitoringStatusResponse:
    ensure_feature_access(db, current_user=user, feature="registry_monitoring")
    status = get_monitoring_status(db, user_id=user.user_id)
    log_action(
        db,
        user_id=user.user_id,
        action="registry_status",
        entity_type="registry_watch_item",
        entity_id=None,
        metadata={
            "total_watch_items": status.total_watch_items,
            "due_watch_items": status.due_watch_items,
            "warning_watch_items": status.warning_watch_items,
            "state_changed_events_24h": status.state_changed_events_24h,
        },
    )
    return RegistryMonitoringStatusResponse(
        total_watch_items=status.total_watch_items,
        active_watch_items=status.active_watch_items,
        due_watch_items=status.due_watch_items,
        warning_watch_items=status.warning_watch_items,
        state_changed_events_24h=status.state_changed_events_24h,
        last_event_at=status.last_event_at.isoformat() if status.last_event_at else None,
        by_status=status.by_status or {},
    )


@router.post("/check-due", response_model=RegistryCheckDueResponse)
def check_due_endpoint(
    payload: RegistryCheckDueRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RegistryCheckDueResponse:
    ensure_feature_access(db, current_user=user, feature="registry_monitoring")
    stats = check_due_watch_items(db, user_id=user.user_id, limit=payload.limit, auto=False)
    log_action(
        db,
        user_id=user.user_id,
        action="registry_check_due",
        entity_type="registry_watch_item",
        entity_id=None,
        metadata={
            "limit": payload.limit,
            "scanned": stats.scanned,
            "checked": stats.checked,
            "state_changed": stats.state_changed,
        },
    )
    publish_user_event(
        user.user_id,
        "monitoring.check_due_completed",
        {
            "scanned": stats.scanned,
            "checked": stats.checked,
            "state_changed": stats.state_changed,
        },
    )
    return RegistryCheckDueResponse(
        status="ok",
        scanned=stats.scanned,
        checked=stats.checked,
        state_changed=stats.state_changed,
    )
