"""Favourites (ADR 0025): recipes the Household has hearted, Seed or Imported. Ranking
uses them to break ties (kitchen_match); the Recipes tab shows and filters them."""

import uuid
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Favourite, PlannedMeal, utcnow
from app.services import recipes
from app.services.households import MemberContext

# A Favourite Cooked this recently loses its tie-break, so it isn't every week's answer.
COOLDOWN = timedelta(days=7)


async def heart(session: AsyncSession, ctx: MemberContext, recipe_id: uuid.UUID) -> None:
    """Idempotent: hearting a Favourite again changes nothing. 404 for a recipe this
    Household can't see."""
    await recipes.get_recipe(session, ctx.household.id, recipe_id)
    await session.execute(
        insert(Favourite)
        .values(household_id=ctx.household.id, recipe_id=recipe_id, hearted_by=ctx.member.id)
        .on_conflict_do_nothing()
    )


async def unheart(session: AsyncSession, ctx: MemberContext, recipe_id: uuid.UUID) -> None:
    """Idempotent. Keeps the recipe: un-hearting an import doesn't delete it."""
    await session.execute(
        delete(Favourite).where(
            Favourite.household_id == ctx.household.id, Favourite.recipe_id == recipe_id
        )
    )


async def ids(session: AsyncSession, household_id: uuid.UUID) -> set[uuid.UUID]:
    found = await session.execute(
        select(Favourite.recipe_id).where(Favourite.household_id == household_id)
    )
    return set(found.scalars())


async def boosted(session: AsyncSession, household_id: uuid.UUID) -> set[uuid.UUID]:
    """The Favourites that win ties in Kitchen ranking: not Cooked in the last 7 days."""
    recent = select(PlannedMeal.recipe_id).where(
        PlannedMeal.household_id == household_id,
        PlannedMeal.cooked_at >= utcnow() - COOLDOWN,
    )
    found = await session.execute(
        select(Favourite.recipe_id).where(
            Favourite.household_id == household_id, Favourite.recipe_id.not_in(recent)
        )
    )
    return set(found.scalars())
