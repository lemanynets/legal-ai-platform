"""add case law cache tables

Revision ID: 20260218_0003
Revises: 20260218_0002
Create Date: 2026-02-18 01:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260218_0003"
down_revision = "20260218_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_law_cache",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("decision_id", sa.String(length=255), nullable=False),
        sa.Column("court_name", sa.String(length=255), nullable=True),
        sa.Column("court_type", sa.String(length=50), nullable=True),
        sa.Column("decision_date", sa.Date(), nullable=True),
        sa.Column("case_number", sa.String(length=255), nullable=True),
        sa.Column("subject_categories", sa.JSON(), nullable=False),
        sa.Column("legal_positions", sa.JSON(), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("reference_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "decision_id", name="uq_case_law_cache_source_decision_id"),
    )
    op.create_index("ix_case_law_cache_source", "case_law_cache", ["source"], unique=False)
    op.create_index("ix_case_law_cache_court_type", "case_law_cache", ["court_type"], unique=False)
    op.create_index("ix_case_law_cache_decision_date", "case_law_cache", ["decision_date"], unique=False)
    op.create_index(
        "ix_case_law_cache_court_type_decision_date",
        "case_law_cache",
        ["court_type", "decision_date"],
        unique=False,
    )

    op.create_table(
        "document_case_law_refs",
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("case_law_id", sa.String(length=36), nullable=False),
        sa.Column("relevance_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_law_id"], ["case_law_cache.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["generated_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "case_law_id"),
    )
    op.create_index("ix_document_case_law_refs_case_law_id", "document_case_law_refs", ["case_law_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_document_case_law_refs_case_law_id", table_name="document_case_law_refs")
    op.drop_table("document_case_law_refs")
    op.drop_index("ix_case_law_cache_court_type_decision_date", table_name="case_law_cache")
    op.drop_index("ix_case_law_cache_decision_date", table_name="case_law_cache")
    op.drop_index("ix_case_law_cache_court_type", table_name="case_law_cache")
    op.drop_index("ix_case_law_cache_source", table_name="case_law_cache")
    op.drop_table("case_law_cache")
