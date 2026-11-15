"""starters: kale, cavolo nero, silverbeet (slice 3d)

Data only. Loads the starter list again, which also merges Household Ingredients with
these names into the new starters (ADR 0012): a Household's "kale" becomes the shared
kale, Kitchen rows and all. Downgrade leaves the data: a merge can't be undone.

Revision ID: d3fd95252bb5
Revises: 0c1628713814
Create Date: 2026-11-15 17:51:19.231176

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.seed import upsert_ingredients


# revision identifiers, used by Alembic.
revision: str = 'd3fd95252bb5'
down_revision: Union[str, Sequence[str], None] = '0c1628713814'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    upsert_ingredients(op.get_bind())


def downgrade() -> None:
    """Downgrade schema."""
    pass  # see the module docstring
