"""create transcript segments table

Revision ID: 468cc13cefe0
Revises: a534b1a92157
Create Date: 2026-08-17 06:32:36.361494

"""
from typing import Sequence, Union


revision: str = '468cc13cefe0'
down_revision: Union[str, None] = 'a534b1a92157'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema superseded by aa8238f07ac5 (transcript_segments a ete redessinee
    # avec des colonnes speaker/start/end pour l'integration pyannote).
    # Devenu un no-op pour ne pas creer deux fois la meme table lors du
    # merge des deux tetes de migration : voir la revision de merge.
    pass


def downgrade() -> None:
    pass
