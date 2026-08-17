"""create transcript segments table

Revision ID: 468cc13cefe0
Revises: a534b1a92157
Create Date: 2026-08-17 06:32:36.361494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '468cc13cefe0'
down_revision: Union[str, None] = 'a534b1a92157'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transcript_segments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recording_id', sa.Integer(), nullable=False),
        sa.Column('speaker_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.ForeignKeyConstraint(['recording_id'], ['recordings.id']),
        sa.ForeignKeyConstraint(['speaker_id'], ['speakers.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_transcript_segments_id'), 'transcript_segments', ['id'], unique=False)
    op.create_index(op.f('ix_transcript_segments_recording_id'), 'transcript_segments', ['recording_id'], unique=False)
    op.create_index(op.f('ix_transcript_segments_speaker_id'), 'transcript_segments', ['speaker_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transcript_segments_speaker_id'), table_name='transcript_segments')
    op.drop_index(op.f('ix_transcript_segments_recording_id'), table_name='transcript_segments')
    op.drop_index(op.f('ix_transcript_segments_id'), table_name='transcript_segments')
    op.drop_table('transcript_segments')
