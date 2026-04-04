"""add court submissions table for e-court module

Revision ID: 20260222_0008
Revises: 20260222_0007
Create Date: 2026-02-22 01:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260222_0008"
down_revision = "20260222_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "court_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("external_submission_id", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("court_name", sa.String(length=255), nullable=False),
        sa.Column("signer_method", sa.String(length=50), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("tracking_url", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["generated_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_submission_id"),
    )
    op.create_index("ix_court_submissions_user_id", "court_submissions", ["user_id"], unique=False)
    op.create_index("ix_court_submissions_document_id", "court_submissions", ["document_id"], unique=False)
    op.create_index("ix_court_submissions_status", "court_submissions", ["status"], unique=False)
    op.create_index(
        "ix_court_submissions_external_submission_id",
        "court_submissions",
        ["external_submission_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_court_submissions_external_submission_id", table_name="court_submissions")
    op.drop_index("ix_court_submissions_status", table_name="court_submissions")
    op.drop_index("ix_court_submissions_document_id", table_name="court_submissions")
    op.drop_index("ix_court_submissions_user_id", table_name="court_submissions")
    op.drop_table("court_submissions")
