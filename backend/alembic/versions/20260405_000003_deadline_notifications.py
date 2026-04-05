"""add deadline notifications table

Revision ID: 20260405_000003
Revises: 20260405_000002
Create Date: 2026-04-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260405_000003"
down_revision = "20260405_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deadline_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("deadline_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False, server_default="in_app"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deadline_id"], ["deadlines.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_deadline_notifications_user_id", "deadline_notifications", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_deadline_notifications_user_id", table_name="deadline_notifications")
    op.drop_table("deadline_notifications")
