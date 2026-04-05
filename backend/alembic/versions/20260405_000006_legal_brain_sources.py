"""add legal brain source tables

Revision ID: 20260405_000006
Revises: 20260405_000005
Create Date: 2026-04-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260405_000006"
down_revision = "20260405_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legal_sources",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("article", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_legal_sources_user_id", "legal_sources", ["user_id"], unique=False)

    op.create_table(
        "legal_source_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["source_id"], ["legal_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_legal_source_chunks_source_id", "legal_source_chunks", ["source_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_legal_source_chunks_source_id", table_name="legal_source_chunks")
    op.drop_table("legal_source_chunks")
    op.drop_index("idx_legal_sources_user_id", table_name="legal_sources")
    op.drop_table("legal_sources")
