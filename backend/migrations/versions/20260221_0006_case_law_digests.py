"""add case law digests tables

Revision ID: 20260221_0006
Revises: 20260218_0005
Create Date: 2026-02-21 12:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260221_0006"
down_revision = "20260218_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_law_digests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("limit", sa.Integer(), nullable=False),
        sa.Column("only_supreme", sa.Boolean(), nullable=False),
        sa.Column("court_type", sa.String(length=50), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_law_digests_user_id", "case_law_digests", ["user_id"], unique=False)
    op.create_index("ix_case_law_digests_created_at", "case_law_digests", ["created_at"], unique=False)

    op.create_table(
        "case_law_digest_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("digest_id", sa.String(length=36), nullable=False),
        sa.Column("case_law_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("decision_id", sa.String(length=255), nullable=False),
        sa.Column("court_name", sa.String(length=255), nullable=True),
        sa.Column("court_type", sa.String(length=50), nullable=True),
        sa.Column("decision_date", sa.Date(), nullable=True),
        sa.Column("case_number", sa.String(length=255), nullable=True),
        sa.Column("subject_categories", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("legal_positions", sa.JSON(), nullable=True),
        sa.Column("prompt_snippet", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["digest_id"], ["case_law_digests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_law_id"], ["case_law_cache.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_law_digest_items_digest_id", "case_law_digest_items", ["digest_id"], unique=False)
    op.create_index("ix_case_law_digest_items_case_law_id", "case_law_digest_items", ["case_law_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_case_law_digest_items_case_law_id", table_name="case_law_digest_items")
    op.drop_index("ix_case_law_digest_items_digest_id", table_name="case_law_digest_items")
    op.drop_table("case_law_digest_items")
    op.drop_index("ix_case_law_digests_created_at", table_name="case_law_digests")
    op.drop_index("ix_case_law_digests_user_id", table_name="case_law_digests")
    op.drop_table("case_law_digests")
