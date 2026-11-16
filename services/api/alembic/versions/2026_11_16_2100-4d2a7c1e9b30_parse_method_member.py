"""parse method member: a Member linked the line (slice 4d)

Revision ID: 4d2a7c1e9b30
Revises: 672b53a7ca33
Create Date: 2026-11-16 21:00:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "4d2a7c1e9b30"
down_revision: Union[str, Sequence[str], None] = "672b53a7ca33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# str_enum stores a VARCHAR with a CHECK, so a new value is a new CHECK.
NAME = "ck_recipe_ingredients_parse_method"


def upgrade() -> None:
    op.drop_constraint(op.f(NAME), "recipe_ingredients", type_="check")
    op.create_check_constraint(
        op.f(NAME), "recipe_ingredients", "parse_method IN ('rule', 'llm', 'member')"
    )


def downgrade() -> None:
    op.execute("UPDATE recipe_ingredients SET parse_method = 'rule' WHERE parse_method = 'member'")
    op.drop_constraint(op.f(NAME), "recipe_ingredients", type_="check")
    op.create_check_constraint(op.f(NAME), "recipe_ingredients", "parse_method IN ('rule', 'llm')")
