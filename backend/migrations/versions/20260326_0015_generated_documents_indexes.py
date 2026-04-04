"""add indexes for generated_documents document_type and created_at

Revision ID: 20260326_0015
Revises: 20260309_0014
Create Date: 2026-03-26 23:47:00
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260326_0015"
down_revision = "20260309_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_generated_documents_document_type",
        "generated_documents",
        ["document_type"],
        unique=False,
    )
    op.create_index(
        "ix_generated_documents_created_at",
        "generated_documents",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_generated_documents_created_at", table_name="generated_documents")
    op.drop_index("ix_generated_documents_document_type", table_name="generated_documents")
