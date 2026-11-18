"""Favourites: recipes a Household has hearted (ADR 0025)

Revision ID: f2c9a7d1b384
Revises: e8b3c6d4f021
Create Date: 2026-11-18 15:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2c9a7d1b384"
down_revision: Union[str, Sequence[str], None] = "e8b3c6d4f021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "favourites",
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("hearted_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hearted_by"], ["members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("household_id", "recipe_id"),
    )
    op.create_index("ix_favourites_recipe_id", "favourites", ["recipe_id"])
    # Imported Recipes start as Favourites, including the ones already saved.
    op.execute(
        "INSERT INTO favourites (household_id, recipe_id)"
        " SELECT household_id, id FROM recipes WHERE kind = 'imported'"
    )


def downgrade() -> None:
    op.drop_index("ix_favourites_recipe_id", table_name="favourites")
    op.drop_table("favourites")
