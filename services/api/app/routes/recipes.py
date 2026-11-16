"""HTTP routes for the Recipe Knowledge Base: browse, search, read one recipe, and the
Household's own Imported Recipes (list, read lines, save, edit, delete)."""

import uuid
from typing import Annotated, cast

from fastapi import APIRouter, Query, Request, Response, status

from app import errors
from app.deps import MemberDep, SessionDep
from app.embeddings import Embedder, EmbeddingUnavailable
from app.idempotency import IdempotencyKeyHeader
from app.models import Course
from app.routes.common import idempotent
from app.schemas import (
    ImportedLineIn,
    ImportedRecipeIn,
    ImportedRecipeOut,
    LinesIn,
    RecipeIngredientOut,
    RecipeOut,
    RecipeSummaryOut,
)
from app.services import imported_recipes, recipes
from app.services.recipes import SEARCH_LIMIT

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("")
async def list_or_search(
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=200, description="What you feel like")] = None,
    cuisine: Annotated[str | None, Query(max_length=40)] = None,
    max_minutes: Annotated[int | None, Query(gt=0, le=1440)] = None,
    course: Course | None = None,
    exclude_ingredient: Annotated[list[uuid.UUID], Query(max_length=50)] = [],  # noqa: B006
    limit: Annotated[int, Query(gt=0, le=50)] = SEARCH_LIMIT,
    offset: Annotated[int, Query(ge=0, le=10_000, description="Browsing only")] = 0,
) -> list[RecipeSummaryOut]:
    """With `q`: recipes closest in meaning, best first. Without: all, by title, a page
    at a time (`offset`). Search has no pages: past the top results, matches get weak."""
    household_id = ctx.household.id
    filters = await recipes.filters_for(
        session, household_id, max_minutes, cuisine, exclude_ingredient, course
    )
    query = (q or "").strip()
    if not query:
        rows = await recipes.list_recipes(session, household_id, filters, limit, offset)
        return [RecipeSummaryOut.model_validate(r) for r in rows]

    embedder = cast(Embedder | None, request.app.state.embedder)
    if embedder is None:
        raise errors.Unavailable("Recipe search isn't configured on this server")
    try:
        found = await recipes.search(session, household_id, embedder, query, filters, limit)
    except EmbeddingUnavailable as error:
        raise errors.Unavailable("Recipe search is unavailable right now") from error
    return [
        RecipeSummaryOut.model_validate(r).model_copy(update={"score": round(score, 4)})
        for r, score in found
    ]


# Before /{recipe_id}: routes match in order, and "cuisines", "imported" and "lines" aren't ids.
@router.get("/cuisines")
async def list_cuisines(ctx: MemberDep, session: SessionDep) -> list[str]:
    return await recipes.cuisines(session, ctx.household.id)


@router.get("/imported")
async def list_imported(ctx: MemberDep, session: SessionDep) -> list[ImportedRecipeOut]:
    """ "Your recipes": every one, even those the Dietary Rules hide, with the reason."""
    return [
        ImportedRecipeOut(
            **RecipeSummaryOut.model_validate(r).model_dump(), rule_breaks=check.breaks
        )
        for r, check in await imported_recipes.listed(session, ctx.household.id)
    ]


@router.post("/lines")
async def read_lines(
    body: LinesIn, ctx: MemberDep, session: SessionDep
) -> list[RecipeIngredientOut]:
    """Read and match ingredient lines for the review screen. Stores nothing, uses no AI,
    so it has no limit beyond the request's size."""
    found = await imported_recipes.read_lines(
        session, ctx.household.id, [ImportedLineIn(raw_text=t) for t in body.lines]
    )
    return [RecipeIngredientOut.model_validate(line) for line in found]


@router.post("/imported", status_code=status.HTTP_201_CREATED, response_model=RecipeOut)
async def save_imported(
    body: ImportedRecipeIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    """Save from the review screen (every door ends here)."""

    async def work() -> RecipeOut:
        return RecipeOut.model_validate(await imported_recipes.save(session, ctx, body))

    return await idempotent(request, session, ctx, key, work, status.HTTP_201_CREATED)


@router.put("/imported/{recipe_id}", response_model=RecipeOut)
async def update_imported(
    recipe_id: uuid.UUID,
    body: ImportedRecipeIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> RecipeOut:
        recipe = await imported_recipes.update(session, ctx, recipe_id, body)
        return RecipeOut.model_validate(recipe)

    return await idempotent(request, session, ctx, key, work)


@router.delete("/imported/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_imported(
    recipe_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> None:
        await imported_recipes.delete(session, ctx, recipe_id)

    return await idempotent(request, session, ctx, key, work, status.HTTP_204_NO_CONTENT)


@router.get("/{recipe_id}")
async def get_recipe(recipe_id: uuid.UUID, ctx: MemberDep, session: SessionDep) -> RecipeOut:
    return RecipeOut.model_validate(await recipes.get_recipe(session, ctx.household.id, recipe_id))
