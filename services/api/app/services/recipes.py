"""The Recipe Knowledge Base: loading Seed Recipes, embedding them, and searching (R1).

R1 search (plan §9) = vector similarity + hard filters. The filters are plain SQL
`WHERE` clauses, so they are exact: "under 30 minutes" can never return a 40-minute
recipe because it happened to be "similar". Similarity only decides the order.
"""

import hashlib
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import Select, exists, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors
from app.data.recipes import ATTRIBUTION, LICENCE, SeedRecipe
from app.embeddings import Embedder
from app.models import Ingredient, Recipe, RecipeEmbedding, RecipeIngredient, RecipeKind
from app.services.ingredient_lines import IngredientIndex, normalise_lines

SEARCH_LIMIT = 20


# --- Loading Seed Recipes ---------------------------------------------------------------


@dataclass
class SeedReport:
    loaded: int = 0
    removed: int = 0
    lines: int = 0
    needs_review: list[str] = field(default_factory=list)  # "slug: raw line"


async def upsert_seed_recipes(
    session: AsyncSession, seeds: Sequence[SeedRecipe], index: IngredientIndex
) -> SeedReport:
    """Make the Seed Recipes in the database match `seeds`. Safe to run any number of times."""
    report = SeedReport()
    ingredient_ids = dict((await session.execute(select(Ingredient.name, Ingredient.id))).all())
    existing = {
        r.slug: r
        for r in (await session.execute(select(Recipe).where(Recipe.kind == RecipeKind.SEED)))
        .scalars()
        .all()
    }

    for seed in seeds:
        recipe = existing.pop(seed.slug, None)
        if recipe is None:
            recipe = Recipe(kind=RecipeKind.SEED, slug=seed.slug, ingredients=[])
            session.add(recipe)
        else:
            recipe.ingredients.clear()
            await session.flush()  # delete the old lines before adding new ones
        recipe.title, recipe.summary, recipe.cuisine = seed.title, seed.summary, seed.cuisine
        recipe.servings, recipe.total_minutes = seed.servings, seed.minutes
        recipe.method = list(seed.method)
        recipe.licence, recipe.attribution = LICENCE, ATTRIBUTION

        # Rules only (no LLM) for the seed: we wrote these lines, so they should parse.
        for position, line in enumerate(await normalise_lines(seed.ingredients, index)):
            recipe.ingredients.append(
                RecipeIngredient(
                    position=position,
                    raw_text=line.raw_text,
                    ingredient_id=ingredient_ids[line.ingredient.name] if line.ingredient else None,
                    quantity=line.quantity,
                    unit=line.unit,
                    base_quantity=line.base_quantity,
                    note=line.note,
                    optional=line.optional,
                    parse_method=line.method,
                    needs_review=line.needs_review,
                )
            )
            report.lines += 1
            if line.needs_review:
                report.needs_review.append(f"{seed.slug}: {line.raw_text}")
        report.loaded += 1

    for gone in existing.values():  # removed from the seed files
        await session.delete(gone)
        report.removed += 1
    await session.flush()
    return report


# --- Embeddings -------------------------------------------------------------------------


def embedding_text(recipe: Recipe) -> str:
    """The one document per recipe that gets embedded (plan §9).

    Ingredient *names* rather than raw lines: "500 g beef mince" adds numbers that mean
    nothing to search, and the canonical name matches how people ask ("mince").
    """
    names = [
        line.ingredient.name if line.ingredient else line.raw_text for line in recipe.ingredients
    ]
    return (
        f"{recipe.title}. {recipe.summary} Cuisine: {recipe.cuisine or 'any'}. "
        f"Ingredients: {', '.join(names)}."
    )


def _hash(text: str) -> bytes:
    return hashlib.sha256(text.encode()).digest()


async def embed_missing(session: AsyncSession, embedder: Embedder, limit: int | None = None) -> int:
    """Embed recipes that have no vector for this model, or whose text has changed.

    `limit` caps how many in one go, so a caller can commit between chunks and a failure
    halfway loses nothing: the next run picks up whatever is still missing.
    """
    recipes = (await session.execute(select(Recipe))).scalars().all()
    stored = dict(
        (
            await session.execute(
                select(RecipeEmbedding.recipe_id, RecipeEmbedding.content_hash).where(
                    RecipeEmbedding.model == embedder.model
                )
            )
        ).all()
    )
    todo = []
    for recipe in recipes:
        text = embedding_text(recipe)
        if stored.get(recipe.id) != _hash(text):
            todo.append((recipe.id, text))
    todo = todo[:limit] if limit is not None else todo
    if not todo:
        return 0

    vectors = await embedder.embed([text for _, text in todo], "document")
    for (recipe_id, text), vector in zip(todo, vectors, strict=True):
        values = {"content_hash": _hash(text), "embedding": vector}
        await session.execute(
            insert(RecipeEmbedding)
            .values(recipe_id=recipe_id, model=embedder.model, **values)
            .on_conflict_do_update(index_elements=["recipe_id", "model"], set_=values)
        )
    return len(todo)


# --- Reading and searching --------------------------------------------------------------


@dataclass(frozen=True)
class RecipeFilters:
    """Hard filters: a recipe either passes or it's not in the results."""

    max_minutes: int | None = None
    cuisine: str | None = None
    exclude_ingredient_ids: Sequence[uuid.UUID] = ()


def _visible_to(household_id: uuid.UUID) -> Select[Recipe]:
    # Seed Recipes are everyone's; Imported Recipes only their own Household's.
    return select(Recipe).where(
        or_(Recipe.household_id.is_(None), Recipe.household_id == household_id)
    )


def _filtered(query: Select[Recipe], filters: RecipeFilters) -> Select[Recipe]:
    if filters.max_minutes is not None:
        query = query.where(Recipe.total_minutes <= filters.max_minutes)
    if filters.cuisine is not None:
        query = query.where(Recipe.cuisine == filters.cuisine)
    if filters.exclude_ingredient_ids:
        query = query.where(
            ~exists().where(
                RecipeIngredient.recipe_id == Recipe.id,
                RecipeIngredient.ingredient_id.in_(filters.exclude_ingredient_ids),
            )
        )
    return query


async def list_recipes(
    session: AsyncSession, household_id: uuid.UUID, filters: RecipeFilters, limit: int
) -> list[Recipe]:
    query = _filtered(_visible_to(household_id), filters).order_by(Recipe.title).limit(limit)
    return list((await session.execute(query)).scalars())


async def search(
    session: AsyncSession,
    household_id: uuid.UUID,
    embedder: Embedder,
    text: str,
    filters: RecipeFilters,
    limit: int,
) -> list[tuple[Recipe, float]]:
    """Recipes closest in meaning to `text`, best first, with a score (1 = identical)."""
    [vector] = await embedder.embed([text], "query")
    # Cosine distance: 0 = pointing the same way (same meaning), 2 = opposite.
    distance = RecipeEmbedding.embedding.cosine_distance(vector)
    query = (
        _filtered(_visible_to(household_id), filters)
        .join(
            RecipeEmbedding,
            (RecipeEmbedding.recipe_id == Recipe.id) & (RecipeEmbedding.model == embedder.model),
        )
        .add_columns(distance)
        .order_by(distance)
        .limit(limit)
    )
    rows = (await session.execute(query)).all()
    return [(recipe, 1 - float(d)) for recipe, d in rows]


async def get_recipe(
    session: AsyncSession, household_id: uuid.UUID, recipe_id: uuid.UUID
) -> Recipe:
    recipe = (
        await session.execute(_visible_to(household_id).where(Recipe.id == recipe_id))
    ).scalar_one_or_none()
    if recipe is None:
        # Same answer for "doesn't exist" and "another Household's": no existence leak.
        raise errors.NotFound("Recipe not found")
    return recipe
