"""starters: squid, fennel seeds, chia seeds, almond milk, almond butter, oranges (4d)

Data only, found missing by evals.link_import on real recipe sites. Loads the starter
list again (new names and aliases), which also merges Household Ingredients with these
names into the new starters (ADR 0012). Downgrade leaves the data: a merge can't be
undone.

Revision ID: 5e1b8f3a6c21
Revises: 4d2a7c1e9b30
Create Date: 2026-11-16 22:00:00

"""
from typing import Sequence, Union

from alembic import op

from app.seed import upsert_ingredients


# revision identifiers, used by Alembic.
revision: str = '5e1b8f3a6c21'
down_revision: Union[str, Sequence[str], None] = '4d2a7c1e9b30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    upsert_ingredients(op.get_bind())


def downgrade() -> None:
    pass  # see the module docstring
