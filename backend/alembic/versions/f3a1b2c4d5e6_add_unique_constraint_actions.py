"""add unique constraint on actions (recording_id, description)

Nettoie d'abord les doublons deja presents en base (garde la ligne la plus
ancienne par groupe) avant de creer la contrainte, pour que cette migration
reste applicable automatiquement au demarrage du conteneur sans script
manuel prealable : une contrainte unique sur des donnees deja dupliquees
echouerait sinon a l'application.

Revision ID: f3a1b2c4d5e6
Revises: 747675951b8b
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a1b2c4d5e6'
down_revision: Union[str, None] = '747675951b8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Supprime les doublons (meme recording_id + meme description), en
    # conservant uniquement la ligne d'id le plus bas par groupe.
    op.execute(
        """
        DELETE FROM actions a
        USING actions b
        WHERE a.recording_id = b.recording_id
          AND a.description = b.description
          AND a.id > b.id
        """
    )

    op.create_index(
        'uq_actions_recording_description',
        'actions',
        ['recording_id', 'description'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_actions_recording_description', table_name='actions')
