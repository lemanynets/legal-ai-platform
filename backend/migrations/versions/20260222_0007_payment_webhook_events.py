"""add payment webhook events table for replay protection

Revision ID: 20260222_0007
Revises: 20260221_0006
Create Date: 2026-02-22 00:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260222_0007"
down_revision = "20260221_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_webhook_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("payment_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "event_id", name="uq_payment_webhook_events_provider_event_id"),
    )
    op.create_index("ix_payment_webhook_events_payment_id", "payment_webhook_events", ["payment_id"], unique=False)
    op.create_index("ix_payment_webhook_events_provider", "payment_webhook_events", ["provider"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payment_webhook_events_provider", table_name="payment_webhook_events")
    op.drop_index("ix_payment_webhook_events_payment_id", table_name="payment_webhook_events")
    op.drop_table("payment_webhook_events")
