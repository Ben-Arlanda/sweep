"""ingredient groups: a recipe line's heading ("Marinade slather"), ADR 0033

Revision ID: 9526c8fd843d
Revises: 0ebce5967aa8
Create Date: 2026-11-22 11:09:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9526c8fd843d"
down_revision: Union[str, Sequence[str], None] = "0ebce5967aa8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recipe_ingredients", sa.Column("group_name", sa.String(80), nullable=True))


def downgrade() -> None:
    op.drop_column("recipe_ingredients", "group_name")
