from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.models import RegistryMonitorEvent, RegistryWatchItem


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


@dataclass(frozen=True)
class RegistryCheckDueStats:
    scanned: int = 0
    checked: int = 0
    state_changed: int = 0


@dataclass(frozen=True)
class RegistryMonitoringStatus:
    total_watch_items: int = 0
    active_watch_items: int = 0
    due_watch_items: int = 0
    warning_watch_items: int = 0
    state_changed_events_24h: int = 0
    last_event_at: datetime | None = None
    by_status: dict[str, int] | None = None


def create_watch_item(
    db: Session,
    *,
    user_id: str,
    source: str,
    registry_type: str,
    identifier: str,
    entity_name: str,
    check_interval_hours: int,
    notes: str | None,
) -> tuple[RegistryWatchItem, RegistryMonitorEvent]:
    now = _now()
    safe_interval = max(1, min(check_interval_hours, 720))
    row = RegistryWatchItem(
        user_id=user_id,
        source=(source or "opendatabot").strip().lower(),
        registry_type=registry_type.strip().lower(),
        identifier=identifier.strip(),
        entity_name=entity_name.strip(),
        status="active",
        check_interval_hours=safe_interval,
        last_checked_at=None,
        next_check_at=now + timedelta(hours=safe_interval),
        last_change_at=None,
        latest_snapshot=None,
        notes=_clean(notes),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()

    event = RegistryMonitorEvent(
        watch_item_id=row.id,
        user_id=user_id,
        event_type="watch_created",
        severity="info",
        title="Watch item created",
        details={
            "source": row.source,
            "registry_type": row.registry_type,
            "identifier": row.identifier,
            "entity_name": row.entity_name,
            "check_interval_hours": row.check_interval_hours,
        },
        observed_at=now,
        created_at=now,
    )
    db.add(event)
    db.commit()
    db.refresh(row)
    db.refresh(event)
    return row, event


def list_watch_items(
    db: Session,
    *,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    registry_type: str | None = None,
    status: str | None = None,
    query: str | None = None,
) -> tuple[list[RegistryWatchItem], int, int, int]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))
    stmt = select(RegistryWatchItem).where(RegistryWatchItem.user_id == user_id)

    normalized_registry_type = _clean(registry_type)
    if normalized_registry_type:
        stmt = stmt.where(RegistryWatchItem.registry_type == normalized_registry_type.lower())

    normalized_status = _clean(status)
    if normalized_status:
        stmt = stmt.where(RegistryWatchItem.status == normalized_status.lower())

    normalized_query = _clean(query)
    if normalized_query:
        pattern = f"%{normalized_query.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(RegistryWatchItem.identifier).like(pattern),
                func.lower(RegistryWatchItem.entity_name).like(pattern),
            )
        )

    total = int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one() or 0)
    pages = max(1, math.ceil(total / safe_page_size)) if total > 0 else 1
    if safe_page > pages:
        safe_page = pages

    rows = list(
        db.execute(
            stmt.order_by(desc(RegistryWatchItem.created_at), desc(RegistryWatchItem.id))
            .offset((safe_page - 1) * safe_page_size)
            .limit(safe_page_size)
        )
        .scalars()
        .all()
    )
    return rows, total, safe_page, pages


def get_watch_item(
    db: Session,
    *,
    user_id: str,
    watch_item_id: str,
) -> RegistryWatchItem | None:
    return db.execute(
        select(RegistryWatchItem)
        .where(RegistryWatchItem.id == watch_item_id, RegistryWatchItem.user_id == user_id)
        .limit(1)
    ).scalar_one_or_none()


def delete_watch_item(
    db: Session,
    *,
    user_id: str,
    watch_item_id: str,
) -> RegistryWatchItem | None:
    row = get_watch_item(db, user_id=user_id, watch_item_id=watch_item_id)
    if row is None:
        return None
    db.delete(row)
    db.commit()
    return row


def _build_check_event(
    *,
    row: RegistryWatchItem,
    previous_status: str,
    new_status: str,
    summary: str | None,
    details: dict,
    now: datetime,
) -> RegistryMonitorEvent:
    status_changed = previous_status != new_status
    if status_changed:
        event_type = "state_changed"
        severity = "warning"
        title = f"Status changed: {previous_status or '-'} -> {new_status}"
    else:
        event_type = "checked"
        severity = "info"
        title = "Registry check completed"

    payload = {
        "previous_status": previous_status,
        "status": new_status,
        "summary": summary,
        "source": row.source,
        "registry_type": row.registry_type,
        "identifier": row.identifier,
        "checked_at": now.isoformat(),
        **details,
    }
    return RegistryMonitorEvent(
        watch_item_id=row.id,
        user_id=row.user_id,
        event_type=event_type,
        severity=severity,
        title=title,
        details=payload,
        observed_at=now,
        created_at=now,
    )


def run_watch_check(
    db: Session,
    *,
    user_id: str,
    watch_item_id: str,
    observed_status: str | None,
    summary: str | None,
    details: dict | None,
) -> tuple[RegistryWatchItem, RegistryMonitorEvent] | None:
    row = get_watch_item(db, user_id=user_id, watch_item_id=watch_item_id)
    if row is None:
        return None

    now = _now()
    previous_status = (row.status or "").strip().lower()
    new_status = (_clean(observed_status) or previous_status or "active").lower()
    safe_details = details or {}
    safe_summary = _clean(summary)

    snapshot = {
        "status": new_status,
        "summary": safe_summary,
        "details": safe_details,
        "source": row.source,
        "registry_type": row.registry_type,
        "identifier": row.identifier,
        "checked_at": now.isoformat(),
    }
    row.status = new_status
    row.latest_snapshot = snapshot
    row.last_checked_at = now
    row.next_check_at = now + timedelta(hours=max(1, min(int(row.check_interval_hours or 24), 720)))
    if previous_status != new_status:
        row.last_change_at = now

    event = _build_check_event(
        row=row,
        previous_status=previous_status,
        new_status=new_status,
        summary=safe_summary,
        details=safe_details,
        now=now,
    )
    db.add(event)
    db.commit()
    db.refresh(row)
    db.refresh(event)
    return row, event


def _infer_auto_status(row: RegistryWatchItem) -> tuple[str, str, dict[str, Any]]:
    from app.services.opendatabot_client import opendatabot
    
    identifier = (row.identifier or "").strip()
    status_now = (row.status or "").strip().lower() or "active"
    
    # Attempt real check
    try:
        details = opendatabot.get_company_details(identifier)
        status = details.get("status") or status_now
        
        # Risk assessment
        is_sanctioned = details.get("is_sanctioned", False)
        has_tax_debt = details.get("has_tax_debt", False)
        
        summary = f"Registry check completed. Status: {status}."
        if is_sanctioned:
            status = "risk_detected"
            summary += " CRITICAL: Company is on sanctions list!"
        elif has_tax_debt:
            status = "risk_detected"
            summary += " WARNING: Tax debt detected."
            
        return status, summary, details
    except Exception as e:
        return status_now, f"Failed to reach registry: {str(e)}", {}


def check_due_watch_items(
    db: Session,
    *,
    user_id: str,
    limit: int = 50,
    auto: bool = False,
) -> RegistryCheckDueStats:
    now = _now()
    safe_limit = max(1, min(limit, 500))
    due_rows = list(
        db.execute(
            select(RegistryWatchItem)
            .where(
                RegistryWatchItem.user_id == user_id,
                RegistryWatchItem.status != "archived",
                or_(RegistryWatchItem.next_check_at.is_(None), RegistryWatchItem.next_check_at <= now),
            )
            .order_by(RegistryWatchItem.next_check_at.asc(), RegistryWatchItem.created_at.asc())
            .limit(safe_limit)
        )
        .scalars()
        .all()
    )

    checked = 0
    state_changed = 0
    for item in due_rows:
        next_status, summary_text, details = _infer_auto_status(item)
        checked_row = run_watch_check(
            db,
            user_id=user_id,
            watch_item_id=item.id,
            observed_status=next_status,
            summary=summary_text,
            details={**details, "mode": "auto_due_check" if auto else "manual_due_check", "due": True},
        )
        if checked_row is None:
            continue
        checked += 1
        _, event = checked_row
        if event.event_type == "state_changed":
            state_changed += 1

    return RegistryCheckDueStats(scanned=len(due_rows), checked=checked, state_changed=state_changed)


def get_monitoring_status(db: Session, *, user_id: str) -> RegistryMonitoringStatus:
    now = _now()
    day_ago = now - timedelta(hours=24)

    total_watch_items = int(
        db.execute(
            select(func.count())
            .select_from(RegistryWatchItem)
            .where(RegistryWatchItem.user_id == user_id)
        ).scalar_one()
        or 0
    )
    active_watch_items = int(
        db.execute(
            select(func.count())
            .select_from(RegistryWatchItem)
            .where(RegistryWatchItem.user_id == user_id, RegistryWatchItem.status == "active")
        ).scalar_one()
        or 0
    )
    due_watch_items = int(
        db.execute(
            select(func.count())
            .select_from(RegistryWatchItem)
            .where(
                RegistryWatchItem.user_id == user_id,
                RegistryWatchItem.status != "archived",
                or_(RegistryWatchItem.next_check_at.is_(None), RegistryWatchItem.next_check_at <= now),
            )
        ).scalar_one()
        or 0
    )
    warning_watch_items = int(
        db.execute(
            select(func.count())
            .select_from(RegistryWatchItem)
            .where(
                RegistryWatchItem.user_id == user_id,
                RegistryWatchItem.status.in_(["risk_detected", "warning", "blocked"]),
            )
        ).scalar_one()
        or 0
    )

    state_changed_events_24h = int(
        db.execute(
            select(func.count())
            .select_from(RegistryMonitorEvent)
            .where(
                RegistryMonitorEvent.user_id == user_id,
                RegistryMonitorEvent.event_type == "state_changed",
                RegistryMonitorEvent.observed_at >= day_ago,
            )
        ).scalar_one()
        or 0
    )
    last_event_at = db.execute(
        select(func.max(RegistryMonitorEvent.observed_at)).where(RegistryMonitorEvent.user_id == user_id)
    ).scalar_one_or_none()

    grouped_rows = db.execute(
        select(RegistryWatchItem.status, func.count())
        .where(RegistryWatchItem.user_id == user_id)
        .group_by(RegistryWatchItem.status)
    ).all()
    by_status = {str(status or ""): int(count or 0) for status, count in grouped_rows}

    return RegistryMonitoringStatus(
        total_watch_items=total_watch_items,
        active_watch_items=active_watch_items,
        due_watch_items=due_watch_items,
        warning_watch_items=warning_watch_items,
        state_changed_events_24h=state_changed_events_24h,
        last_event_at=last_event_at,
        by_status=by_status,
    )


def list_monitor_events(
    db: Session,
    *,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    watch_item_id: str | None = None,
    severity: str | None = None,
    event_type: str | None = None,
) -> tuple[list[RegistryMonitorEvent], int, int, int]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))
    stmt = select(RegistryMonitorEvent).where(RegistryMonitorEvent.user_id == user_id)

    normalized_watch_id = _clean(watch_item_id)
    if normalized_watch_id:
        stmt = stmt.where(RegistryMonitorEvent.watch_item_id == normalized_watch_id)

    normalized_severity = _clean(severity)
    if normalized_severity:
        stmt = stmt.where(RegistryMonitorEvent.severity == normalized_severity.lower())

    normalized_event_type = _clean(event_type)
    if normalized_event_type:
        stmt = stmt.where(RegistryMonitorEvent.event_type == normalized_event_type.lower())

    total = int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one() or 0)
    pages = max(1, math.ceil(total / safe_page_size)) if total > 0 else 1
    if safe_page > pages:
        safe_page = pages

    rows = list(
        db.execute(
            stmt.order_by(desc(RegistryMonitorEvent.observed_at), desc(RegistryMonitorEvent.id))
            .offset((safe_page - 1) * safe_page_size)
            .limit(safe_page_size)
        )
        .scalars()
        .all()
    )
    return rows, total, safe_page, pages
