"""Shopping List rules. Every Member of a Household may change any of its lists.

Every change follows the same three steps, all inside the caller's transaction:

1. `_touch`: lock the list row (scoped to the caller's Household) and bump its version.
   The lock lines up concurrent writers to one list, so versions follow commit order.
2. Make the change.
3. Queue a change notice with the new version. Postgres only sends it if we commit.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Final, Literal

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import Conflict, LimitReached, NotFound
from app.models import ShoppingList, ShoppingListItem, utcnow
from app.realtime import notify_change
from app.services.households import MemberContext

MAX_LISTS_PER_HOUSEHOLD = 20
MAX_ITEMS_PER_LIST = 500
ENTITY = "shopping_list"


class _Unset(Enum):
    """Marks "field not sent" in edits, so `None` can still mean "clear this field".

    A one-member Enum (not a bare `object()`) so mypy can narrow `x is not UNSET`.
    """

    UNSET = "unset"


UNSET: Final = _Unset.UNSET
Unset = Literal[_Unset.UNSET]


@dataclass(frozen=True)
class ListSummary:
    list: ShoppingList
    unchecked_count: int


async def list_lists(session: AsyncSession, ctx: MemberContext) -> list[ListSummary]:
    unchecked = (
        select(func.count())
        .where(ShoppingListItem.list_id == ShoppingList.id, ShoppingListItem.checked_at.is_(None))
        .scalar_subquery()
    )
    rows = await session.execute(
        select(ShoppingList, unchecked)
        .where(ShoppingList.household_id == ctx.household.id)
        .order_by(ShoppingList.created_at, ShoppingList.id)
    )
    return [ListSummary(list=lst, unchecked_count=count) for lst, count in rows]


async def get_list(
    session: AsyncSession, ctx: MemberContext, list_id: uuid.UUID
) -> tuple[ShoppingList, list[ShoppingListItem]]:
    lst = await _find_list(session, ctx, list_id)
    items = await session.execute(
        select(ShoppingListItem)
        .where(ShoppingListItem.list_id == lst.id)
        .order_by(ShoppingListItem.created_at, ShoppingListItem.id)
    )
    return lst, list(items.scalars())


async def create_list(session: AsyncSession, ctx: MemberContext, name: str) -> ShoppingList:
    count = await session.scalar(
        select(func.count()).where(ShoppingList.household_id == ctx.household.id)
    )
    if (count or 0) >= MAX_LISTS_PER_HOUSEHOLD:
        raise LimitReached(f"A Household can have at most {MAX_LISTS_PER_HOUSEHOLD} lists")
    lst = ShoppingList(household_id=ctx.household.id, name=name)
    session.add(lst)
    await session.flush()
    await notify_change(session, ctx.household.id, ENTITY, lst.id, lst.version)
    return lst


async def rename_list(
    session: AsyncSession, ctx: MemberContext, list_id: uuid.UUID, name: str
) -> ShoppingList:
    lst = await _touch(session, ctx, list_id)
    lst.name = name
    return lst


async def delete_list(session: AsyncSession, ctx: MemberContext, list_id: uuid.UUID) -> None:
    lst = await _touch(session, ctx, list_id)
    await session.delete(lst)  # ON DELETE CASCADE removes its items


async def add_item(
    session: AsyncSession,
    ctx: MemberContext,
    list_id: uuid.UUID,
    text: str,
    quantity: Decimal | None,
    unit: str | None,
    item_id: uuid.UUID | None = None,
) -> ShoppingListItem:
    lst = await _touch(session, ctx, list_id)
    count = await session.scalar(select(func.count()).where(ShoppingListItem.list_id == lst.id))
    if (count or 0) >= MAX_ITEMS_PER_LIST:
        raise LimitReached(f"A list can have at most {MAX_ITEMS_PER_LIST} items")
    item = ShoppingListItem(
        id=item_id or uuid.uuid4(),
        list_id=lst.id,
        text=text,
        quantity=quantity,
        unit=unit,
        added_by_member_id=ctx.member.id,
    )
    session.add(item)
    try:
        await session.flush()
    except IntegrityError as error:  # the request rolls back, so nothing is half-done
        raise Conflict("An item with this id already exists") from error
    return item


async def edit_item(
    session: AsyncSession,
    ctx: MemberContext,
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    *,
    text: str | Unset = UNSET,
    quantity: Decimal | None | Unset = UNSET,
    unit: str | None | Unset = UNSET,
) -> ShoppingListItem:
    """Change only the fields that were sent. Two Members editing different fields of the
    same item at the same time both keep their change (last write wins *per field*)."""
    lst = await _touch(session, ctx, list_id)
    item = await _find_item(session, lst, item_id)
    if text is not UNSET:
        item.text = text
    if quantity is not UNSET:
        item.quantity = quantity
    if unit is not UNSET:
        item.unit = unit
    return item


async def set_checked(
    session: AsyncSession,
    ctx: MemberContext,
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    checked: bool,
) -> ShoppingListItem:
    """Set, never toggle. Saying "checked" twice leaves it checked, credited to the first."""
    lst = await _touch(session, ctx, list_id)
    item = await _find_item(session, lst, item_id)
    if checked and item.checked_at is None:
        item.checked_at = utcnow()
        item.checked_by = ctx.member.id
    elif not checked:
        item.checked_at = None
        item.checked_by = None
    return item


async def delete_item(
    session: AsyncSession, ctx: MemberContext, list_id: uuid.UUID, item_id: uuid.UUID
) -> None:
    """ "This item should be gone." If someone already deleted it, that's already true."""
    lst = await _touch(session, ctx, list_id)
    item = await session.get(ShoppingListItem, item_id)
    if item is not None and item.list_id == lst.id:
        await session.delete(item)


async def _find_list(session: AsyncSession, ctx: MemberContext, list_id: uuid.UUID) -> ShoppingList:
    lst = (
        await session.execute(
            select(ShoppingList).where(
                ShoppingList.id == list_id, ShoppingList.household_id == ctx.household.id
            )
        )
    ).scalar_one_or_none()
    if lst is None:
        raise NotFound("No such list in your Household")
    return lst


async def _touch(session: AsyncSession, ctx: MemberContext, list_id: uuid.UUID) -> ShoppingList:
    # One statement: Household check, row lock (UPDATE locks it until commit) and bump.
    version = await session.scalar(
        update(ShoppingList)
        .where(ShoppingList.id == list_id, ShoppingList.household_id == ctx.household.id)
        .values(version=ShoppingList.version + 1)
        .returning(ShoppingList.version)
    )
    if version is None:
        raise NotFound("No such list in your Household")
    await notify_change(session, ctx.household.id, ENTITY, list_id, version)
    # populate_existing: the session may hold this row from earlier with the old version.
    return (
        await session.execute(
            select(ShoppingList)
            .where(ShoppingList.id == list_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _find_item(
    session: AsyncSession, lst: ShoppingList, item_id: uuid.UUID
) -> ShoppingListItem:
    # Scoped by list, which `_touch` already scoped by Household. An item id from another
    # Household's list is simply "not found" here.
    item = (
        await session.execute(
            select(ShoppingListItem).where(
                ShoppingListItem.id == item_id, ShoppingListItem.list_id == lst.id
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise NotFound("No such item on this list")
    return item
