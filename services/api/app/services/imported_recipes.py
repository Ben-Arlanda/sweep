"""Imported Recipes: a Household's own recipes, brought in by a Member (slice 4d).

Every door (paste, photo, link, file, type) ends on the review screen, and the review
screen saves through here. This module has no AI in it: the doors that use a model
hand over plain lines and fields, and they're checked and stored the same way.

Lines are matched with the Household's view of the Ingredients (its links, then the
starters, then its own), not the starters-only index Seed Recipes use (ADR 0012). A
line nothing matches gets a new Household Ingredient on Save, named by the parser's
cleaned name; the review screen shows it first as "New: andouille sausage" (ADR 0032).
"""

import uuid
from collections.abc import Sequence
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors
from app.embeddings import Embedder
from app.models import Favourite, Ingredient, ParseMethod, Recipe, RecipeIngredient, RecipeKind
from app.schemas import ImportedLineIn, ImportedRecipeIn
from app.services import diet, ingredients, recipe_photos, recipes
from app.services.households import MemberContext
from app.services.ingredient_lines import (
    IngredientIndex,
    KnownIngredient,
    ParsedLine,
    index_from_db,
    parse_line,
    parse_lines,
)
from app.services.recipe_photos import PhotoStore

LICENCE = "Household copy"  # a private copy for this Household, not for sharing


async def _match(
    session: AsyncSession, household_id: uuid.UUID, parsed: ParsedLine
) -> Ingredient | None:
    """The Household's matcher first (so its links win), then what the rules found:
    they also see past descriptors and "cooked", as in "2 large onions" or "cooked rice"."""
    found = await ingredients.resolve(session, household_id, parsed.name, create=False)
    if found is None and parsed.ingredient is not None:
        found = (
            await session.execute(
                select(Ingredient).where(
                    Ingredient.name == parsed.ingredient.name, ingredients.STARTERS
                )
            )
        ).scalar_one()
    return found


def _line(
    position: int, parsed: ParsedLine, found: Ingredient | None, method: ParseMethod
) -> RecipeIngredient:
    known = KnownIngredient(found.name, found.default_unit, found.grams_per_ml) if found else None
    parsed = replace(parsed, ingredient=known, method=method)
    return RecipeIngredient(
        position=position,
        raw_text=parsed.raw_text,
        ingredient_id=found.id if found else None,
        ingredient=found,
        quantity=parsed.quantity,
        unit=parsed.unit,
        base_quantity=parsed.base_quantity,  # in the matched Ingredient's own unit
        note=parsed.note,
        optional=parsed.optional,
        parse_method=parsed.method,
        needs_review=parsed.needs_review,
    )


async def read_lines(
    session: AsyncSession,
    household_id: uuid.UUID,
    lines: Sequence[ImportedLineIn],
    index: IngredientIndex | None = None,
    *,
    create: bool = False,
) -> list[RecipeIngredient]:
    """Each line read and matched, as unsaved rows: the review screen shows them, Save
    stores them. A Member's own choice of Ingredient is kept as theirs.

    A line nothing matches: with `create` (Save), a new Household Ingredient, in the
    caller's transaction; without (the review screen), just the name it would get."""
    index = index or await index_from_db(session)
    out: list[RecipeIngredient] = []
    for written, line in enumerate(lines):
        if line.ingredient_id is not None:
            chosen = await ingredients.get(session, household_id, line.ingredient_id)
            if chosen is None:
                raise errors.NotFound("Ingredient not found")
            rows = [_line(len(out), parse_line(line.raw_text, index), chosen, ParseMethod.MEMBER)]
        else:
            rows = []
            for parsed in parse_lines(line.raw_text, index):
                position = len(out) + len(rows)
                found = await _match(session, household_id, parsed)
                row = _line(position, parsed, found, ParseMethod.RULE)
                if row.needs_review:
                    row = await _new_food(session, household_id, position, parsed, row, create)
                rows.append(row)
        for row in rows:
            row.from_line = written
            row.group_name = line.group_name
        out += rows
    return out


async def _new_food(
    session: AsyncSession,
    household_id: uuid.UUID,
    position: int,
    parsed: ParsedLine,
    row: RecipeIngredient,
    create: bool,
) -> RecipeIngredient:
    name = ingredients.normalise(parsed.name)
    if len(name) > ingredients.NAME_MAX:  # a sentence, not a food: the Member splits it
        if create:
            raise errors.InvalidInput(
                f'"{parsed.raw_text[:40]}…" is too long to be one ingredient.'
                " Shorten it, or split it into two lines."
            )
        return row
    if not create:
        row.new_ingredient = name
        return row
    added = await ingredients.resolve(session, household_id, name, create=True)
    return _line(position, parsed, added, ParseMethod.RULE)


def _fill(recipe: Recipe, body: ImportedRecipeIn) -> None:
    recipe.title, recipe.course, recipe.cuisine = body.title, body.course, body.cuisine
    recipe.summary = body.summary or ""
    recipe.servings, recipe.total_minutes = body.servings, body.total_minutes
    recipe.method = list(body.method) if body.method else None
    recipe.source_url = body.source_url


async def save(
    session: AsyncSession, ctx: MemberContext, body: ImportedRecipeIn, embedder: Embedder | None
) -> Recipe:
    lines = await read_lines(session, ctx.household.id, body.lines, create=True)
    recipe = Recipe(
        kind=RecipeKind.IMPORTED,
        household_id=ctx.household.id,
        licence=LICENCE,
        attribution=f"Added by {ctx.member.display_name}",
        ingredients=lines,
    )
    _fill(recipe, body)
    session.add(recipe)
    await session.flush()
    # Imports start as Favourites: you brought it in because you like it (ADR 0025).
    session.add(
        Favourite(household_id=ctx.household.id, recipe_id=recipe.id, hearted_by=ctx.member.id)
    )
    await recipes.refresh_search_documents(session, [recipe.id])
    await recipes.embed_after_save(session, embedder)  # for search; never fails the Save
    return recipe


async def _own(session: AsyncSession, household_id: uuid.UUID, recipe_id: uuid.UUID) -> Recipe:
    """One of this Household's Imported Recipes. Seed Recipes and other Households'
    get the same 404 as ids that don't exist."""
    recipe = (
        await session.execute(
            select(Recipe).where(
                Recipe.id == recipe_id,
                Recipe.household_id == household_id,
                Recipe.kind == RecipeKind.IMPORTED,
            )
        )
    ).scalar_one_or_none()
    if recipe is None:
        raise errors.NotFound("Recipe not found")
    return recipe


async def update(
    session: AsyncSession,
    ctx: MemberContext,
    recipe_id: uuid.UUID,
    body: ImportedRecipeIn,
    embedder: Embedder | None,
) -> Recipe:
    """Replace the whole recipe (the review screen sends everything). Any Member may."""
    recipe = await _own(session, ctx.household.id, recipe_id)
    lines = await read_lines(session, ctx.household.id, body.lines, create=True)
    recipe.ingredients.clear()
    await session.flush()  # delete the old lines first: (recipe, position) is unique
    recipe.ingredients.extend(lines)
    _fill(recipe, body)
    await session.flush()
    await recipes.refresh_search_documents(session, [recipe.id])
    await recipes.embed_after_save(session, embedder)  # its text changed: a new vector
    return recipe


async def delete(
    session: AsyncSession, ctx: MemberContext, recipe_id: uuid.UUID, store: PhotoStore
) -> None:
    """Gone for good. Planned Meals that used it go with it (ON DELETE CASCADE), and its
    photo's files (ADR 0031)."""
    await session.delete(await _own(session, ctx.household.id, recipe_id))
    await session.flush()
    store.delete_prefix(recipe_photos.folder(ctx.household.id, recipe_id))


async def set_photo(
    session: AsyncSession,
    ctx: MemberContext,
    recipe_id: uuid.UUID,
    store: PhotoStore,
    data: bytes | None,
) -> Recipe:
    """Add or replace the recipe's own photo (None removes it); the old files go (ADR 0031)."""
    recipe = await _own(session, ctx.household.id, recipe_id)
    old = recipe.image
    recipe.image = (
        recipe_photos.save(store, ctx.household.id, recipe.id, data) if data is not None else None
    )
    await session.flush()
    recipe_photos.forget(store, old)
    return recipe


async def listed(
    session: AsyncSession, household_id: uuid.UUID
) -> list[tuple[Recipe, diet.RuleCheck]]:
    """This Household's Imported Recipes, newest first, each with its Rule check.

    Not filtered by the Rules, unlike every other way of finding recipes: this is the
    Household's own list ("Your recipes"), so a recipe the Rules hide still shows, with
    the reason.
    """
    rules = await diet.get_rules(session, household_id)
    found = await session.execute(
        select(Recipe)
        .where(Recipe.household_id == household_id, Recipe.kind == RecipeKind.IMPORTED)
        .order_by(Recipe.created_at.desc(), Recipe.id)
    )
    return [(r, diet.check_recipe(r, rules)) for r in found.scalars()]
