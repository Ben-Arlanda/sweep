"""starters: 164 Ingredients the richer Seed Recipe library uses (pancetta, buttermilk,
ground coriander…), plus aliases for British and specific names (slice 4g, ADR 0028)

Data only. Loads the starter list again, which also merges Household Ingredients with
these names into the starters (ADR 0012). Downgrade leaves the data: a merge can't be
undone.

Revision ID: b5d1e7a3c962
Revises: a6d3e8f2c517
Create Date: 2026-11-19 12:00:00

"""

from typing import Sequence, Union

from alembic import op

from app.seed import upsert_ingredients


# revision identifiers, used by Alembic.
revision: str = "b5d1e7a3c962"
down_revision: Union[str, Sequence[str], None] = "a6d3e8f2c517"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    upsert_ingredients(op.get_bind())


def downgrade() -> None:
    pass  # see the module docstring
