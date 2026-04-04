"""add tamper-evident integrity chain fields to audit log

Revision ID: 20260303_0011
Revises: 20260222_0010
Create Date: 2026-03-03 12:00:00
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260303_0011"
down_revision = "20260222_0010"
branch_labels = None
depends_on = None

INTEGRITY_VERSION = "v1"


def _normalize_json_value(value):
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


def _canonical_json(value) -> str:
    normalized = _normalize_json_value(value or {})
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _build_row_hash(
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
    payload = "\n".join(
        [
            INTEGRITY_VERSION,
            scope,
            row_id,
            _normalize_datetime(created_at).isoformat(),
            str(action or "").strip(),
            str(entity_type or "").strip(),
            str(entity_id or "").strip(),
            payload_hash,
            str(prev_hash or ""),
        ]
    )
    return _sha256_hex(payload)


def upgrade() -> None:
    op.add_column("audit_log", sa.Column("integrity_scope", sa.String(length=96), nullable=True))
    op.add_column("audit_log", sa.Column("integrity_prev_hash", sa.String(length=64), nullable=True))
    op.add_column("audit_log", sa.Column("integrity_payload_hash", sa.String(length=64), nullable=True))
    op.add_column("audit_log", sa.Column("integrity_hash", sa.String(length=64), nullable=True))

    bind = op.get_bind()
    audit_log = sa.table(
        "audit_log",
        sa.column("id", sa.String(length=36)),
        sa.column("user_id", sa.String(length=64)),
        sa.column("action", sa.String(length=100)),
        sa.column("entity_type", sa.String(length=50)),
        sa.column("entity_id", sa.String(length=36)),
        sa.column("metadata", sa.JSON()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    rows = list(
        bind.execute(
            sa.select(
                audit_log.c.id,
                audit_log.c.user_id,
                audit_log.c.action,
                audit_log.c.entity_type,
                audit_log.c.entity_id,
                audit_log.c.metadata,
                audit_log.c.created_at,
            ).order_by(audit_log.c.created_at.asc(), audit_log.c.id.asc())
        ).mappings()
    )

    prev_by_scope: dict[str, str | None] = {}
    for row in rows:
        user_id = str(row["user_id"] or "").strip()
        scope = f"user:{user_id}" if user_id else "system"
        prev_hash = prev_by_scope.get(scope)
        created_at = _normalize_datetime(row["created_at"])
        payload_hash = _sha256_hex(_canonical_json(row["metadata"]))
        row_hash = _build_row_hash(
            scope=scope,
            row_id=str(row["id"]),
            created_at=created_at,
            action=str(row["action"] or ""),
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            payload_hash=payload_hash,
            prev_hash=prev_hash,
        )
        bind.execute(
            sa.text(
                """
                UPDATE audit_log
                SET integrity_scope = :scope,
                    integrity_prev_hash = :prev_hash,
                    integrity_payload_hash = :payload_hash,
                    integrity_hash = :row_hash
                WHERE id = :row_id
                """
            ),
            {
                "scope": scope,
                "prev_hash": prev_hash,
                "payload_hash": payload_hash,
                "row_hash": row_hash,
                "row_id": row["id"],
            },
        )
        prev_by_scope[scope] = row_hash

    op.alter_column("audit_log", "integrity_scope", nullable=False)
    op.alter_column("audit_log", "integrity_payload_hash", nullable=False)
    op.alter_column("audit_log", "integrity_hash", nullable=False)
    op.create_index("ix_audit_log_integrity_scope", "audit_log", ["integrity_scope"], unique=False)
    op.create_index("ix_audit_log_integrity_hash", "audit_log", ["integrity_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_log_integrity_hash", table_name="audit_log")
    op.drop_index("ix_audit_log_integrity_scope", table_name="audit_log")
    op.drop_column("audit_log", "integrity_hash")
    op.drop_column("audit_log", "integrity_payload_hash")
    op.drop_column("audit_log", "integrity_prev_hash")
    op.drop_column("audit_log", "integrity_scope")
