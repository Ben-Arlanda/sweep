"""every recipe line has an Ingredient (ADR 0032)

A recipe line you'd shop for must have an Ingredient (a CHECK), and an Ingredient a line
uses can't be deleted (the foreign key loses ON DELETE SET NULL). No backfill: the
upgrade stops if unlinked lines remain, so they're fixed or deleted by a person first.

Revision ID: 0ebce5967aa8
Revises: e3a7c5f19b42
Create Date: 2026-11-22 09:33:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0ebce5967aa8"
down_revision: Union[str, Sequence[str], None] = "e3a7c5f19b42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK = "fk_recipe_ingredients_ingredient_id_ingredients"


def upgrade() -> None:
    unlinked = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT r.title FROM recipe_ingredients ri JOIN recipes r ON r.id = ri.recipe_id"
                " WHERE ri.ingredient_id IS NULL AND ri.needs_review GROUP BY r.title"
            )
        )
        .scalars()
        .all()
    )
    if unlinked:
        raise RuntimeError(
            "These recipes have lines with no Ingredient. Edit or delete them, then run"
            f" this again (ADR 0032): {', '.join(unlinked)}"
        )
    op.create_check_constraint(
        "linked", "recipe_ingredients", "ingredient_id IS NOT NULL OR NOT needs_review"
    )
    op.drop_constraint(FK, "recipe_ingredients", type_="foreignkey")
    op.create_foreign_key(FK, "recipe_ingredients", "ingredients", ["ingredient_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint(FK, "recipe_ingredients", type_="foreignkey")
    op.create_foreign_key(
        FK, "recipe_ingredients", "ingredients", ["ingredient_id"], ["id"], ondelete="SET NULL"
    )
    op.drop_constraint("ck_recipe_ingredients_linked", "recipe_ingredients", type_="check")
