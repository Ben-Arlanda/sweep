"""starters: jalapenos, pork ribs, apple cider vinegar, taco seasoning and shells; aliases
for lemon/lime zest and juice, cooking salt, sesame seeds, olive oil spray (4d)

Data only, found by the recipe import eval on RecipeTin print-outs. Loads the starter
list again, which also merges Household Ingredients with these names into the starters
(ADR 0012). Downgrade leaves the data: a merge can't be undone.

Revision ID: 8e2f4a6b1c73
Revises: 6a7c2d9e4f10
Create Date: 2026-11-17 14:00:00

"""
from typing import Sequence, Union

from alembic import op

from app.seed import upsert_ingredients


# revision identifiers, used by Alembic.
revision: str = '8e2f4a6b1c73'
down_revision: Union[str, Sequence[str], None] = '6a7c2d9e4f10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    upsert_ingredients(op.get_bind())


def downgrade() -> None:
    pass  # see the module docstring
