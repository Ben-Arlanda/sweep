"""starters: gluten free bread, dairy free spread, goat cheese, celery salt, cayenne pepper,
dried sage; "sliced bread" for bread (3e, found by the Kitchen Photo eval, ADR 0023)

Data only. Loads the starter list again, which also merges Household Ingredients with
these names into the starters (ADR 0012). Downgrade leaves the data: a merge can't be
undone.

Revision ID: c4e8b1d27f95
Revises: a3f7c2e91d64
Create Date: 2026-11-18 10:00:00

"""

from typing import Sequence, Union

from alembic import op

from app.seed import upsert_ingredients


# revision identifiers, used by Alembic.
revision: str = "c4e8b1d27f95"
down_revision: Union[str, Sequence[str], None] = "a3f7c2e91d64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    upsert_ingredients(op.get_bind())


def downgrade() -> None:
    pass  # see the module docstring
