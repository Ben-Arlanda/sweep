"""food groups: plain meat starters (chicken, beef, lamb, pork), "mince beef" spellings,
and Household Ingredients in Other moved to the group their words name (ADR 0030)

Data only. Loads the starter list again (which merges Household Ingredients with these
names into the starters, ADR 0012), then regroups. Downgrade leaves the data: a merge
can't be undone.

Revision ID: e3a7c5f19b42
Revises: d8c91ecb211e
Create Date: 2026-11-20 15:00:00

"""

from typing import Sequence, Union

from alembic import op

from app.seed import regroup_household_ingredients, upsert_ingredients


# revision identifiers, used by Alembic.
revision: str = "e3a7c5f19b42"
down_revision: Union[str, Sequence[str], None] = "d8c91ecb211e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    upsert_ingredients(op.get_bind())
    regroup_household_ingredients(op.get_bind())


def downgrade() -> None:
    pass  # see the module docstring
