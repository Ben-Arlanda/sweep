"""The Kitchen (ADR 0003): Staples are have / run out; Tracked Ingredients have a quantity.

Status is calculated when read, never stored:

    age = now - last_confirmed_at
    age >= 14 days                          → Unknown    (don't trust it; ask)
    last change was Cooked, or age >= 7 days → Estimated  (probably about right)
    otherwise                                → Confirmed  (a Member said so recently)

Every change bumps the Household's `kitchen_version` with an UPDATE on the Household
row. That also locks the row, so two changes to one Kitchen run one after the other.
Lock order is always Household before list, here and in account deletion, so two
transactions can't each hold the lock the other is waiting for (a deadlock).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.places import Place, default_place
from app.errors import Conflict, NotFound
from app.models import (
    ChangeSource,
    Household,
    HouseholdStaple,
    Ingredient,
    KitchenItem,
    ShoppingListItem,
    utcnow,
)
from app.realtime import notify_change
from app.services.households import MemberContext
from app.units import convert

CONFIRMED_FOR = timedelta(days=7)
UNKNOWN_AFTER = timedelta(days=14)
ENTITY = "kitchen"


class Status(StrEnum):
    CONFIRMED = "confirmed"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


def status_of(item: KitchenItem, now: datetime) -> Status:
    age = now - item.last_confirmed_at
    if age >= UNKNOWN_AFTER:
        return Status.UNKNOWN
    if item.last_change_source == ChangeSource.COOKED or age >= CONFIRMED_FOR:
        return Status.ESTIMATED
    return Status.CONFIRMED


@dataclass(frozen=True)
class KitchenView:
    version: int
    tracked: list[KitchenItem]
    staples: list[HouseholdStaple]


async def get_kitchen(session: AsyncSession, ctx: MemberContext) -> KitchenView:
    household = await session.get_one(Household, ctx.household.id, populate_existing=True)
    tracked = await session.execute(
        select(KitchenItem)
        .join(Ingredient, KitchenItem.ingredient_id == Ingredient.id)
        .where(KitchenItem.household_id == ctx.household.id)
        .order_by(Ingredient.category, Ingredient.name)
    )
    staples = await session.execute(
        select(HouseholdStaple)
        .join(Ingredient, HouseholdStaple.ingredient_id == Ingredient.id)
        .where(HouseholdStaple.household_id == ctx.household.id)
        .order_by(Ingredient.name)
    )
    return KitchenView(
        version=household.kitchen_version,
        tracked=list(tracked.scalars().unique()),
        staples=list(staples.scalars().unique()),
    )


# --- Manual edits ----------------------------------------------------------------------


async def set_tracked(
    session: AsyncSession,
    ctx: MemberContext,
    ingredient_id: uuid.UUID,
    quantity: Decimal | None,
) -> KitchenItem:
    """A Member says how much there is (None = "some"). That's a confirmation."""
    await _bump(session, ctx.household.id)
    ingredient = await _ingredient(session, ingredient_id)
    if await _staple(session, ctx.household.id, ingredient.id) is not None:
        raise Conflict(f"{ingredient.name} is a Staple, so it has no quantity")
    now = utcnow()
    item = await _tracked(session, ctx.household.id, ingredient.id)
    if item is None:
        item = KitchenItem(household_id=ctx.household.id, ingredient=ingredient)
        session.add(item)
    item.quantity = quantity
    item.last_change_source = ChangeSource.MANUAL
    item.last_confirmed_at = now
    item.updated_at = now
    await session.flush()
    return item


async def remove_tracked(
    session: AsyncSession, ctx: MemberContext, ingredient_id: uuid.UUID
) -> None:
    """ "We don't have any." Already gone is fine."""
    await _bump(session, ctx.household.id)
    item = await _tracked(session, ctx.household.id, ingredient_id)
    if item is not None:
        await session.delete(item)


async def set_staple(
    session: AsyncSession, ctx: MemberContext, ingredient_id: uuid.UUID, have: bool
) -> HouseholdStaple:
    """Make this a Staple (if it isn't yet) and say whether we have it."""
    await _bump(session, ctx.household.id)
    ingredient = await _ingredient(session, ingredient_id)
    staple = await _staple(session, ctx.household.id, ingredient.id)
    if staple is None:
        tracked = await _tracked(session, ctx.household.id, ingredient.id)
        staple = HouseholdStaple(household_id=ctx.household.id, ingredient=ingredient)
        if tracked is not None:
            staple.place = tracked.place  # keep where the Household moved it
            await session.delete(tracked)  # a Staple carries no quantity
        session.add(staple)
    staple.ran_out_at = None if have else (staple.ran_out_at or utcnow())
    await session.flush()
    return staple


def place_of(row: KitchenItem | HouseholdStaple) -> Place:
    """Where it lives: the Household's choice, else the default for its category."""
    return row.place or default_place(row.ingredient.name, row.ingredient.category)


async def set_place(
    session: AsyncSession, ctx: MemberContext, ingredient_id: uuid.UUID, place: Place | None
) -> Place:
    """Move a Tracked item or Staple to another Place. None puts it back to the default."""
    await _bump(session, ctx.household.id)
    row: KitchenItem | HouseholdStaple | None = await _tracked(
        session, ctx.household.id, ingredient_id
    ) or await _staple(session, ctx.household.id, ingredient_id)
    if row is None:
        raise NotFound("That isn't in your Kitchen")
    row.place = place
    await session.flush()
    return place_of(row)


async def remove_staple(
    session: AsyncSession, ctx: MemberContext, ingredient_id: uuid.UUID
) -> None:
    """Stop treating it as a Staple. It doesn't become Tracked until someone adds it."""
    await _bump(session, ctx.household.id)
    staple = await _staple(session, ctx.household.id, ingredient_id)
    if staple is not None:
        await session.delete(staple)


# --- Ticking off the Shopping List -----------------------------------------------------


async def lock(session: AsyncSession, household_id: uuid.UUID) -> None:
    """Take the Kitchen's lock before the list's (see the module docstring on lock order)."""
    await session.execute(
        select(Household.id).where(Household.id == household_id).with_for_update()
    )


async def apply_purchase(
    session: AsyncSession, household_id: uuid.UUID, item: ShoppingListItem
) -> None:
    """A linked item was ticked: we now have it. Caller holds `lock`."""
    ingredient = item.ingredient
    if ingredient is None or item.kitchen_applied:
        return
    await _bump(session, household_id)
    item.kitchen_applied = True
    item.kitchen_added_quantity = None

    staple = await _staple(session, household_id, ingredient.id)
    if staple is not None:
        staple.ran_out_at = None
        return

    amount = (
        convert(item.quantity, item.unit, ingredient.default_unit, ingredient.grams_per_ml)
        if item.quantity is not None
        else None
    )
    now = utcnow()
    existing = await _tracked(session, household_id, ingredient.id)
    if existing is None:
        session.add(
            KitchenItem(
                household_id=household_id,
                ingredient=ingredient,
                quantity=amount,
                last_change_source=ChangeSource.PURCHASE,
                last_confirmed_at=now,
                updated_at=now,
            )
        )
    else:
        trusted = status_of(existing, now) != Status.UNKNOWN
        if amount is None:
            existing.quantity = None  # bought some, amount unknown: "we have some"
        elif existing.quantity is not None and trusted:
            existing.quantity += amount
        else:
            existing.quantity = amount  # all we really know is what was just bought
        existing.last_change_source = ChangeSource.PURCHASE
        existing.last_confirmed_at = now
        existing.updated_at = now
    item.kitchen_added_quantity = amount


async def undo_purchase(
    session: AsyncSession, household_id: uuid.UUID, item: ShoppingListItem
) -> None:
    """A ticked item was unticked (usually a mis-tap): take back what ticking added.

    Best effort. A Staple stays "have" and an unmeasured purchase stays "some", because
    we can't tell what was there before. Caller holds `lock`.
    """
    if not item.kitchen_applied:
        return
    added = item.kitchen_added_quantity
    item.kitchen_applied = False
    item.kitchen_added_quantity = None
    if added is None or item.ingredient_id is None:
        return
    existing = await _tracked(session, household_id, item.ingredient_id)
    if existing is None or existing.quantity is None:
        return
    await _bump(session, household_id)
    existing.quantity = max(Decimal(0), existing.quantity - added)
    existing.updated_at = utcnow()
    if existing.quantity == 0:
        await session.delete(existing)


# --- Internals -------------------------------------------------------------------------


async def _bump(session: AsyncSession, household_id: uuid.UUID) -> None:
    version = await session.scalar(
        update(Household)
        .where(Household.id == household_id)
        .values(kitchen_version=Household.kitchen_version + 1)
        .returning(Household.kitchen_version)
    )
    assert version is not None  # the caller's own Household always exists
    await notify_change(session, household_id, ENTITY, household_id, version)


async def _ingredient(session: AsyncSession, ingredient_id: uuid.UUID) -> Ingredient:
    ingredient = await session.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise NotFound("No such Ingredient")
    return ingredient


async def _tracked(
    session: AsyncSession, household_id: uuid.UUID, ingredient_id: uuid.UUID
) -> KitchenItem | None:
    return (
        await session.execute(
            select(KitchenItem).where(
                KitchenItem.household_id == household_id,
                KitchenItem.ingredient_id == ingredient_id,
            )
        )
    ).scalar_one_or_none()


async def _staple(
    session: AsyncSession, household_id: uuid.UUID, ingredient_id: uuid.UUID
) -> HouseholdStaple | None:
    return await session.get(HouseholdStaple, (household_id, ingredient_id))
