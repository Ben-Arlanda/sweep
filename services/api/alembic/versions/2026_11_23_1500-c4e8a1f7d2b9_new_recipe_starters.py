"""starters for the second Seed Recipe batch: basa, barramundi, brown rice, hummus and
30 more, plus aliases for how the new recipes name existing ones ("lean beef mince")

Data only. Loads the starter list again (which merges Household Ingredients with these
names into the starters, ADR 0012). Downgrade leaves the data: a merge can't be undone.

Revision ID: c4e8a1f7d2b9
Revises: b7d41e9c2a63
Create Date: 2026-11-23 15:00:00

"""

from typing import Sequence, Union

from alembic import op

from app.seed import upsert_ingredients


# revision identifiers, used by Alembic.
revision: str = "c4e8a1f7d2b9"
down_revision: Union[str, Sequence[str], None] = "b7d41e9c2a63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    upsert_ingredients(op.get_bind())


def downgrade() -> None:
    pass  # see the module docstring
