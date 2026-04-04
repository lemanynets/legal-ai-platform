"""add calculation runs table for m9 history

Revision ID: 20260222_0010
Revises: 20260222_0009
Create Date: 2026-02-22 03:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260222_0010"
down_revision = "20260222_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calculation_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("calculation_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("input_payload", sa.JSON(), nullable=True),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calculation_runs_user_id", "calculation_runs", ["user_id"], unique=False)
    op.create_index("ix_calculation_runs_calculation_type", "calculation_runs", ["calculation_type"], unique=False)
    op.create_index(
        "ix_calculation_runs_user_created_at",
        "calculation_runs",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_calculation_runs_user_created_at", table_name="calculation_runs")
    op.drop_index("ix_calculation_runs_calculation_type", table_name="calculation_runs")
    op.drop_index("ix_calculation_runs_user_id", table_name="calculation_runs")
    op.drop_table("calculation_runs")
