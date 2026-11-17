"""recipe adaptations: a recipe kind with a parent, and the line each Swap replaced (5e)

Revision ID: 3c9e5a1f7b42
Revises: 8e2f4a6b1c73
Create Date: 2026-11-17 18:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3c9e5a1f7b42"
down_revision: Union[str, Sequence[str], None] = "8e2f4a6b1c73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# str_enum stores a VARCHAR with a CHECK, so a new value is a new CHECK.
KIND = "ck_recipes_recipe_kind"


def upgrade() -> None:
    op.add_column("recipes", sa.Column("parent_recipe_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_recipes_parent_recipe_id"), "recipes", ["parent_recipe_id"])
    op.create_foreign_key(
        op.f("fk_recipes_parent_recipe_id_recipes"),
        "recipes",
        "recipes",
        ["parent_recipe_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(op.f(KIND), "recipes", type_="check")
    op.create_check_constraint(op.f(KIND), "recipes", "kind IN ('seed', 'imported', 'adaptation')")
    op.create_check_constraint(
        op.f("ck_recipes_adaptation_has_parent"),
        "recipes",
        "(kind = 'adaptation') = (parent_recipe_id IS NOT NULL)",
    )
    op.add_column("recipe_ingredients", sa.Column("replaces", sa.String(length=300)))


def downgrade() -> None:
    op.execute("DELETE FROM recipes WHERE kind = 'adaptation'")
    op.drop_column("recipe_ingredients", "replaces")
    op.drop_constraint(op.f("ck_recipes_adaptation_has_parent"), "recipes", type_="check")
    op.drop_constraint(op.f(KIND), "recipes", type_="check")
    op.create_check_constraint(op.f(KIND), "recipes", "kind IN ('seed', 'imported')")
    op.drop_constraint(op.f("fk_recipes_parent_recipe_id_recipes"), "recipes", type_="foreignkey")
    op.drop_index(op.f("ix_recipes_parent_recipe_id"), table_name="recipes")
    op.drop_column("recipes", "parent_recipe_id")
