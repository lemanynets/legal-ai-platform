"""create knowledge_base_entries table

Revision ID: 20260309_0014
Revises: 20260306_0013
Create Date: 2026-03-09 18:50:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260309_0014"
down_revision = "20260306_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_base_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("tags", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kb_user_id", "knowledge_base_entries", ["user_id"], unique=False)
    op.create_index("ix_kb_category", "knowledge_base_entries", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_kb_category", table_name="knowledge_base_entries")
    op.drop_index("ix_kb_user_id", table_name="knowledge_base_entries")
    op.drop_table("knowledge_base_entries")
