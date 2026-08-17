"""create speakers table

Revision ID: 7cbec262203d
Revises: ac10ee64654c
Create Date: 2026-08-17 05:49:30.502112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7cbec262203d'
down_revision: Union[str, None] = 'ac10ee64654c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'speakers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recording_id', sa.Integer(), nullable=False),
        sa.Column('provisional_name', sa.String(length=100), nullable=False),
        sa.Column('real_name', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['recording_id'], ['recordings.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_speakers_id'), 'speakers', ['id'], unique=False)
    op.create_index(op.f('ix_speakers_recording_id'), 'speakers', ['recording_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_speakers_recording_id'), table_name='speakers')
    op.drop_index(op.f('ix_speakers_id'), table_name='speakers')
    op.drop_table('speakers')
