"""recipe search documents: a weighted tsvector per recipe for keyword search (R2, slice 9)

Revision ID: 9b4d2e7a5c18
Revises: 3c9e5a1f7b42
Create Date: 2026-11-17 22:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9b4d2e7a5c18"
down_revision: Union[str, Sequence[str], None] = "3c9e5a1f7b42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# A frozen copy of app.services.recipes.SEARCH_DOCUMENT_SQL as of this migration (a
# migration must keep doing what it did, even after the app's statement changes).
BACKFILL = """
UPDATE recipes AS r SET search_document =
    setweight(to_tsvector('english', r.title), 'A')
    || setweight(to_tsvector('english', coalesce((
        SELECT string_agg(coalesce(i.name, ri.raw_text) || coalesce(' ' || (
                   SELECT string_agg(a.alias, ' ') FROM ingredient_aliases AS a
                   WHERE a.ingredient_id = i.id
               ), ''), ' ')
        FROM recipe_ingredients AS ri
        LEFT JOIN ingredients AS i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = r.id
    ), '')), 'B')
    || setweight(to_tsvector('english', coalesce(r.cuisine, '') || ' ' || r.summary), 'C')
"""


def upgrade() -> None:
    op.add_column("recipes", sa.Column("search_document", postgresql.TSVECTOR(), nullable=True))
    op.execute(BACKFILL)
    op.create_index(
        "ix_recipes_search_document", "recipes", ["search_document"], postgresql_using="gin"
    )


def downgrade() -> None:
    op.drop_index("ix_recipes_search_document", table_name="recipes")
    op.drop_column("recipes", "search_document")
