"""Member-set stock status and Staple package amounts (ADR 0024)

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
    op.add_column("household_staples", sa.Column("pack_quantity", sa.Numeric(5, 2), nullable=True))
    op.add_column("household_staples", sa.Column("pack_unit", sa.String(12), nullable=True))
    op.create_check_constraint(
        op.f("ck_household_staples_pack_both_or_neither"),
        "household_staples",
        "(pack_quantity IS NULL) = (pack_unit IS NULL)",
    )
    op.add_column(
        "kitchen_items", sa.Column("ran_out_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "kitchen_items", sa.Column("low", sa.Boolean(), server_default="false", nullable=False)
    )


def downgrade() -> None:
    op.drop_column("kitchen_items", "low")
    op.drop_column("kitchen_items", "ran_out_at")
    op.drop_constraint(
        op.f("ck_household_staples_pack_both_or_neither"), "household_staples", type_="check"
    )
    op.drop_column("household_staples", "pack_unit")
    op.drop_column("household_staples", "pack_quantity")
    op.drop_column("household_staples", "low")
