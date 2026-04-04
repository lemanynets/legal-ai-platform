"""add workspace_id to users for multi-tenant rbac basis

Revision ID: 20260303_0012
Revises: 20260303_0011
Create Date: 2026-03-03 12:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260303_0012"
down_revision = "20260303_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("workspace_id", sa.String(length=64), nullable=True))
    op.execute("UPDATE users SET workspace_id = 'personal' WHERE workspace_id IS NULL OR workspace_id = ''")
    op.alter_column("users", "workspace_id", nullable=False)
    op.create_index("ix_users_workspace_id", "users", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_workspace_id", table_name="users")
    op.drop_column("users", "workspace_id")
