"""Load reference data (Ingredients and their aliases). Safe to run any number of times.

Called from migrations so every database gets the same set; can also be run by hand:
`uv run python -m app.seed`.

Uses its own minimal table definitions rather than the ORM models in app/models.py. A
migration that imports today's models breaks as soon as a later model adds a column
that doesn't exist yet at that point in the migration history. These definitions list
only the columns this code writes.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy import Connection, create_engine, delete, select
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.data.ingredients import INGREDIENTS
from app.db import sqlalchemy_url
from app.services.ingredients import normalise

Ingredient = sa.table(
    "ingredients",
    sa.column("id", sa.Uuid),
    sa.column("name", sa.String),
    sa.column("category", sa.String),
    sa.column("default_unit", sa.String),
    sa.column("grams_per_ml", sa.Numeric),
    sa.column("is_default_staple", sa.Boolean),
)
IngredientAlias = sa.table(
    "ingredient_aliases", sa.column("alias", sa.String), sa.column("ingredient_id", sa.Uuid)
)


def upsert_ingredients(conn: Connection) -> None:
    for seed in INGREDIENTS:
        values = {
            "name": seed.name,
            "category": seed.category,
            "default_unit": seed.default_unit,
            "grams_per_ml": seed.grams_per_ml,
            "is_default_staple": seed.is_default_staple,
        }
        ingredient_id = conn.execute(
            insert(Ingredient)
            .values(id=uuid.uuid4(), **values)
            .on_conflict_do_update(index_elements=["name"], set_=values)
            .returning(Ingredient.c.id)
        ).scalar_one()

        aliases = {normalise(a) for a in seed.aliases} - {normalise(seed.name)}
        # Replace this Ingredient's aliases with the seed's (an alias can move between
        # Ingredients when the seed is corrected).
        conn.execute(
            delete(IngredientAlias).where(IngredientAlias.c.ingredient_id == ingredient_id)
        )
        for alias in aliases:
            conn.execute(
                insert(IngredientAlias)
                .values(alias=alias, ingredient_id=ingredient_id)
                .on_conflict_do_update(
                    index_elements=["alias"], set_={"ingredient_id": ingredient_id}
                )
            )


if __name__ == "__main__":
    engine = create_engine(sqlalchemy_url(settings.database_url))
    with engine.begin() as conn:
        upsert_ingredients(conn)
        count = len(conn.execute(select(Ingredient.c.id)).all())
    print(f"{count} Ingredients loaded")
