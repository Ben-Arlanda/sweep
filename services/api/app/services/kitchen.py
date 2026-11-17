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
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.places import Place, default_place
from app.errors import Conflict, InvalidInput, NotFound
from app.models import (
    ChangeSource,
    Household,
    HouseholdStaple,
    Ingredient,
    KitchenItem,
    Recipe,
    ShoppingListItem,
    utcnow,
)
from app.realtime import notify_change
from app.services import ingredients
from app.services.households import MemberContext
from app.units import convert

CONFIRMED_FOR = timedelta(days=7)
UNKNOWN_AFTER = timedelta(days=14)
ENTITY = "kitchen"


class Status(StrEnum):
    CONFIRMED = "confirmed"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class Stock(StrEnum):
    """What the Member says (ADR 0024), separate from how much we trust an amount."""

    IN_STOCK = "in_stock"
    LOW = "low"
    OUT = "out"


def stock_of(row: KitchenItem | HouseholdStaple) -> Stock:
    if row.ran_out_at is not None:
        return Stock.OUT
    return Stock.LOW if row.low else Stock.IN_STOCK


def split_out(items: list[KitchenItem]) -> tuple[list[KitchenItem], list[KitchenItem]]:
    """(have, out): Out Non-staples stay on screen but never count as "have"."""
    return [i for i in items if i.ran_out_at is None], [i for i in items if i.ran_out_at]


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
    tracked: list[KitchenItem]  # what we have (In stock or Running low)
    staples: list[HouseholdStaple]
    tracked_out: list[KitchenItem]  # Out Non-staples: for the screen only


def running_low(view: KitchenView) -> list[str]:
    """Names the Member flagged as Running low: still at home, worth topping up."""
    rows: list[KitchenItem | HouseholdStaple] = [*view.tracked, *view.staples]
    return sorted(r.ingredient.name for r in rows if r.low and r.ran_out_at is None)


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
    have, out = split_out(list(tracked.scalars().unique()))
    return KitchenView(
        version=household.kitchen_version,
        tracked=have,
        staples=list(staples.scalars().unique()),
        tracked_out=out,
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
    ingredient = await _ingredient(session, ctx.household.id, ingredient_id)
    if await _staple(session, ctx.household.id, ingredient.id) is not None:
        raise Conflict(f"{ingredient.name} is a Staple, so it has no quantity")
    now = utcnow()
    item = await _tracked(session, ctx.household.id, ingredient.id)
    if item is None:
        item = KitchenItem(household_id=ctx.household.id, ingredient=ingredient)
        session.add(item)
    item.quantity = quantity
    item.ran_out_at = None  # an amount means we have some
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
    ingredient = await _ingredient(session, ctx.household.id, ingredient_id)
    staple = await _staple(session, ctx.household.id, ingredient.id)
    if staple is None:
        tracked = await _tracked(session, ctx.household.id, ingredient.id)
        staple = HouseholdStaple(household_id=ctx.household.id, ingredient=ingredient)
        if tracked is not None:
            staple.place = tracked.place  # keep where the Household moved it
            staple.low = tracked.low
            await session.delete(tracked)  # a Staple carries no quantity
        session.add(staple)
    staple.ran_out_at = None if have else (staple.ran_out_at or utcnow())
    await session.flush()
    return staple


async def set_stock(
    session: AsyncSession, ctx: MemberContext, ingredient_id: uuid.UUID, stock: Stock
) -> KitchenItem | HouseholdStaple:
    """The Member's In stock / Running low / Out. Doesn't touch the list (see stock.py)."""
    await _bump(session, ctx.household.id)
    row: KitchenItem | HouseholdStaple | None = await _staple(
        session, ctx.household.id, ingredient_id
    ) or await _tracked(session, ctx.household.id, ingredient_id)
    if row is None:
        raise NotFound("That isn't in your Kitchen")
    row.low = stock == Stock.LOW
    row.ran_out_at = (row.ran_out_at or utcnow()) if stock == Stock.OUT else None
    if isinstance(row, KitchenItem) and stock != Stock.OUT:
        # Saying it's there is a check, like setting an amount.
        row.last_change_source = ChangeSource.MANUAL
        row.last_confirmed_at = row.updated_at = utcnow()
    await session.flush()
    return row


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
    item.kitchen_created_at = None

    staple = await _staple(session, household_id, ingredient.id)
    if staple is not None:
        staple.ran_out_at = None
        staple.low = False
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
        item.kitchen_created_at = now
    else:
        trusted = status_of(existing, now) != Status.UNKNOWN and existing.ran_out_at is None
        existing.ran_out_at = None
        existing.low = False
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
    """A ticked item was unticked (a mis-tap) or relinked: take back what ticking added.

    If this tick created the row and nothing has touched it since (still this purchase,
    same timestamp), the row goes, measured or not. Otherwise best effort: subtract a
    measured amount; a Staple stays "have" and an unmeasured purchase into a row that
    was already there stays "some". Caller holds `lock`.
    """
    if not item.kitchen_applied:
        return
    added = item.kitchen_added_quantity
    created_at = item.kitchen_created_at
    item.kitchen_applied = False
    item.kitchen_added_quantity = None
    item.kitchen_created_at = None
    if item.ingredient_id is None:
        return
    existing = await _tracked(session, household_id, item.ingredient_id)
    if existing is None:
        return
    only_this_tick = (
        created_at is not None
        and existing.last_change_source == ChangeSource.PURCHASE
        and existing.last_confirmed_at == created_at
    )
    if only_this_tick:
        await _bump(session, household_id)
        await session.delete(existing)
        return
    if added is None or existing.quantity is None:
        return
    await _bump(session, household_id)
    existing.quantity = max(Decimal(0), existing.quantity - added)
    existing.updated_at = utcnow()
    if existing.quantity == 0:
        await session.delete(existing)


# --- Kitchen Photos (ADR 0023) ---------------------------------------------------------


@dataclass(frozen=True)
class PhotoItem:
    """One approved row: the Ingredient and how much there is (None = "have some")."""

    ingredient_id: uuid.UUID
    quantity: Decimal | None


async def apply_photo(
    session: AsyncSession, household_id: uuid.UUID, place: Place, items: list[PhotoItem]
) -> None:
    """Approved rows from a Kitchen Photo of items taken out of `place`.

    The photo shows the total, so an amount replaces (never adds). No amount keeps a
    trusted one and turns an Unknown one into "have some". Never removes, and only new
    items go to `place`.
    """
    seen = [item.ingredient_id for item in items]
    if len(seen) != len(set(seen)):
        raise InvalidInput("Each Ingredient can only be listed once")
    if any(item.quantity is not None and item.quantity < 0 for item in items):
        raise InvalidInput("An amount can't be negative")
    await _bump(session, household_id)
    now = utcnow()
    for item in items:
        ingredient = await _ingredient(session, household_id, item.ingredient_id)
        staple = await _staple(session, household_id, ingredient.id)
        if staple is not None:
            staple.ran_out_at = None  # a Staple has no amount
            staple.low = False
            continue
        existing = await _tracked(session, household_id, ingredient.id)
        if existing is None:
            moved = place != default_place(ingredient.name, ingredient.category)
            existing = KitchenItem(
                household_id=household_id,
                ingredient=ingredient,
                quantity=item.quantity,
                place=place if moved else None,
            )
            session.add(existing)
        elif item.quantity is not None:
            existing.quantity = item.quantity
        elif status_of(existing, now) == Status.UNKNOWN or existing.ran_out_at:
            existing.quantity = None
        existing.ran_out_at = None
        existing.low = False
        existing.last_change_source = ChangeSource.PHOTO
        existing.last_confirmed_at = now
        existing.updated_at = now
    await session.flush()


# --- Mark as Cooked ----------------------------------------------------------------------


def _needs(recipe: Recipe, servings: int) -> dict[uuid.UUID, Decimal | None]:
    """How much of each Ingredient cooking this recipe for `servings` uses, in the
    Ingredient's own unit. None = used, amount unknown. Optional lines don't count."""
    scale = Decimal(servings) / Decimal(recipe.servings)
    needs: dict[uuid.UUID, Decimal | None] = {}
    for line in recipe.ingredients:
        if line.ingredient_id is None or line.optional:
            continue
        amount = line.base_quantity * scale if line.base_quantity is not None else None
        if line.ingredient_id in needs:
            known = needs[line.ingredient_id]
            amount = known + amount if known is not None and amount is not None else known or amount
        needs[line.ingredient_id] = amount
    return needs


async def deduct_cooked(
    session: AsyncSession, household_id: uuid.UUID, recipe: Recipe, servings: int
) -> list[dict[str, Any]]:
    """A Planned Meal was Cooked: take what it used out of the Tracked items. Caller
    holds `lock`. Returns exactly what changed, so `restore_cooked` can put it back.

    - Staples aren't touched (they have no amount), nor is anything not in the Kitchen.
    - Never below zero: a row that would go to zero or less is removed.
    - "We have some" (no amount) stays "some". Every touched row becomes Estimated.
    """
    changes: list[dict[str, Any]] = []
    for ingredient_id, need in _needs(recipe, servings).items():
        row = await _tracked(session, household_id, ingredient_id)
        if row is None or row.ran_out_at is not None:
            continue  # not here, or already Out
        change: dict[str, Any] = {
            "ingredient_id": str(ingredient_id),
            "taken": None,
            "removed": False,
            "source": row.last_change_source.value,
            "confirmed_at": row.last_confirmed_at.isoformat(),
            "place": row.place.value if row.place else None,
        }
        if need is not None and row.quantity is not None:
            taken = min(row.quantity, need)
            change["taken"] = str(taken)
            row.quantity -= taken
        if row.quantity is not None and row.quantity <= 0:
            change["removed"] = True
            await session.delete(row)
        else:
            # The amount is now our sum, not something a Member checked: Estimated.
            # last_confirmed_at stays: Cooking isn't a confirmation.
            row.last_change_source = ChangeSource.COOKED
            row.updated_at = utcnow()
        changes.append(change)
    if changes:
        await _bump(session, household_id)
    return changes


async def restore_cooked(
    session: AsyncSession, household_id: uuid.UUID, changes: list[dict[str, Any]]
) -> None:
    """Undo Cooked: put back what `deduct_cooked` took. Caller holds `lock`.

    If a Member has changed a row since (a new amount, a purchase), their change wins
    on the status; the taken amount is still added back where there's an amount."""
    for change in changes:
        ingredient_id = uuid.UUID(change["ingredient_id"])
        taken = Decimal(change["taken"]) if change["taken"] is not None else None
        row = await _tracked(session, household_id, ingredient_id)
        if row is None:
            if not change["removed"]:
                continue  # removed by a Member since: leave it gone
            ingredient = await session.get_one(Ingredient, ingredient_id)
            session.add(
                KitchenItem(
                    household_id=household_id,
                    ingredient=ingredient,
                    quantity=taken,
                    last_change_source=ChangeSource(change["source"]),
                    last_confirmed_at=datetime.fromisoformat(change["confirmed_at"]),
                    place=Place(change["place"]) if change["place"] else None,
                    updated_at=utcnow(),
                )
            )
            continue
        if taken is not None and row.quantity is not None:
            row.quantity += taken
        if row.last_change_source == ChangeSource.COOKED:
            row.last_change_source = ChangeSource(change["source"])
        row.updated_at = utcnow()
    if changes:
        await _bump(session, household_id)


async def tracked_of(
    session: AsyncSession, household_id: uuid.UUID, ingredient_id: uuid.UUID
) -> KitchenItem | None:
    return await _tracked(session, household_id, ingredient_id)


async def staple_of(
    session: AsyncSession, household_id: uuid.UUID, ingredient_id: uuid.UUID
) -> HouseholdStaple | None:
    return await _staple(session, household_id, ingredient_id)


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


async def _ingredient(
    session: AsyncSession, household_id: uuid.UUID, ingredient_id: uuid.UUID
) -> Ingredient:
    ingredient = await ingredients.get(session, household_id, ingredient_id)
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
