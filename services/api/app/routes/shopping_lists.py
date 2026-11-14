"""HTTP routes for Shopping Lists and their items.

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
    ListNameIn,
    SetCheckedIn,
    ShoppingListDetailOut,
    ShoppingListOut,
    ShoppingListSummaryOut,
)
from app.services import shopping_lists as lists
from app.services.shopping_lists import UNSET

router = APIRouter(prefix="/lists", tags=["shopping-lists"])


@router.get("")
async def list_lists(ctx: MemberDep, session: SessionDep) -> list[ShoppingListSummaryOut]:
    return [
        ShoppingListSummaryOut(
            **ShoppingListOut.model_validate(s.list).model_dump(),
            unchecked_count=s.unchecked_count,
        )
        for s in await lists.list_lists(session, ctx)
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ShoppingListOut)
async def create_list(
    body: ListNameIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> ShoppingListOut:
        return ShoppingListOut.model_validate(await lists.create_list(session, ctx, body.name))

    return await idempotent(request, session, ctx, key, work, status.HTTP_201_CREATED)


@router.get("/{list_id}")
async def get_list(
    list_id: uuid.UUID, ctx: MemberDep, session: SessionDep
) -> ShoppingListDetailOut:
    lst, items = await lists.get_list(session, ctx, list_id)
    return ShoppingListDetailOut(
        **ShoppingListOut.model_validate(lst).model_dump(),
        items=[ItemOut.model_validate(i) for i in items],
    )


@router.patch("/{list_id}", response_model=ShoppingListOut)
async def rename_list(
    list_id: uuid.UUID,
    body: ListNameIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> ShoppingListOut:
        lst = await lists.rename_list(session, ctx, list_id, body.name)
        return ShoppingListOut.model_validate(lst)

    return await idempotent(request, session, ctx, key, work)


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list(
    list_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> None:
        await lists.delete_list(session, ctx, list_id)

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
