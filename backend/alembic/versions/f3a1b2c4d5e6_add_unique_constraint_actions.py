"""add unique constraint on actions (recording_id, description)

Revision ID: f3a1b2c4d5e6
Revises: 83dc569e95e0
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a1b2c4d5e6'
down_revision: Union[str, None] = '83dc569e95e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'uq_actions_recording_description',
        'actions',
        ['recording_id', 'description'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_actions_recording_description', table_name='actions')
