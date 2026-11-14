"""HTTP routes for the Cabinet and for looking up Ingredients.

Cabinet entries are addressed by Ingredient id (`/cabinet/items/{ingredient_id}`): a
Household has at most one entry per Ingredient, so "set how much pasta we have" is a
PUT to pasta's address, and repeating it is harmless.
"""

import uuid

from fastapi import APIRouter, Query, Request, Response, status

from app.deps import MemberDep, SessionDep
from app.idempotency import IdempotencyKeyHeader
from app.models import CabinetItem, HouseholdStaple, utcnow
from app.routes.common import idempotent
from app.schemas import (
    CabinetItemOut,
    CabinetOut,
    IngredientOut,
    SetQuantityIn,
    SetStapleIn,
    StapleOut,
)
from app.services import cabinet, ingredients

router = APIRouter(tags=["cabinet"])


def tracked_out(item: CabinetItem) -> CabinetItemOut:
    return CabinetItemOut(
        ingredient=IngredientOut.model_validate(item.ingredient),
        quantity=item.quantity,
        unit=item.ingredient.default_unit,
        status=cabinet.status_of(item, utcnow()).value,
        last_change_source=item.last_change_source,
        last_confirmed_at=item.last_confirmed_at,
    )


def staple_out(staple: HouseholdStaple) -> StapleOut:
    return StapleOut(
        ingredient=IngredientOut.model_validate(staple.ingredient),
        have=staple.ran_out_at is None,
    )


@router.get("/cabinet")
async def get_cabinet(ctx: MemberDep, session: SessionDep) -> CabinetOut:
    view = await cabinet.get_cabinet(session, ctx)
    return CabinetOut(
        version=view.version,
        tracked=[tracked_out(i) for i in view.tracked],
        staples=[staple_out(s) for s in view.staples],
    )


@router.put("/cabinet/items/{ingredient_id}", response_model=CabinetItemOut)
async def set_tracked(
    ingredient_id: uuid.UUID,
    body: SetQuantityIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> CabinetItemOut:
        return tracked_out(await cabinet.set_tracked(session, ctx, ingredient_id, body.quantity))

    return await idempotent(request, session, ctx, key, work)


@router.delete("/cabinet/items/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tracked(
    ingredient_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> None:
        await cabinet.remove_tracked(session, ctx, ingredient_id)

    return await idempotent(request, session, ctx, key, work, status.HTTP_204_NO_CONTENT)


@router.put("/cabinet/staples/{ingredient_id}", response_model=StapleOut)
async def set_staple(
    ingredient_id: uuid.UUID,
    body: SetStapleIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> StapleOut:
        return staple_out(await cabinet.set_staple(session, ctx, ingredient_id, body.have))

    return await idempotent(request, session, ctx, key, work)


@router.delete("/cabinet/staples/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_staple(
    ingredient_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> None:
        await cabinet.remove_staple(session, ctx, ingredient_id)

    return await idempotent(request, session, ctx, key, work, status.HTTP_204_NO_CONTENT)


@router.get("/ingredients")
async def search_ingredients(
    ctx: MemberDep,  # signed-in Members only, though the data isn't Household-specific
    session: SessionDep,
    q: str = Query(min_length=1, max_length=80),
) -> list[IngredientOut]:
    return [IngredientOut.model_validate(i) for i in await ingredients.search(session, q)]
