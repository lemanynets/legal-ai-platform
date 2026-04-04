"""create core tables for auth/subscriptions/generated documents

Revision ID: 20260218_0001
Revises:
Create Date: 2026-02-18 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260218_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("plan", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("analyses_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("analyses_limit", sa.Integer(), nullable=True),
        sa.Column("docs_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("docs_limit", sa.Integer(), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)

    op.create_table(
        "generated_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=False),
        sa.Column("document_category", sa.String(length=50), nullable=False),
        sa.Column("form_data", sa.JSON(), nullable=False),
        sa.Column("generated_text", sa.Text(), nullable=False),
        sa.Column("preview_text", sa.Text(), nullable=False),
        sa.Column("calculations", sa.JSON(), nullable=False),
        sa.Column("court_fee_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column("used_ai", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ai_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_documents_user_id", "generated_documents", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_generated_documents_user_id", table_name="generated_documents")
    op.drop_table("generated_documents")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_table("users")
