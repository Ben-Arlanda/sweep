"""starters: curry leaves, and "oil" as an alias of vegetable oil (4d)

Data only, found by reading a real cookbook photo. Loads the starter list again, which
also merges Household Ingredients with these names into the starters (ADR 0012): a
Household's own "oil" becomes vegetable oil. Downgrade leaves the data: a merge can't
be undone.

Revision ID: 6a7c2d9e4f10
Revises: 1307b9d90db9
Create Date: 2026-11-17 00:10:00

"""
from typing import Sequence, Union

from alembic import op

from app.seed import upsert_ingredients


# revision identifiers, used by Alembic.
revision: str = '6a7c2d9e4f10'
down_revision: Union[str, Sequence[str], None] = '1307b9d90db9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    upsert_ingredients(op.get_bind())


def downgrade() -> None:
    pass  # see the module docstring
