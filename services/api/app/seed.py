"""Load reference data (starter Ingredients and their aliases). Safe to run any number of
times. Household Ingredients (ADR 0012) are never touched here.

Called from a migration so every database gets the same set; can also be run by hand:
`uv run python -m app.seed`.

Uses its own minimal table definitions rather than the ORM models in app/models.py, so a
column added later doesn't break it. But it still targets today's constraints (the
upsert needs the `(household_id, name)` one), so only migrations from 1a8824d1da9a on
may call it. A migration that changes these constraints must take over the call.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import Connection, create_engine, delete, select
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.data.ingredients import INGREDIENTS, SeedIngredient
from app.db import sqlalchemy_url
from app.services.ingredients import normalise, variants

Ingredient = sa.table(
    "ingredients",
    sa.column("id", sa.Uuid),
    sa.column("household_id", sa.Uuid),
    sa.column("name", sa.String),
    sa.column("category", sa.String),
    sa.column("default_unit", sa.String),
    sa.column("grams_per_ml", sa.Numeric),
    sa.column("is_default_staple", sa.Boolean),
)
IngredientAlias = sa.table(
    "ingredient_aliases", sa.column("alias", sa.String), sa.column("ingredient_id", sa.Uuid)
)


# Every table that points at ingredients.id, except ingredient_aliases (starters only).
# merge_into_starters must repoint each one: deleting the Household copy afterwards would
# otherwise CASCADE-delete their rows. A test compares this with the models' foreign keys.
MERGED_TABLES = (
    "household_staples",
    "kitchen_items",
    "household_excluded_ingredients",
    "household_ingredient_links",
    "shopping_list_items",
    "recipe_ingredients",
)

# Per (old Household Ingredient, new starter). Order matters: Staples move before Tracked
# rows, because a Staple carries no quantity and wins over a Tracked row (as in
# kitchen.set_staple). Where a table allows one row per Household and Ingredient, a row
# the Household already has for the starter wins and the old one goes.
_MERGE_STEPS = (
    """DELETE FROM household_staples o WHERE o.ingredient_id = :old AND EXISTS (
        SELECT 1 FROM household_staples n
        WHERE n.household_id = o.household_id AND n.ingredient_id = :new)""",
    "UPDATE household_staples SET ingredient_id = :new WHERE ingredient_id = :old",
    """DELETE FROM kitchen_items o WHERE o.ingredient_id = :old AND (
        EXISTS (SELECT 1 FROM kitchen_items n
                WHERE n.household_id = o.household_id AND n.ingredient_id = :new)
        OR EXISTS (SELECT 1 FROM household_staples s
                WHERE s.household_id = o.household_id AND s.ingredient_id = :new))""",
    # An amount in the old unit means nothing in the new one: keep it as "some".
    """UPDATE kitchen_items SET ingredient_id = :new,
        quantity = CASE WHEN :unit_changed THEN NULL ELSE quantity END
        WHERE ingredient_id = :old""",
    # A Staple just moved onto the starter beats a Tracked row the Household already had.
    """DELETE FROM kitchen_items k WHERE k.ingredient_id = :new AND EXISTS (
        SELECT 1 FROM household_staples s
        WHERE s.household_id = k.household_id AND s.ingredient_id = :new)""",
    """DELETE FROM household_excluded_ingredients o WHERE o.ingredient_id = :old AND EXISTS (
        SELECT 1 FROM household_excluded_ingredients n
        WHERE n.household_id = o.household_id AND n.ingredient_id = :new)""",
    "UPDATE household_excluded_ingredients SET ingredient_id = :new WHERE ingredient_id = :old",
    "UPDATE household_ingredient_links SET ingredient_id = :new WHERE ingredient_id = :old",
    """UPDATE shopping_list_items SET ingredient_id = :new,
        kitchen_added_quantity = CASE WHEN :unit_changed THEN NULL ELSE kitchen_added_quantity END
        WHERE ingredient_id = :old""",
    """UPDATE recipe_ingredients SET ingredient_id = :new,
        base_quantity = CASE WHEN :unit_changed THEN NULL ELSE base_quantity END
        WHERE ingredient_id = :old""",
    "DELETE FROM ingredients WHERE id = :old",
)


def upsert_ingredients(conn: Connection, seeds: Sequence[SeedIngredient] = INGREDIENTS) -> None:
    """Insert or update these starters, then merge Household Ingredients into them."""
    for seed in seeds:
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
            # household_id left NULL: a starter. NULLS NOT DISTINCT makes this conflict
            # with an existing starter of the same name, not with Household ones.
            .on_conflict_do_update(constraint="uq_ingredients_household_id_name", set_=values)
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
    merge_into_starters(conn)


def merge_into_starters(conn: Connection) -> int:
    """ADR 0012: a Household Ingredient whose name a starter now has (as its name or an
    alias, with the matcher's simple plurals) becomes that starter. Kitchen rows, Staples,
    list items, links and Dietary Rules move with it, so the Household starts matching
    Seed Recipes with nothing to do. Returns how many were merged.

    Starters are loaded into memory once (a few hundred names); then one pass over the
    Household Ingredients.
    """
    starters: dict[str, tuple[uuid.UUID, str]] = {}
    for row in conn.execute(
        select(Ingredient.c.id, Ingredient.c.name, Ingredient.c.default_unit).where(
            Ingredient.c.household_id.is_(None)
        )
    ):
        starters[row.name] = (row.id, row.default_unit)
    for alias, ingredient_id in conn.execute(
        select(IngredientAlias.c.alias, IngredientAlias.c.ingredient_id)
    ):
        unit = next((u for i, u in starters.values() if i == ingredient_id), None)
        if unit is not None:
            starters.setdefault(alias, (ingredient_id, unit))  # a name beats an alias

    household = conn.execute(
        select(Ingredient.c.id, Ingredient.c.name, Ingredient.c.default_unit).where(
            Ingredient.c.household_id.is_not(None)
        )
    ).all()
    merged = 0
    for row in household:
        match = next((starters[v] for v in variants(row.name) if v in starters), None)
        if match is None:
            continue
        new_id, new_unit = match
        params = {"old": row.id, "new": new_id, "unit_changed": new_unit != row.default_unit}
        for step in _MERGE_STEPS:
            conn.execute(sa.text(step), params)
        merged += 1
    return merged


if __name__ == "__main__":
    engine = create_engine(sqlalchemy_url(settings.database_url))
    with engine.begin() as conn:
        upsert_ingredients(conn)
        count = len(
            conn.execute(select(Ingredient.c.id).where(Ingredient.c.household_id.is_(None))).all()
        )
    print(f"{count} starter Ingredients loaded")
