"""HTTP routes for the Kitchen and for looking up Ingredients.

Kitchen entries are addressed by Ingredient id (`/kitchen/items/{ingredient_id}`): a
Household has at most one entry per Ingredient, so "set how much pasta we have" is a
PUT to pasta's address, and repeating it is harmless.
"""

import uuid

from fastapi import APIRouter, Query, Request, Response, status

from app.deps import MemberDep, SessionDep
from app.idempotency import IdempotencyKeyHeader
from app.models import HouseholdStaple, KitchenItem, utcnow
from app.routes.common import idempotent
from app.schemas import (
    IngredientIn,
    IngredientOut,
    KitchenItemOut,
    KitchenOut,
    PlaceIn,
    PlaceOut,
    SetQuantityIn,
    SetStapleIn,
    StapleOut,
)
from app.services import ingredients, kitchen

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
