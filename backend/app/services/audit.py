from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.models import AnalyticsEvent, AuditLog
from app.models.base import utcnow


INTEGRITY_VERSION = "v1"


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _canonical_json(value: dict[str, Any] | None) -> str:
    normalized = _normalize_json_value(value or {})
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _build_integrity_scope(user_id: str | None) -> str:
    normalized_user_id = str(user_id or "").strip()
    if normalized_user_id:
        return f"user:{normalized_user_id}"
    return "system"


def _normalize_datetime(value: datetime | None) -> datetime:
    if value is None:
        return utcnow()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _build_integrity_hash(
    *,
    scope: str,
    row_id: str,
    created_at: datetime,
    action: str,
    entity_type: str | None,
    entity_id: str | None,
    payload_hash: str,
    prev_hash: str | None,
) -> str:
    created_at_iso = _normalize_datetime(created_at).isoformat()
    payload = "\n".join(
        [
            INTEGRITY_VERSION,
            scope,
            row_id,
            created_at_iso,
            str(action or "").strip(),
            str(entity_type or "").strip(),
            str(entity_id or "").strip(),
            payload_hash,
            str(prev_hash or ""),
        ]
    )
    return _sha256_hex(payload)


def _compute_integrity_payload(
    *,
    user_id: str | None,
    action: str,
    entity_type: str | None,
    entity_id: str | None,
    metadata: dict[str, Any] | None,
    created_at: datetime | None = None,
    row_id: str | None = None,
    prev_hash: str | None = None,
) -> dict[str, Any]:
    scope = _build_integrity_scope(user_id)
    normalized_created_at = _normalize_datetime(created_at)
    normalized_id = str(row_id or str(uuid4()))
    normalized_metadata = metadata if isinstance(metadata, dict) else {}
    payload_json = _canonical_json(normalized_metadata)
    payload_hash = _sha256_hex(payload_json)
    integrity_hash = _build_integrity_hash(
        scope=scope,
        row_id=normalized_id,
        created_at=normalized_created_at,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
    )
    return {
        "scope": scope,
        "created_at": normalized_created_at,
        "row_id": normalized_id,
        "metadata": normalized_metadata,
        "payload_hash": payload_hash,
        "hash": integrity_hash,
        "prev_hash": prev_hash,
    }


def _get_latest_scope_hash(db: Session, *, scope: str) -> str | None:
    row = db.execute(
        select(AuditLog)
        .where(AuditLog.integrity_scope == scope)
        .order_by(desc(AuditLog.created_at), desc(AuditLog.id))
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None
    return str(row.integrity_hash or "").strip() or None


def log_action(
    db: Session,
    *,
    user_id: str | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    scope = _build_integrity_scope(user_id)
    prev_hash = _get_latest_scope_hash(db, scope=scope)
    integrity = _compute_integrity_payload(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata,
        prev_hash=prev_hash,
    )
    row = AuditLog(
        id=integrity["row_id"],
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=integrity["metadata"],
        integrity_scope=integrity["scope"],
        integrity_prev_hash=integrity["prev_hash"],
        integrity_payload_hash=integrity["payload_hash"],
        integrity_hash=integrity["hash"],
        created_at=integrity["created_at"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def log_action_once(
    db: Session,
    *,
    user_id: str | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    dedupe_keys: dict[str, Any] | None = None,
) -> AuditLog:
    expected_meta = metadata or {}
    keys = dedupe_keys or {}
    if keys:
        stmt = select(AuditLog).where(
            AuditLog.user_id == user_id,
            AuditLog.action == action,
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
        )
        rows = list(db.execute(stmt.order_by(desc(AuditLog.created_at), desc(AuditLog.id)).limit(20)).scalars().all())
        for existing in rows:
            existing_meta = existing.metadata_json if isinstance(existing.metadata_json, dict) else {}
            if all(existing_meta.get(key) == value for key, value in keys.items()):
                return existing
    return log_action(
        db,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=expected_meta,
    )


def verify_audit_integrity_chain(
    db: Session,
    *,
    user_id: str | None,
    limit: int = 2000,
) -> dict[str, Any]:
    safe_limit = max(10, min(int(limit or 10), 20000))
    scope = _build_integrity_scope(user_id)
    total = int(
        db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.integrity_scope == scope)).scalar_one() or 0
    )
    rows = list(
        db.execute(
            select(AuditLog)
            .where(AuditLog.integrity_scope == scope)
            .order_by(asc(AuditLog.created_at), asc(AuditLog.id))
            .limit(safe_limit)
        )
        .scalars()
        .all()
    )

    issues: list[dict[str, Any]] = []
    previous_hash: str | None = None
    for row in rows:
        expected_prev = previous_hash
        actual_prev = str(row.integrity_prev_hash or "").strip() or None
        if actual_prev != expected_prev:
            issues.append(
                {
                    "row_id": row.id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "code": "PREV_HASH_MISMATCH",
                    "message": (
                        f"Previous hash mismatch. expected={expected_prev or 'null'} actual={actual_prev or 'null'}"
                    ),
                }
            )

        metadata = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        expected_payload_hash = _sha256_hex(_canonical_json(metadata))
        actual_payload_hash = str(row.integrity_payload_hash or "").strip()
        if actual_payload_hash != expected_payload_hash:
            issues.append(
                {
                    "row_id": row.id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "code": "PAYLOAD_HASH_MISMATCH",
                    "message": "Payload hash mismatch.",
                }
            )

        expected_hash = _build_integrity_hash(
            scope=str(row.integrity_scope or "").strip(),
            row_id=row.id,
            created_at=row.created_at,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            payload_hash=expected_payload_hash,
            prev_hash=actual_prev,
        )
        actual_hash = str(row.integrity_hash or "").strip()
        if actual_hash != expected_hash:
            issues.append(
                {
                    "row_id": row.id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "code": "ROW_HASH_MISMATCH",
                    "message": "Row integrity hash mismatch.",
                }
            )

        previous_hash = actual_hash or None
        if len(issues) >= 100:
            break

    tail_hash = str(rows[0].integrity_hash or "").strip() if rows else None
    head_hash = str(rows[-1].integrity_hash or "").strip() if rows else None
    return {
        "scope": scope,
        "status": "pass" if not issues else "fail",
        "rows_total": total,
        "rows_checked": len(rows),
        "truncated": total > len(rows),
        "head_hash": head_hash or None,
        "tail_hash": tail_hash or None,
        "issues": issues,
        "verified_at": utcnow().isoformat(),
    }


def log_analytics_event(
    db: Session,
    user_id: str,
    event_type: str,
    metadata: dict[str, Any],
) -> AnalyticsEvent:
    event = AnalyticsEvent(
        user_id=user_id,
        event_type=event_type,
        metadata=metadata,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
