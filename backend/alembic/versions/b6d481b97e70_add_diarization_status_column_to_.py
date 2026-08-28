"""add diarization_status column to recordings

Revision ID: b6d481b97e70
Revises: cce5afb9f52e
Create Date: 2026-08-28 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6d481b97e70'
down_revision: Union[str, None] = 'cce5afb9f52e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'recordings',
        sa.Column('diarization_status', sa.String(length=20), nullable=False, server_default='pending'),
    )
    # Les réunions qui ont déjà des segments diarisés sont rétroactivement
    # marquées "done" ; le server_default couvre déjà toutes les autres.
    op.execute(
        "UPDATE recordings SET diarization_status = 'done' "
        "WHERE id IN (SELECT DISTINCT recording_id FROM transcript_segments)"
    )
    op.alter_column('recordings', 'diarization_status', server_default=None)


def downgrade() -> None:
    op.drop_column('recordings', 'diarization_status')
