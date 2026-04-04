"""add registry monitoring watchlist and events tables

Revision ID: 20260222_0009
Revises: 20260222_0008
Create Date: 2026-02-22 02:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260222_0009"
down_revision = "20260222_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registry_watch_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("registry_type", sa.String(length=50), nullable=False),
        sa.Column("identifier", sa.String(length=120), nullable=False),
        sa.Column("entity_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("check_interval_hours", sa.Integer(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_change_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_snapshot", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_registry_watch_items_user_id", "registry_watch_items", ["user_id"], unique=False)
    op.create_index("ix_registry_watch_items_identifier", "registry_watch_items", ["identifier"], unique=False)
    op.create_index("ix_registry_watch_items_status", "registry_watch_items", ["status"], unique=False)
    op.create_index(
        "ix_registry_watch_items_user_registry_identifier",
        "registry_watch_items",
        ["user_id", "registry_type", "identifier"],
        unique=False,
    )

    op.create_table(
        "registry_monitor_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("watch_item_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["watch_item_id"], ["registry_watch_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_registry_monitor_events_watch_item_id", "registry_monitor_events", ["watch_item_id"], unique=False)
    op.create_index("ix_registry_monitor_events_user_id", "registry_monitor_events", ["user_id"], unique=False)
    op.create_index("ix_registry_monitor_events_event_type", "registry_monitor_events", ["event_type"], unique=False)
    op.create_index("ix_registry_monitor_events_severity", "registry_monitor_events", ["severity"], unique=False)
    op.create_index(
        "ix_registry_monitor_events_user_created_at",
        "registry_monitor_events",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_registry_monitor_events_user_created_at", table_name="registry_monitor_events")
    op.drop_index("ix_registry_monitor_events_severity", table_name="registry_monitor_events")
    op.drop_index("ix_registry_monitor_events_event_type", table_name="registry_monitor_events")
    op.drop_index("ix_registry_monitor_events_user_id", table_name="registry_monitor_events")
    op.drop_index("ix_registry_monitor_events_watch_item_id", table_name="registry_monitor_events")
    op.drop_table("registry_monitor_events")

    op.drop_index("ix_registry_watch_items_user_registry_identifier", table_name="registry_watch_items")
    op.drop_index("ix_registry_watch_items_status", table_name="registry_watch_items")
    op.drop_index("ix_registry_watch_items_identifier", table_name="registry_watch_items")
    op.drop_index("ix_registry_watch_items_user_id", table_name="registry_watch_items")
    op.drop_table("registry_watch_items")
