"""Shopping List rules. A Household has one list (ADR 0009); every Member may change it,
and its Shops (the labels for where to buy an item).

Every change follows the same three steps, all inside the caller's transaction:

1. `_touch`: lock the list row (scoped to the caller's Household) and bump its version.
   The lock lines up concurrent writers to one list, so versions follow commit order.
   Shop changes touch the list too, since they change how it looks.
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
from app.models import Ingredient, Shop, ShoppingList, ShoppingListItem, utcnow
from app.realtime import notify_change
from app.services import ingredients, kitchen
from app.services.households import MemberContext
from app.units import parse_item_text

MAX_SHOPS_PER_HOUSEHOLD = 20
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
class ListView:
    shopping_list: ShoppingList
    items: list[ShoppingListItem]
    shops: list[Shop]


async def get_household_list(session: AsyncSession, ctx: MemberContext) -> ListView:
    """The Household's one list, its items (in the order added) and its Shops (A to Z)."""
    lst = (
        await session.execute(
            select(ShoppingList).where(ShoppingList.household_id == ctx.household.id)
        )
    ).scalar_one()  # created with the Household; the UNIQUE constraint keeps it to one
    items = await session.execute(
        select(ShoppingListItem)
        .where(ShoppingListItem.list_id == lst.id)
        .order_by(ShoppingListItem.created_at, ShoppingListItem.id)
    )
    return ListView(
        shopping_list=lst, items=list(items.scalars()), shops=await _shops(session, ctx)
    )


# --- Shops -------------------------------------------------------------------------


async def add_shop(session: AsyncSession, ctx: MemberContext, name: str) -> Shop:
    await _touch_household_list(session, ctx)  # also lines up two Members adding at once
    if len(await _shops(session, ctx)) >= MAX_SHOPS_PER_HOUSEHOLD:
        raise LimitReached(f"A Household can have at most {MAX_SHOPS_PER_HOUSEHOLD} shops")
    shop = Shop(household_id=ctx.household.id, name=name)
    session.add(shop)
    await _flush_unique_name(session)
    return shop


async def rename_shop(
    session: AsyncSession, ctx: MemberContext, shop_id: uuid.UUID, name: str
) -> Shop:
    await _touch_household_list(session, ctx)
    shop = await _shop(session, ctx, shop_id)
    shop.name = name
    await _flush_unique_name(session)
    return shop


async def delete_shop(session: AsyncSession, ctx: MemberContext, shop_id: uuid.UUID) -> None:
    """ "This Shop should be gone." Its items stay, as "any shop" (ON DELETE SET NULL).
    A Shop that's already gone, or isn't this Household's, leaves nothing to do."""
    await _touch_household_list(session, ctx)
    shop = await session.get(Shop, shop_id)
    if shop is not None and shop.household_id == ctx.household.id:
        # ON DELETE SET NULL would do this too, but saying it here also updates any
        # items this session already loaded, so nothing reads a stale shop_id.
        await session.execute(
            update(ShoppingListItem).where(ShoppingListItem.shop_id == shop.id).values(shop_id=None)
        )
        await session.delete(shop)


async def _flush_unique_name(session: AsyncSession) -> None:
    try:
        await session.flush()
    except IntegrityError as error:  # the request rolls back, so nothing is half-done
        raise Conflict("Your Household already has a shop with that name") from error


async def _shops(session: AsyncSession, ctx: MemberContext) -> list[Shop]:
    found = await session.execute(
        select(Shop)
        .where(Shop.household_id == ctx.household.id)
        .order_by(func.lower(Shop.name), Shop.id)
    )
    return list(found.scalars())


async def _shop(session: AsyncSession, ctx: MemberContext, shop_id: uuid.UUID) -> Shop:
    shop = (
        await session.execute(
            select(Shop).where(Shop.id == shop_id, Shop.household_id == ctx.household.id)
        )
    ).scalar_one_or_none()
    if shop is None:
        raise NotFound("No such shop in your Household")
    return shop


# --- Items -------------------------------------------------------------------------


async def add_item(
    session: AsyncSession,
    ctx: MemberContext,
    list_id: uuid.UUID,
    text: str,
    quantity: Decimal | None,
    unit: str | None,
    item_id: uuid.UUID | None = None,
    ingredient_id: uuid.UUID | None = None,
    shop_id: uuid.UUID | None = None,
) -> ShoppingListItem:
    """Add a line. "500g pasta" becomes "Pasta", 500 g, linked to the pasta Ingredient."""
    lst = await _touch(session, ctx, list_id)
    if shop_id is not None:
        await _shop(session, ctx, shop_id)  # must be this Household's
    count = await session.scalar(select(func.count()).where(ShoppingListItem.list_id == lst.id))
    if (count or 0) >= MAX_ITEMS_PER_LIST:
        raise LimitReached(f"A list can have at most {MAX_ITEMS_PER_LIST} items")

    if quantity is None and unit is None:
        name, quantity, unit = parse_item_text(text)
        if quantity is not None:
            text = name[:1].upper() + name[1:]
    ingredient = (
        await _ingredient(session, ctx, ingredient_id)
        if ingredient_id is not None
        else await ingredients.resolve(session, ctx.household.id, text, create=True)
    )

    item = ShoppingListItem(
        id=item_id or uuid.uuid4(),
        list_id=lst.id,
        text=text,
        quantity=quantity,
        unit=unit,
        added_by_member_id=ctx.member.id,
        ingredient=ingredient,
        shop_id=shop_id,
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
    ingredient_id: uuid.UUID | None | Unset = UNSET,
    shop_id: uuid.UUID | None | Unset = UNSET,
) -> ShoppingListItem:
    """Change only the fields that were sent. Two Members editing different fields of the
    same item at the same time both keep their change (last write wins *per field*).

    Relinking also saves a Household link for the item's name (ADR 0012), so the next
    "Chocolate" goes to dark chocolate without asking again.
    """
    if ingredient_id is not UNSET:
        await kitchen.lock(session, ctx.household.id)  # relinking may move Kitchen stock
    lst = await _touch(session, ctx, list_id)
    item = await _find_item(session, lst, item_id)
    if ingredient_id is not UNSET and ingredient_id != item.ingredient_id:
        # Relinking a ticked item moves what it added to the Kitchen to the new Ingredient.
        was_applied = item.kitchen_applied
        await kitchen.undo_purchase(session, ctx.household.id, item)
        item.ingredient = (
            await _ingredient(session, ctx, ingredient_id) if ingredient_id is not None else None
        )
        if was_applied:
            await kitchen.apply_purchase(session, ctx.household.id, item)
    if text is not UNSET:
        item.text = text
    if ingredient_id is not UNSET:
        await ingredients.set_link(session, ctx.household.id, item.text, item.ingredient)
    if quantity is not UNSET:
        item.quantity = quantity
    if unit is not UNSET:
        item.unit = unit
    if shop_id is not UNSET:
        if shop_id is not None:
            await _shop(session, ctx, shop_id)
        item.shop_id = shop_id
    return item


async def set_checked(
    session: AsyncSession,
    ctx: MemberContext,
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    checked: bool,
) -> ShoppingListItem:
    """Set, never toggle. Saying "checked" twice leaves it checked, credited to the first.

    Ticking a linked item puts it in the Kitchen as Confirmed; unticking takes it back.
    """
    await kitchen.lock(session, ctx.household.id)
    lst = await _touch(session, ctx, list_id)
    item = await _find_item(session, lst, item_id)
    if checked and item.checked_at is None:
        item.checked_at = utcnow()
        item.checked_by = ctx.member.id
        await kitchen.apply_purchase(session, ctx.household.id, item)
    elif not checked and item.checked_at is not None:
        item.checked_at = None
        item.checked_by = None
        await kitchen.undo_purchase(session, ctx.household.id, item)
    return item


async def delete_item(
    session: AsyncSession, ctx: MemberContext, list_id: uuid.UUID, item_id: uuid.UUID
) -> None:
    """ "This item should be gone." If someone already deleted it, that's already true."""
    lst = await _touch(session, ctx, list_id)
    item = await session.get(ShoppingListItem, item_id)
    if item is not None and item.list_id == lst.id:
        await session.delete(item)


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


async def _touch_household_list(session: AsyncSession, ctx: MemberContext) -> ShoppingList:
    list_id = await session.scalar(
        select(ShoppingList.id).where(ShoppingList.household_id == ctx.household.id)
    )
    assert list_id is not None  # every Household has its list
    return await _touch(session, ctx, list_id)


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


async def _ingredient(
    session: AsyncSession, ctx: MemberContext, ingredient_id: uuid.UUID
) -> Ingredient:
    ingredient = await ingredients.get(session, ctx.household.id, ingredient_id)
    if ingredient is None:
        raise NotFound("No such Ingredient")
    return ingredient
