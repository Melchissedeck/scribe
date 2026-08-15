"""add summary column to recordings

Revision ID: 8276ac62cffc
Revises: 67cf0db0f6f0
Create Date: 2026-08-15 11:44:33.766486

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8276ac62cffc'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('recordings', sa.Column('summary', sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column('recordings', 'summary')



