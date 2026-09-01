"""drop real_name column from speakers

Revision ID: 41a84e3faaf1
Revises: b6d481b97e70
Create Date: 2026-08-29 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41a84e3faaf1'
down_revision: Union[str, None] = 'b6d481b97e70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Champ jamais renseigne en pratique (aucune route ne l'ecrivait) :
    # supprime plutot que laisse comme colonne morte ambigue.
    op.drop_column('speakers', 'real_name')


def downgrade() -> None:
    op.add_column(
        'speakers',
        sa.Column('real_name', sa.String(length=100), nullable=True),
    )
