"""add consent_given_at to users

Revision ID: 747675951b8b
Revises: 41a84e3faaf1
Create Date: 2026-08-29 10:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '747675951b8b'
down_revision: Union[str, None] = '41a84e3faaf1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('consent_given_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'consent_given_at')
