"""HTTP routes for the Recipe Knowledge Base: browse, search, read one recipe, and list
the Household's own Imported Recipes."""

import uuid
from typing import Annotated, cast

from fastapi import APIRouter, Query, Request

from app import errors
from app.deps import MemberDep, SessionDep
from app.embeddings import Embedder, EmbeddingUnavailable
from app.models import Course
from app.schemas import ImportedRecipeOut, RecipeOut, RecipeSummaryOut
from app.services import recipes
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


# Before /{recipe_id}: routes match in order, and "cuisines" and "imported" aren't ids.
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
        for r, check in await recipes.imported(session, ctx.household.id)
    ]


@router.get("/{recipe_id}")
async def get_recipe(recipe_id: uuid.UUID, ctx: MemberDep, session: SessionDep) -> RecipeOut:
    return RecipeOut.model_validate(await recipes.get_recipe(session, ctx.household.id, recipe_id))
