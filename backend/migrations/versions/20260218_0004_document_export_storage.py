"""add export storage paths to generated documents

Revision ID: 20260218_0004
Revises: 20260218_0003
Create Date: 2026-02-18 02:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260218_0004"
down_revision = "20260218_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("generated_documents", sa.Column("docx_storage_path", sa.String(length=500), nullable=True))
    op.add_column("generated_documents", sa.Column("pdf_storage_path", sa.String(length=500), nullable=True))
    op.add_column("generated_documents", sa.Column("last_exported_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("generated_documents", "last_exported_at")
    op.drop_column("generated_documents", "pdf_storage_path")
    op.drop_column("generated_documents", "docx_storage_path")
