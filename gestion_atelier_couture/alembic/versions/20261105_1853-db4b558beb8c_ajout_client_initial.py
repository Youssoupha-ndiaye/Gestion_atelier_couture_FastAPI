"""ajout client initial

Revision ID: db4b558beb8c
Revises: 86e7fdefe082
Create Date: 2026-11-05 18:53:42.508066

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db4b558beb8c'
down_revision: Union[str, Sequence[str], None] = '86e7fdefe082'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
