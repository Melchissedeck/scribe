"""merge transcript_segments migration heads

Revision ID: 9c6bc79ddba7
Revises: 468cc13cefe0, aa8238f07ac5
Create Date: 2026-08-24 00:03:09.203542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c6bc79ddba7'
down_revision: Union[str, None] = ('468cc13cefe0', 'aa8238f07ac5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
