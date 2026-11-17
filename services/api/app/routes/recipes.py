"""HTTP routes for the Recipe Knowledge Base: browse, search, read one recipe, and the
Household's own Imported Recipes (list, read lines, save, edit, delete)."""

import uuid
from typing import Annotated, cast

from fastapi import APIRouter, File, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors
from app.deps import MemberDep, SessionDep
from app.embeddings import Embedder, EmbeddingUnavailable
from app.idempotency import IdempotencyKeyHeader
from app.models import Course
from app.pdf_text import MAX_PDF_BYTES
from app.routes.common import idempotent
from app.schemas import (
    AdaptationOut,
    DraftLineOut,
    ImportDraftOut,
    ImportedLineIn,
    ImportedRecipeIn,
    ImportedRecipeOut,
    LinesIn,
    LinkIn,
    PasteIn,
    RecipeIngredientOut,
    RecipeOut,
    RecipeSummaryOut,
    SwapOut,
)
from app.services import adaptations, import_limits, imported_recipes, recipe_import, recipes
from app.services.households import MemberContext
from app.services.import_limits import Door, MeteredReader
from app.services.recipe_import import (
    MAX_PHOTO_BYTES,
    MAX_PHOTOS,
    Draft,
    PageFetcher,
    Photo,
    RecipeReader,
    photo_type,
)
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


# Before GET /{recipe_id}: routes match in order, and "cuisines" and "imported" aren't ids.
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


@router.post("/imports/paste")
async def read_paste(
    body: PasteIn, request: Request, ctx: MemberDep, session: SessionDep
) -> ImportDraftOut:
    """The Paste door: one model call reads the text into a draft. Stores nothing."""
    reader = await _metered_reader(request, session, ctx, "paste")
    draft = await recipe_import.from_paste(session, ctx.household.id, reader, body.text)
    return _draft_out(draft)


@router.post("/imports/photo")
async def read_photos(
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    photos: Annotated[list[UploadFile], File(description="1 to 3 photos, pages in order")],
) -> ImportDraftOut:
    """The Photo door: one model call reads the photos into a draft. Nothing is stored:
    the bytes live only for this request (and every line comes back marked Check)."""
    reader = await _metered_reader(request, session, ctx, "photo")
    if not 1 <= len(photos) <= MAX_PHOTOS:
        raise errors.InvalidInput(f"Add 1 to {MAX_PHOTOS} photos of the recipe.")
    read: list[Photo] = []
    for upload in photos:
        data = await upload.read(MAX_PHOTO_BYTES + 1)  # one byte over is enough to tell
        if len(data) > MAX_PHOTO_BYTES:
            raise errors.InvalidInput("Each photo can be up to 5 MB.")
        kind = photo_type(data)
        if kind is None:
            raise errors.InvalidInput("Photos must be JPEG, PNG or WebP.")
        read.append(Photo(media_type=kind, data=data))
    draft = await recipe_import.from_photos(session, ctx.household.id, reader, read)
    return _draft_out(draft)


@router.post("/imports/file")
async def read_file(
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    file: Annotated[UploadFile, File(description="One PDF; the first 10 pages are read")],
) -> ImportDraftOut:
    """The File door (PDF only). Nothing is stored: the bytes live only for this request."""
    reader = await _metered_reader(request, session, ctx, "file")
    data = await file.read(MAX_PDF_BYTES + 1)  # one byte over is enough to tell
    draft = await recipe_import.from_pdf(session, ctx.household.id, reader, data)
    return _draft_out(draft)


@router.post("/imports/link")
async def read_link(
    body: LinkIn, request: Request, ctx: MemberDep, session: SessionDep
) -> ImportDraftOut:
    """The Link door: the page's own recipe data, read by code. Stores nothing."""
    await import_limits.start(session, ctx, "link", daily_budget=None)  # no model: no tokens
    fetcher = cast(PageFetcher, request.app.state.page_fetcher)
    draft = await recipe_import.from_link(session, ctx.household.id, fetcher, body.url)
    return _draft_out(draft)


async def _metered_reader(
    request: Request, session: AsyncSession, ctx: MemberContext, door: Door
) -> MeteredReader:
    """The reader for a model door, once the limits allow it: the attempt is recorded,
    and every call's tokens will count toward today's budget."""
    reader = cast(RecipeReader | None, request.app.state.recipe_reader)
    if reader is None:
        raise errors.Unavailable("Reading recipes isn't configured on this server")
    budget = cast(int, request.app.state.daily_token_budget)
    await import_limits.start(session, ctx, door, daily_budget=budget)
    return MeteredReader(reader, request.app.state.sessionmaker, ctx.household.id)


def _draft_out(draft: Draft) -> ImportDraftOut:
    lines = [
        DraftLineOut(**RecipeIngredientOut.model_validate(line).model_dump(), check=check)
        for line, check in zip(draft.lines, draft.check, strict=True)
    ]
    return ImportDraftOut(
        title=draft.title,
        servings=draft.servings,
        total_minutes=draft.total_minutes,
        course=draft.course,
        cuisine=draft.cuisine,
        lines=lines,
        method=draft.method,
        source_url=draft.source_url,
        more_recipes=draft.more_recipes,
    )


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
        embedder = cast(Embedder | None, request.app.state.embedder)
        return RecipeOut.model_validate(await imported_recipes.save(session, ctx, body, embedder))

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
        embedder = cast(Embedder | None, request.app.state.embedder)
        recipe = await imported_recipes.update(session, ctx, recipe_id, body, embedder)
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


# Recipe Adaptations (ADR 0021). No POST: only an approved Proposal makes one.
@router.get("/{recipe_id}/adaptations")
async def list_adaptations(
    recipe_id: uuid.UUID, ctx: MemberDep, session: SessionDep
) -> list[AdaptationOut]:
    """This Household's Adaptations of a recipe, with their Swaps."""
    return [
        AdaptationOut(
            **RecipeSummaryOut.model_validate(a).model_dump(),
            parent_recipe_id=recipe_id,
            swaps=[
                SwapOut(replaces=line.replaces, raw_text=line.raw_text)
                for line in a.ingredients
                if line.replaces is not None
            ],
        )
        for a in await adaptations.for_parent(session, ctx.household.id, recipe_id)
    ]


@router.delete("/adaptations/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_adaptation(
    recipe_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> None:
        await adaptations.delete(session, ctx.household.id, recipe_id)

    return await idempotent(request, session, ctx, key, work, status.HTTP_204_NO_CONTENT)


@router.get("/{recipe_id}")
async def get_recipe(recipe_id: uuid.UUID, ctx: MemberDep, session: SessionDep) -> RecipeOut:
    return RecipeOut.model_validate(await recipes.get_recipe(session, ctx.household.id, recipe_id))
