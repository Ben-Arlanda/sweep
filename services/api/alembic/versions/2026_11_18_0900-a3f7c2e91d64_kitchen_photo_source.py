"""kitchen change source photo: approved from a Kitchen Photo (slice 3e)

Revision ID: a3f7c2e91d64
Revises: 9b4d2e7a5c18
Create Date: 2026-11-18 09:00:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a3f7c2e91d64"
down_revision: Union[str, Sequence[str], None] = "9b4d2e7a5c18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# str_enum stores a VARCHAR with a CHECK, so a new value is a new CHECK.
NAME = "ck_kitchen_items_kitchen_change_source"


def upgrade() -> None:
    op.drop_constraint(op.f(NAME), "kitchen_items", type_="check")
    op.create_check_constraint(
        op.f(NAME),
        "kitchen_items",
        "last_change_source IN ('purchase', 'manual', 'cooked', 'photo')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE kitchen_items SET last_change_source = 'manual'"
        " WHERE last_change_source = 'photo'"
    )
    op.drop_constraint(op.f(NAME), "kitchen_items", type_="check")
    op.create_check_constraint(
        op.f(NAME), "kitchen_items", "last_change_source IN ('purchase', 'manual', 'cooked')"
    )
