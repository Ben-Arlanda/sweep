"""Used up / Ran out: gone from the Kitchen and onto the Shopping List, in one step.

Most households plan only dinners, so what breakfast and lunch use never reaches the
Kitchen as a Cooked meal. When a Member says something's gone, that's the moment to buy
it again: a Staple is marked run out (it stays a Staple), a Tracked item leaves the
Kitchen, and the item goes on the list unless it's already there unticked (ADR 0016's
rule). "Remove" (it was never there) stays separate and doesn't touch the list.

Kitchen first, then the list: the lock order every Kitchen and list change keeps.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFound
from app.services import kitchen, shopping_lists
from app.services.households import MemberContext


@dataclass(frozen=True)
class UsedUp:
    list_id: uuid.UUID
    list_item_id: uuid.UUID | None  # None: it was already on the list


async def used_up(session: AsyncSession, ctx: MemberContext, ingredient_id: uuid.UUID) -> UsedUp:
    household_id = ctx.household.id
    staple = await kitchen.staple_of(session, household_id, ingredient_id)
    tracked = None if staple else await kitchen.tracked_of(session, household_id, ingredient_id)
    if staple is None and tracked is None:
        raise NotFound("That isn't in your Kitchen")
    if staple is not None:
        await kitchen.set_staple(session, ctx, ingredient_id, have=False)
        ingredient = staple.ingredient
    else:
        assert tracked is not None
        ingredient = tracked.ingredient
        await kitchen.remove_tracked(session, ctx, ingredient_id)

    view = await shopping_lists.get_household_list(session, ctx)
    list_id = view.shopping_list.id
    if shopping_lists.unticked_match(view.items, ingredient.id, ingredient.name):
        return UsedUp(list_id, None)
    item = await shopping_lists.add_item(
        session,
        ctx,
        list_id,
        text=ingredient.name[:1].upper() + ingredient.name[1:],
        quantity=None,
        unit=None,
        ingredient_id=ingredient.id,
    )
    return UsedUp(list_id, item.id)
