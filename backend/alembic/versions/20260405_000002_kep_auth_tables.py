"""add kep auth tables

Revision ID: 20260405_000002
Revises: 20260404_000001
Create Date: 2026-04-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260405_000002"
down_revision = "20260404_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("nonce", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False, server_default="local_key"),
        sa.Column("purpose", sa.Text(), nullable=False, server_default="login"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("origin", sa.Text(), nullable=True),
        sa.Column("ua_hash", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_auth_challenges_expires_at", "auth_challenges", ["expires_at"], unique=False)
    op.create_index("idx_auth_challenges_used_at", "auth_challenges", ["used_at"], unique=False)

    op.create_table(
        "user_kep_identities",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("cert_fingerprint", sa.Text(), nullable=False),
        sa.Column("subject_dn", sa.Text(), nullable=False),
        sa.Column("issuer_dn", sa.Text(), nullable=False),
        sa.Column("serial_number", sa.Text(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("cert_fingerprint", name="uq_user_kep_cert_fingerprint"),
    )
    op.create_index("idx_user_kep_identities_user_id", "user_kep_identities", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_user_kep_identities_user_id", table_name="user_kep_identities")
    op.drop_table("user_kep_identities")
    op.drop_index("idx_auth_challenges_used_at", table_name="auth_challenges")
    op.drop_index("idx_auth_challenges_expires_at", table_name="auth_challenges")
    op.drop_table("auth_challenges")
