"""The Recipe Knowledge Base: loading Seed Recipes, embedding them, and searching.

R1 search (plan §9) = vector similarity + hard filters. The filters are plain SQL
`WHERE` clauses, so they are exact: "under 30 minutes" can never return a 40-minute
recipe because it happened to be "similar". Similarity only decides the order.

R2 (slice 9) = Postgres full-text search over a weighted document per recipe, after the
same filters. `fuse` merges ranked lists (R3, reciprocal rank fusion).
"""

import hashlib
import logging
import re
import uuid
from collections.abc import Hashable, Sequence
from dataclasses import dataclass, field
from typing import Any

import anyio
from sqlalchemy import ColumnElement, Select, exists, func, or_, select
from sqlalchemy import text as sql
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import errors
from app.data.recipes import ATTRIBUTION, LICENCE, SeedRecipe
from app.embeddings import Embedder, EmbeddingUnavailable
from app.models import (
    Course,
    Favourite,
    Ingredient,
    Recipe,
    RecipeEmbedding,
    RecipeIngredient,
    RecipeKind,
)
from app.services import diet
from app.services.ingredient_lines import IngredientIndex, normalise_lines

log = logging.getLogger(__name__)

SEARCH_LIMIT = 20
MAX_QUERY_WORDS = 12  # a search box, not a document
RRF_K = 60  # the usual default from the original paper (Cormack et al., 2009)


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
    ingredient_ids = dict(
        (
            await session.execute(
                select(Ingredient.name, Ingredient.id).where(Ingredient.household_id.is_(None))
            )
        ).all()
    )
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
        recipe.course = seed.course
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
    # Every recipe, not just these: new aliases (migrations) change Imported ones too.
    await refresh_search_documents(session)
    return report


# --- Keyword search documents (R2) -------------------------------------------------------

# One statement builds every recipe's keyword document, so seed loading, imports and edits
# can't disagree about what's in it. Weights: A title, B Ingredient names and their
# aliases (so "shrimp" finds prawns), C cuisine and summary. Unlinked lines use their
# raw text, like embedding_text. The migration that added the column has a frozen copy.
SEARCH_DOCUMENT_SQL = """
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


async def refresh_search_documents(
    session: AsyncSession, recipe_ids: Sequence[uuid.UUID] | None = None
) -> None:
    """Rebuild the keyword documents of these recipes (all of them when None). Call
    after a recipe's title, summary, cuisine or lines change, once they're flushed."""
    if recipe_ids is None:
        await session.execute(sql(SEARCH_DOCUMENT_SQL))
    elif recipe_ids:
        await session.execute(
            sql(SEARCH_DOCUMENT_SQL + " WHERE r.id = ANY(:ids)"), {"ids": list(recipe_ids)}
        )


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


def content_hash(text: str) -> bytes:
    return hashlib.sha256(text.encode()).digest()


async def _missing(
    session: AsyncSession,
    embedder: Embedder,
    only: ColumnElement[bool] | None,
    limit: int | None,
) -> list[tuple[uuid.UUID, str]]:
    """(recipe id, text) for recipes with no vector for this model, or a stale one."""
    query = select(Recipe) if only is None else select(Recipe).where(only)
    found = (await session.execute(query)).scalars().all()
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
    for recipe in found:
        text = embedding_text(recipe)
        if stored.get(recipe.id) != content_hash(text):
            todo.append((recipe.id, text))
    return todo[:limit] if limit is not None else todo


async def _store(
    session: AsyncSession,
    embedder: Embedder,
    todo: list[tuple[uuid.UUID, str]],
    vectors: list[list[float]],
) -> None:
    for (recipe_id, text), vector in zip(todo, vectors, strict=True):
        values = {"content_hash": content_hash(text), "embedding": vector}
        await session.execute(
            insert(RecipeEmbedding)
            .values(recipe_id=recipe_id, model=embedder.model, **values)
            .on_conflict_do_update(index_elements=["recipe_id", "model"], set_=values)
        )


async def embed_missing(
    session: AsyncSession,
    embedder: Embedder,
    limit: int | None = None,
    only: ColumnElement[bool] | None = None,
) -> int:
    """Embed recipes that have no vector for this model, or whose text has changed.

    `limit` caps how many in one go, so a caller can commit between chunks and a failure
    halfway loses nothing: the next run picks up whatever is still missing. `only`
    narrows which recipes are looked at (Recipe.kind == IMPORTED after a Save).
    """
    todo = await _missing(session, embedder, only, limit)
    if not todo:
        return 0
    vectors = await embedder.embed([text for _, text in todo], "document")
    await _store(session, embedder, todo, vectors)
    return len(todo)


# Someone is waiting on Save, so the embedding gets this long and no more.
EMBED_ON_SAVE_SECONDS = 5.0
# Imported Recipes embedded per call: the new one plus any that an earlier Save missed.
CATCH_UP_BATCH = 20
IMPORTED_ONLY: ColumnElement[bool] = Recipe.kind == RecipeKind.IMPORTED


async def embed_after_save(session: AsyncSession, embedder: Embedder | None) -> int:
    """After an Imported Recipe is saved or edited: one embedding call, briefly, for it
    and any other Imported Recipe still missing a vector. Never fails the Save: without
    a vector it can still be browsed and planned by Kitchen Match, and the next Save
    (or the API starting) tries again. No job queue until slice 11."""
    if embedder is None:
        return 0
    await session.flush()  # the new lines must be visible to the query below
    todo = await _missing(session, embedder, IMPORTED_ONLY, CATCH_UP_BATCH)
    if not todo:
        return 0
    try:
        with anyio.fail_after(EMBED_ON_SAVE_SECONDS):
            vectors = await embedder.embed([text for _, text in todo], "document")
    except (EmbeddingUnavailable, TimeoutError) as error:
        log.warning("embedding after save skipped (%s): caught up later", type(error).__name__)
        return 0
    await _store(session, embedder, todo, vectors)
    return len(todo)


async def catch_up_imported(
    sessionmaker: async_sessionmaker[AsyncSession], embedder: Embedder
) -> int:
    """At API start: embed every Imported Recipe still missing a vector, in batches,
    committing each. Stops quietly at the first failure: the next start tries again."""
    done = 0
    try:
        while True:
            async with sessionmaker() as session:
                count = await embed_missing(session, embedder, CATCH_UP_BATCH, IMPORTED_ONLY)
                await session.commit()
            done += count
            if count < CATCH_UP_BATCH:
                return done
    except EmbeddingUnavailable as error:
        log.warning("embedding catch-up stopped: %s", error)
        return done


# --- Reading and searching --------------------------------------------------------------


@dataclass(frozen=True)
class RecipeFilters:
    """Hard filters: a recipe either passes or it's not in the results."""

    max_minutes: int | None = None
    cuisine: str | None = None
    course: Course | None = None  # None: every Course
    exclude_ingredient_ids: Sequence[uuid.UUID] = ()
    # Set when Dietary Rules apply: a line we can't check might break them (fail closed).
    # Same lines as diet.check_recipe: unmatched, or linked to a Household Ingredient.
    exclude_uncheckable: bool = False
    only_kind: RecipeKind | None = None  # e.g. IMPORTED: the agent's flagged imports
    favourites_of: uuid.UUID | None = None  # only this Household's Favourites


def visible_to(household_id: uuid.UUID) -> Select[Recipe]:
    # Seed Recipes are everyone's; Imported Recipes only their own Household's.
    return select(Recipe).where(
        or_(Recipe.household_id.is_(None), Recipe.household_id == household_id)
    )


async def cuisines(session: AsyncSession, household_id: uuid.UUID) -> list[str]:
    """The cuisines this Household's recipes cover, most common first. Preferences pick
    from these, so they match the words the recipes (and the agent's search) use."""
    count = func.count()
    found = await session.execute(
        select(Recipe.cuisine, count)
        .where(
            Recipe.cuisine.is_not(None),
            or_(Recipe.household_id.is_(None), Recipe.household_id == household_id),
        )
        .group_by(Recipe.cuisine)
        .order_by(count.desc(), Recipe.cuisine)
    )
    return [cuisine for cuisine, _ in found if cuisine is not None]


def _filtered(query: Select[Recipe], filters: RecipeFilters) -> Select[Recipe]:
    if filters.only_kind is not None:
        query = query.where(Recipe.kind == filters.only_kind)
    if filters.favourites_of is not None:
        query = query.where(
            exists().where(
                Favourite.recipe_id == Recipe.id, Favourite.household_id == filters.favourites_of
            )
        )
    if filters.max_minutes is not None:
        query = query.where(Recipe.total_minutes <= filters.max_minutes)
    if filters.cuisine is not None:
        query = query.where(Recipe.cuisine == filters.cuisine)
    if filters.course is not None:
        query = query.where(Recipe.course == filters.course)
    if filters.exclude_ingredient_ids:
        query = query.where(
            ~exists().where(
                RecipeIngredient.recipe_id == Recipe.id,
                RecipeIngredient.ingredient_id.in_(filters.exclude_ingredient_ids),
            )
        )
    if filters.exclude_uncheckable:
        household_made = select(Ingredient.id).where(Ingredient.household_id.is_not(None))
        query = query.where(
            ~exists().where(
                RecipeIngredient.recipe_id == Recipe.id,
                or_(
                    RecipeIngredient.needs_review.is_(True),
                    RecipeIngredient.ingredient_id.in_(household_made),
                ),
            )
        )
    return query


async def list_recipes(
    session: AsyncSession,
    household_id: uuid.UUID,
    filters: RecipeFilters,
    limit: int,
    offset: int = 0,
) -> list[Recipe]:
    # Ordered by title, then id: a stable order, so pages never repeat or skip a recipe.
    # Adaptations aren't listed on their own: they show under their parent (ADR 0021).
    query = (
        _filtered(visible_to(household_id), filters)
        .where(Recipe.kind != RecipeKind.ADAPTATION)
        .order_by(Recipe.title, Recipe.id)
        .limit(limit)
        .offset(offset)
    )
    return list((await session.execute(query)).scalars())


async def eligible(
    session: AsyncSession,
    household_id: uuid.UUID,
    filters: RecipeFilters,
    *,
    among: Sequence[uuid.UUID] | None = None,
    exclude: Sequence[uuid.UUID] = (),
) -> list[Recipe]:
    """Every recipe this Household may see that passes the filters (Dietary Rules
    included), with its lines. For Kitchen Match, which scores all of them."""
    query = _filtered(visible_to(household_id), filters)
    if among is not None:
        query = query.where(Recipe.id.in_(among))
    if exclude:
        query = query.where(Recipe.id.not_in(exclude))
    return list((await session.execute(query)).scalars())


async def search(
    session: AsyncSession,
    household_id: uuid.UUID,
    embedder: Embedder,
    text: str,
    filters: RecipeFilters,
    limit: int,
) -> list[tuple[Recipe, float]]:
    """Recipes closest in meaning to `text`, best first, with a score (1 = identical).
    Never Adaptations: they're found through their parent (ADR 0021)."""
    [vector] = await embedder.embed([text], "query")
    # Cosine distance: 0 = pointing the same way (same meaning), 2 = opposite.
    distance = RecipeEmbedding.embedding.cosine_distance(vector)
    query = (
        _filtered(visible_to(household_id), filters)
        .where(Recipe.kind != RecipeKind.ADAPTATION)
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


async def search_or_keywords(
    session: AsyncSession,
    household_id: uuid.UUID,
    embedder: Embedder | None,
    text: str,
    filters: RecipeFilters,
    limit: int,
) -> list[tuple[Recipe, float]]:
    """Search by meaning; with no embedder, or Voyage failing, by keyword (R2) instead.
    Scores are on different scales then, so callers use the order, never the number."""
    if embedder is not None:
        try:
            return await search(session, household_id, embedder, text, filters, limit)
        except EmbeddingUnavailable as error:
            log.warning("Search by meaning failed, using keywords: %s", error)
    return await keyword_search(session, household_id, text, filters, limit)


def _words(query: str) -> list[str]:
    # Letters and digits only: what's left can't be tsquery syntax, and each word becomes
    # a bound parameter anyway, never part of the SQL.
    return re.findall(r"[^\W_]+", query.lower())[:MAX_QUERY_WORDS]


async def keyword_search(
    session: AsyncSession,
    household_id: uuid.UUID,
    query: str,
    filters: RecipeFilters,
    limit: int,
) -> list[tuple[Recipe, float]]:
    """R2: recipes containing any of the query's words (stemmed: "curries" finds curry),
    best first by ts_rank_cd, after the same filters as search. Any word, not all:
    websearch_to_tsquery ANDs words, and "cosy chicken dinner" would find nothing.
    Stop words only, or no words, finds nothing. Never Adaptations (ADR 0021)."""
    words = _words(query)
    if not words:
        return []
    tsquery: ColumnElement[Any] = func.plainto_tsquery("english", words[0])
    for word in words[1:]:
        tsquery = tsquery.op("||")(func.plainto_tsquery("english", word))
    rank = func.ts_rank_cd(Recipe.search_document, tsquery)
    found = (
        _filtered(visible_to(household_id), filters)
        .where(Recipe.kind != RecipeKind.ADAPTATION, Recipe.search_document.op("@@")(tsquery))
        .add_columns(rank)
        .order_by(rank.desc(), Recipe.title, Recipe.id)
        .limit(limit)
    )
    rows = (await session.execute(found)).all()
    return [(recipe, float(score)) for recipe, score in rows]


def fuse[T: Hashable](rankings: Sequence[Sequence[T]], k: int = RRF_K) -> list[tuple[T, float]]:
    """Reciprocal rank fusion (R3): each list gives 1 / (k + rank) to every id in it, and
    ids are ordered by their total. Only ranks count, never scores, so lists scored on
    different scales (cosine similarity, ts_rank_cd) merge fairly. A bigger k flattens
    the difference between rank 1 and rank 10. Ties: the earlier list's order wins."""
    totals: dict[T, float] = {}
    first_seen: dict[T, tuple[int, int]] = {}
    for which, ranking in enumerate(rankings):
        for rank, recipe_id in enumerate(ranking, start=1):
            totals[recipe_id] = totals.get(recipe_id, 0.0) + 1 / (k + rank)
            first_seen.setdefault(recipe_id, (rank, which))
    return sorted(totals.items(), key=lambda item: (-item[1], first_seen[item[0]]))


async def get_recipe(
    session: AsyncSession, household_id: uuid.UUID, recipe_id: uuid.UUID
) -> Recipe:
    recipe = (
        await session.execute(visible_to(household_id).where(Recipe.id == recipe_id))
    ).scalar_one_or_none()
    if recipe is None:
        # Same answer for "doesn't exist" and "another Household's": no existence leak.
        raise errors.NotFound("Recipe not found")
    return recipe


async def filters_for(
    session: AsyncSession,
    household_id: uuid.UUID,
    max_minutes: int | None = None,
    cuisine: str | None = None,
    exclude_ingredient_ids: Sequence[uuid.UUID] = (),
    course: Course | None = None,
) -> RecipeFilters:
    """The caller's filters plus the Household's Dietary Rules, which always apply.

    Every way of finding recipes (the Recipes tab, the agent's search tool) goes through
    here, so no caller can forget the Rules.
    """
    rules = await diet.get_rules(session, household_id)
    banned = await diet.banned_ingredient_ids(session, rules)
    return RecipeFilters(
        max_minutes=max_minutes,
        cuisine=cuisine,
        course=course,
        exclude_ingredient_ids=sorted(set(exclude_ingredient_ids) | banned),
        exclude_uncheckable=rules.active,
    )


async def get_many(
    session: AsyncSession, household_id: uuid.UUID, recipe_ids: Sequence[str]
) -> dict[str, Recipe]:
    """The recipes this Household can see, by id (as strings). Unknown or another
    Household's ids are simply missing from the result: that's what grounding checks."""
    ids = set()
    for raw in recipe_ids:
        try:
            ids.add(uuid.UUID(raw))
        except ValueError:
            continue  # an LLM-made-up id that isn't even a UUID
    if not ids:
        return {}
    found = await session.execute(visible_to(household_id).where(Recipe.id.in_(ids)))
    return {str(r.id): r for r in found.scalars()}
