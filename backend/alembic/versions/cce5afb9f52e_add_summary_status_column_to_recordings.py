"""add summary_status column to recordings

Revision ID: cce5afb9f52e
Revises: fd4832b4d1e7
Create Date: 2026-08-28 10:21:31.386548

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cce5afb9f52e'
down_revision: Union[str, None] = 'fd4832b4d1e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'recordings',
        sa.Column('summary_status', sa.String(length=20), nullable=False, server_default='pending'),
    )
    # Les réunions qui ont déjà un résumé sont rétroactivement marquées
    # "done" ; le server_default couvre déjà toutes les autres.
    op.execute("UPDATE recordings SET summary_status = 'done' WHERE summary IS NOT NULL")
    op.alter_column('recordings', 'summary_status', server_default=None)


def downgrade() -> None:
    op.drop_column('recordings', 'summary_status')
