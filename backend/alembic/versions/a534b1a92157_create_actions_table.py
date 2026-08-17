"""create actions table

Revision ID: a534b1a92157
Revises: 7cbec262203d
Create Date: 2026-08-17 06:21:46.227882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a534b1a92157'
down_revision: Union[str, None] = '7cbec262203d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recording_id', sa.Integer(), nullable=False),
        sa.Column('speaker_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['recording_id'], ['recordings.id']),
        sa.ForeignKeyConstraint(['speaker_id'], ['speakers.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_actions_id'), 'actions', ['id'], unique=False)
    op.create_index(op.f('ix_actions_recording_id'), 'actions', ['recording_id'], unique=False)
    op.create_index(op.f('ix_actions_speaker_id'), 'actions', ['speaker_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_actions_speaker_id'), table_name='actions')
    op.drop_index(op.f('ix_actions_recording_id'), table_name='actions')
    op.drop_index(op.f('ix_actions_id'), table_name='actions')
    op.drop_table('actions')
