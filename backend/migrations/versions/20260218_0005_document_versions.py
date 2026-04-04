"""add document versions table

Revision ID: 20260218_0005
Revises: 20260218_0004
Create Date: 2026-02-18 05:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260218_0005"
down_revision = "20260218_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("generated_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["generated_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_versions_doc_version"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"], unique=False)
    op.create_index("ix_document_versions_user_id", "document_versions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_document_versions_user_id", table_name="document_versions")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")
