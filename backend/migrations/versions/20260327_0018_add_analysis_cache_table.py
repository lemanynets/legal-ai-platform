"""add analysis cache table

Revision ID: 20260327_0018
Revises: 20260327_0017
Create Date: 2026-03-27 16:33:37.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260327_0018"
down_revision = "20260327_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_cache",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=False),
        sa.Column("analysis_payload", sa.JSON(), nullable=False),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_cache_user_id", "analysis_cache", ["user_id"], unique=False
    )
    op.create_index(
        "ix_analysis_cache_file_hash", "analysis_cache", ["file_hash"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_cache_file_hash", table_name="analysis_cache")
    op.drop_index("ix_analysis_cache_user_id", table_name="analysis_cache")
    op.drop_table("analysis_cache")
