"""Stock status and the Shopping List (ADR 0024).

Most households plan only dinners, so breakfast and lunch use never reaches the Kitchen
as a Cooked meal. When a Member says something's gone, that's the moment to buy it again:
- a Staple set to Out goes on the list straight away (the app offers Undo);
- a Non-staple set to Out stays in the Kitchen as Out, and the app only *offers* to add it.
Adding skips anything already on the list unticked (ADR 0016's rule).

Kitchen first, then the list: the lock order every Kitchen and list change keeps.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFound
from app.models import HouseholdStaple, Ingredient
from app.services import kitchen, shopping_lists
from app.services.households import MemberContext
from app.services.kitchen import Stock


@dataclass(frozen=True)
class OnList:
    list_id: uuid.UUID
    list_item_id: uuid.UUID | None  # None: it was already on the list


@dataclass(frozen=True)
class StockChange:
    stock: Stock
    on_list: OnList | None  # set when a Staple ran out and went on the list


async def set_stock(
    session: AsyncSession, ctx: MemberContext, ingredient_id: uuid.UUID, stock: Stock
) -> StockChange:
    row = await kitchen.set_stock(session, ctx, ingredient_id, stock)
    on_list = None
    if stock == Stock.OUT and isinstance(row, HouseholdStaple):
        on_list = await _add(session, ctx, row.ingredient)
    return StockChange(stock, on_list)


async def to_list(session: AsyncSession, ctx: MemberContext, ingredient_id: uuid.UUID) -> OnList:
    """ "Add to list" for something in the Kitchen. The Kitchen itself doesn't change."""
    household_id = ctx.household.id
    row = await kitchen.staple_of(session, household_id, ingredient_id) or await kitchen.tracked_of(
        session, household_id, ingredient_id
    )
    if row is None:
        raise NotFound("That isn't in your Kitchen")
    await kitchen.lock(session, household_id)
    return await _add(session, ctx, row.ingredient)


async def _add(session: AsyncSession, ctx: MemberContext, ingredient: Ingredient) -> OnList:
    view = await shopping_lists.get_household_list(session, ctx)
    list_id = view.shopping_list.id
    if shopping_lists.unticked_match(view.items, ingredient.id, ingredient.name):
        return OnList(list_id, None)
    item = await shopping_lists.add_item(
        session,
        ctx,
        list_id,
        text=ingredient.name[:1].upper() + ingredient.name[1:],
        quantity=None,
        unit=None,
        ingredient_id=ingredient.id,
    )
    return OnList(list_id, item.id)
