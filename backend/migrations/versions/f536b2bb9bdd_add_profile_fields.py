"""add profile fields

Revision ID: f536b2bb9bdd
Revises: 20260309_0014
Create Date: 2026-03-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f536b2bb9bdd'
down_revision: Union[str, None] = '20260309_0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('entity_type', sa.String(), nullable=True))
    op.add_column('users', sa.Column('tax_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('address', sa.String(), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('users', 'phone')
    op.drop_column('users', 'address')
    op.drop_column('users', 'tax_id')
    op.drop_column('users', 'entity_type')
