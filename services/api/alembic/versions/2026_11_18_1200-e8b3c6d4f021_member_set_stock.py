"""Member-set stock status (ADR 0024)

Revision ID: e8b3c6d4f021
Revises: d7a2f5c8e310
Create Date: 2026-11-18 12:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8b3c6d4f021"
down_revision: Union[str, Sequence[str], None] = "d7a2f5c8e310"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "household_staples", sa.Column("low", sa.Boolean(), server_default="false", nullable=False)
    )
    # A Staple's amount: a note in the Ingredient's own unit, never used in maths.
    op.add_column("household_staples", sa.Column("quantity", sa.Numeric(12, 3), nullable=True))
    op.add_column(
        "kitchen_items", sa.Column("ran_out_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "kitchen_items", sa.Column("low", sa.Boolean(), server_default="false", nullable=False)
    )


def downgrade() -> None:
    op.drop_column("kitchen_items", "low")
    op.drop_column("kitchen_items", "ran_out_at")
    op.drop_column("household_staples", "quantity")
    op.drop_column("household_staples", "low")
