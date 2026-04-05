"""baseline schema checkpoint

Revision ID: 20260404_000001
Revises:
Create Date: 2026-04-04
"""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "20260404_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Baseline checkpoint.

    Existing environments already bootstrap schema through application startup.
    Next migrations should be incremental from this revision.
    """
    pass


def downgrade() -> None:
    pass
