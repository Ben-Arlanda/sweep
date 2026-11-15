"""HTTP routes for the Household's Shopping List, its items and its Shops.

Every mutation needs an `Idempotency-Key` header and runs through `idempotent`, which
replays the stored response for a retry instead of applying the change twice.
"""

import uuid

from fastapi import APIRouter, Request, Response, status

from app.deps import MemberDep, SessionDep
from app.idempotency import IdempotencyKeyHeader
from app.routes.common import idempotent
from app.schemas import (
    AddItemIn,
    EditItemIn,
    ItemOut,
    SetCheckedIn,
    ShopIn,
    ShopOut,
    ShoppingListDetailOut,
    ShoppingListOut,
)
from app.services import shopping_lists as lists
from app.services.shopping_lists import UNSET

router = APIRouter(prefix="/lists", tags=["shopping-lists"])
list_router = APIRouter(tags=["shopping-lists"])
shops_router = APIRouter(prefix="/shops", tags=["shopping-lists"])


@list_router.get("/list")
async def get_list(ctx: MemberDep, session: SessionDep) -> ShoppingListDetailOut:
    """The Household's one Shopping List, with its items and Shops (ADR 0009)."""
    view = await lists.get_household_list(session, ctx)
    return ShoppingListDetailOut(
        **ShoppingListOut.model_validate(view.shopping_list).model_dump(),
        items=[ItemOut.model_validate(i) for i in view.items],
        shops=[ShopOut.model_validate(s) for s in view.shops],
    )


@shops_router.post("", status_code=status.HTTP_201_CREATED, response_model=ShopOut)
async def add_shop(
    body: ShopIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> ShopOut:
        return ShopOut.model_validate(await lists.add_shop(session, ctx, body.name))

    return await idempotent(request, session, ctx, key, work, status.HTTP_201_CREATED)


@shops_router.patch("/{shop_id}", response_model=ShopOut)
async def rename_shop(
    shop_id: uuid.UUID,
    body: ShopIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> ShopOut:
        return ShopOut.model_validate(await lists.rename_shop(session, ctx, shop_id, body.name))

    return await idempotent(request, session, ctx, key, work)


@shops_router.delete("/{shop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shop(
    shop_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> None:
        await lists.delete_shop(session, ctx, shop_id)

    return await idempotent(request, session, ctx, key, work, status.HTTP_204_NO_CONTENT)


@router.post("/{list_id}/items", status_code=status.HTTP_201_CREATED, response_model=ItemOut)
async def add_item(
    list_id: uuid.UUID,
    body: AddItemIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> ItemOut:
        item = await lists.add_item(
            session,
            ctx,
            list_id,
            body.text,
            body.quantity,
            body.unit,
            item_id=body.id,
            ingredient_id=body.ingredient_id,
            shop_id=body.shop_id,
        )
        return ItemOut.model_validate(item)

    return await idempotent(request, session, ctx, key, work, status.HTTP_201_CREATED)


@router.patch("/{list_id}/items/{item_id}", response_model=ItemOut)
async def edit_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    body: EditItemIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    sent = body.model_fields_set

    async def work() -> ItemOut:
        item = await lists.edit_item(
            session,
            ctx,
            list_id,
            item_id,
            text=body.text if "text" in sent and body.text is not None else UNSET,
            quantity=body.quantity if "quantity" in sent else UNSET,
            unit=body.unit if "unit" in sent else UNSET,
            ingredient_id=body.ingredient_id if "ingredient_id" in sent else UNSET,
            shop_id=body.shop_id if "shop_id" in sent else UNSET,
        )
        return ItemOut.model_validate(item)

    return await idempotent(request, session, ctx, key, work)


@router.put("/{list_id}/items/{item_id}/checked", response_model=ItemOut)
async def set_checked(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    body: SetCheckedIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> ItemOut:
        item = await lists.set_checked(session, ctx, list_id, item_id, body.checked)
        return ItemOut.model_validate(item)

    return await idempotent(request, session, ctx, key, work)


@router.delete("/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> None:
        await lists.delete_item(session, ctx, list_id, item_id)

    return await idempotent(request, session, ctx, key, work, status.HTTP_204_NO_CONTENT)
