"""HTTP routes for the Kitchen and for looking up Ingredients.

Kitchen entries are addressed by Ingredient id (`/kitchen/items/{ingredient_id}`): a
Household has at most one entry per Ingredient, so "set how much pasta we have" is a
PUT to pasta's address, and repeating it is harmless.
"""

import uuid
from typing import Annotated, cast

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile, status

from app import errors
from app.data.places import Place
from app.deps import MemberDep, SessionDep
from app.idempotency import IdempotencyKeyHeader
from app.models import HouseholdStaple, KitchenItem, utcnow
from app.routes.common import checked_photos, idempotent
from app.schemas import (
    IngredientIn,
    IngredientOut,
    InKitchenStapleOut,
    InKitchenTrackedOut,
    KitchenItemOut,
    KitchenOut,
    KitchenPhotoApplyIn,
    KitchenPhotoOut,
    PhotoRowOut,
    PlaceIn,
    PlaceOut,
    SetQuantityIn,
    SetStapleIn,
    StapleOut,
    UsedUpOut,
)
from app.services import import_limits, ingredients, kitchen, kitchen_photos, used_up
from app.services.import_limits import MeteredKitchenReader
from app.services.kitchen import PhotoItem
from app.services.kitchen_photos import KitchenPhotoReader, PhotoRow

router = APIRouter(tags=["kitchen"])


def tracked_out(item: KitchenItem) -> KitchenItemOut:
    return KitchenItemOut(
        ingredient=IngredientOut.model_validate(item.ingredient),
        quantity=item.quantity,
        unit=item.ingredient.default_unit,
        status=kitchen.status_of(item, utcnow()).value,
        last_change_source=item.last_change_source,
        last_confirmed_at=item.last_confirmed_at,
        place=kitchen.place_of(item),
    )


def staple_out(staple: HouseholdStaple) -> StapleOut:
    return StapleOut(
        ingredient=IngredientOut.model_validate(staple.ingredient),
        have=staple.ran_out_at is None,
        place=kitchen.place_of(staple),
    )


@router.get("/kitchen")
async def get_kitchen(ctx: MemberDep, session: SessionDep) -> KitchenOut:
    view = await kitchen.get_kitchen(session, ctx)
    return KitchenOut(
        version=view.version,
        tracked=[tracked_out(i) for i in view.tracked],
        staples=[staple_out(s) for s in view.staples],
    )


@router.put("/kitchen/items/{ingredient_id}", response_model=KitchenItemOut)
async def set_tracked(
    ingredient_id: uuid.UUID,
    body: SetQuantityIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> KitchenItemOut:
        return tracked_out(await kitchen.set_tracked(session, ctx, ingredient_id, body.quantity))

    return await idempotent(request, session, ctx, key, work)


@router.delete("/kitchen/items/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tracked(
    ingredient_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> None:
        await kitchen.remove_tracked(session, ctx, ingredient_id)

    return await idempotent(request, session, ctx, key, work, status.HTTP_204_NO_CONTENT)


@router.put("/kitchen/staples/{ingredient_id}", response_model=StapleOut)
async def set_staple(
    ingredient_id: uuid.UUID,
    body: SetStapleIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> StapleOut:
        return staple_out(await kitchen.set_staple(session, ctx, ingredient_id, body.have))

    return await idempotent(request, session, ctx, key, work)


@router.delete("/kitchen/staples/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_staple(
    ingredient_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> None:
        await kitchen.remove_staple(session, ctx, ingredient_id)

    return await idempotent(request, session, ctx, key, work, status.HTTP_204_NO_CONTENT)


@router.put("/kitchen/places/{ingredient_id}", response_model=PlaceOut)
async def set_place(
    ingredient_id: uuid.UUID,
    body: PlaceIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    """Move an item to the Fridge, Freezer or Cupboard (ADR 0011)."""

    async def work() -> PlaceOut:
        return PlaceOut(place=await kitchen.set_place(session, ctx, ingredient_id, body.place))

    return await idempotent(request, session, ctx, key, work)


@router.get("/ingredients")
async def search_ingredients(
    ctx: MemberDep,
    session: SessionDep,
    q: str = Query(min_length=1, max_length=80),
) -> list[IngredientOut]:
    """Starter Ingredients plus the caller's own Household Ingredients (ADR 0012)."""
    found = await ingredients.search(session, ctx.household.id, q)
    return [IngredientOut.model_validate(i) for i in found]


@router.post("/ingredients", response_model=IngredientOut)
async def add_ingredient(
    body: IngredientIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    """The Kitchen's "Add 'kale'": the Ingredient this name means for the Household, made
    as a Household Ingredient if nothing matches (ADR 0012). 200 either way: asking twice
    returns the same Ingredient."""

    async def work() -> IngredientOut:
        found = await ingredients.resolve(session, ctx.household.id, body.name, create=True)
        assert found is not None  # IngredientIn guarantees a usable name
        return IngredientOut.model_validate(found)

    return await idempotent(request, session, ctx, key, work)


@router.post("/kitchen/used-up/{ingredient_id}", response_model=UsedUpOut)
async def mark_used_up(
    ingredient_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    """Used up (Tracked) or Ran out (Staple): out of the Kitchen and onto the list."""

    async def work() -> UsedUpOut:
        done = await used_up.used_up(session, ctx, ingredient_id)
        return UsedUpOut(list_id=done.list_id, list_item_id=done.list_item_id)

    return await idempotent(request, session, ctx, key, work)


# --- Kitchen Photos (ADR 0023) ---------------------------------------------------------


@router.post("/kitchen/photos")
async def read_kitchen_photos(
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    photos: Annotated[list[UploadFile], File(description="1 to 3 photos of items laid out")],
    place: Annotated[Place, Form(description="Where the items came from")],
) -> KitchenPhotoOut:
    """Rows for the review screen. Nothing is written: the bytes live only for this
    request, and the Kitchen changes only when the Member applies the rows."""
    inner = cast(KitchenPhotoReader | None, request.app.state.kitchen_reader)
    if inner is None:
        raise errors.Unavailable("Reading photos isn't configured on this server")
    budget = cast(int, request.app.state.daily_token_budget)
    await import_limits.start(session, ctx, "kitchen", daily_budget=budget)
    reader = MeteredKitchenReader(inner, request.app.state.sessionmaker, ctx.household.id)
    read = await checked_photos(photos, "")
    rows, _ = await kitchen_photos.from_photos(session, ctx.household.id, reader, read, place)
    return KitchenPhotoOut(place=place, rows=[_row_out(row) for row in rows])


@router.post("/kitchen/photos/apply", response_model=KitchenOut)
async def apply_kitchen_photos(
    body: KitchenPhotoApplyIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    """The ticked rows, all in one transaction. A ticked Not linked name is the Member's
    choice, so it may become a Household Ingredient. Returns the Kitchen as it is now."""

    async def work() -> KitchenOut:
        items: list[PhotoItem] = []
        for row in body.items:
            iid = row.ingredient_id
            if iid is None:
                assert row.name is not None  # PhotoItemIn guarantees one of the two
                made = await ingredients.resolve(session, ctx.household.id, row.name, create=True)
                assert made is not None  # IngredientName guarantees a usable name
                iid = made.id
            items.append(PhotoItem(iid, row.quantity))
        await kitchen.apply_photo(session, ctx.household.id, body.place, items)
        return await get_kitchen(ctx, session)

    return await idempotent(request, session, ctx, key, work)


def _row_out(row: PhotoRow) -> PhotoRowOut:
    in_kitchen: InKitchenTrackedOut | InKitchenStapleOut | None = None
    if row.staple is not None:
        in_kitchen = InKitchenStapleOut(have=row.staple.ran_out_at is None)
    elif row.tracked is not None:
        in_kitchen = InKitchenTrackedOut(
            quantity=row.tracked.quantity,
            unit=row.tracked.ingredient.default_unit,
            status=kitchen.status_of(row.tracked, utcnow()).value,
        )
    return PhotoRowOut(
        name=row.name,
        ingredient=IngredientOut.model_validate(row.ingredient) if row.ingredient else None,
        quantity=row.quantity,
        ticked=row.ticked,
        in_kitchen=in_kitchen,
    )
