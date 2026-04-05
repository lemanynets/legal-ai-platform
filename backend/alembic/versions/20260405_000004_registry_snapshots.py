"""add registry snapshots table

Revision ID: 20260405_000004
Revises: 20260405_000003
Create Date: 2026-04-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260405_000004"
down_revision = "20260405_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registry_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("watch_item_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source", sa.Text(), nullable=False, server_default="opendatabot"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["watch_item_id"], ["registry_watch_items.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_registry_snapshots_user_id", "registry_snapshots", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_registry_snapshots_user_id", table_name="registry_snapshots")
    op.drop_table("registry_snapshots")
