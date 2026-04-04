"""add intake cache table

Revision ID: 20260327_0019
Revises: 20260327_0018
Create Date: 2026-03-27 17:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260327_0019"
down_revision = "20260327_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intake_cache",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=False),
        sa.Column("intake_result", sa.JSON(), nullable=False),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_intake_cache_user_id", "intake_cache", ["user_id"], unique=False)
    op.create_index("ix_intake_cache_file_hash", "intake_cache", ["file_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_intake_cache_file_hash", table_name="intake_cache")
    op.drop_index("ix_intake_cache_user_id", table_name="intake_cache")
    op.drop_table("intake_cache")