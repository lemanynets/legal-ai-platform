"""add analytics events table

Revision ID: 20260404_0020
Revises: 20260327_0019
Create Date: 2026-04-04 13:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260404_0020"
down_revision = "20260327_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analytics_events_user_id", "analytics_events", ["user_id"], unique=False)
    op.create_index("ix_analytics_events_event_type", "analytics_events", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analytics_events_event_type", table_name="analytics_events")
    op.drop_index("ix_analytics_events_user_id", table_name="analytics_events")
    op.drop_table("analytics_events")