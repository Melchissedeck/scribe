"""add theme column to recordings

Revision ID: ac10ee64654c
Revises: 8276ac62cffc
Create Date: 2026-08-15 15:39:51.242981

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac10ee64654c'
down_revision: Union[str, None] = '8276ac62cffc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.add_column('recordings', sa.Column('theme', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('recordings', 'theme')
