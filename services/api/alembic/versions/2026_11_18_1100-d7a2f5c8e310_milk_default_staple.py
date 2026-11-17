"""milk is a default Staple: used a little at a time in meals nobody plans

Data only: loads the starter list again. New Households copy it as a Staple; existing
Households keep what they have (they can tap Make it a Staple). Downgrade leaves it.

Revision ID: d7a2f5c8e310
Revises: c4e8b1d27f95
Create Date: 2026-11-18 11:00:00

"""

from typing import Sequence, Union

from alembic import op

from app.seed import upsert_ingredients


# revision identifiers, used by Alembic.
revision: str = "d7a2f5c8e310"
down_revision: Union[str, Sequence[str], None] = "c4e8b1d27f95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    upsert_ingredients(op.get_bind())


def downgrade() -> None:
    pass  # see the module docstring
