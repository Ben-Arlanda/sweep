"""The Meal Plan: the Household's Planned Meals, one dinner per day.

There's no meal_plans table. "This week's Meal Plan" is the Planned Meals between two
dates, and the UNIQUE (household_id, date) constraint is the one-dinner-per-day rule.
"""

import uuid
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors
from app.models import Household, PlannedMeal, utcnow
from app.realtime import notify_change
from app.services import audit, kitchen
from app.services.households import MemberContext

ENTITY = "meal_plan"


async def between(
    session: AsyncSession,
    household_id: uuid.UUID,
    first: date,
    last: date,
    *,
    for_update: bool = False,
) -> list[PlannedMeal]:
    """Planned Meals from `first` to `last` (both included), by date."""
    query = (
        select(PlannedMeal)
        .where(
            PlannedMeal.household_id == household_id,
            PlannedMeal.date >= first,
            PlannedMeal.date <= last,
        )
        .order_by(PlannedMeal.date)
    )
    if for_update:
        query = query.with_for_update(of=PlannedMeal)
    return list((await session.execute(query)).scalars())


async def bump(session: AsyncSession, household_id: uuid.UUID) -> None:
    """The Meal Plan changed: bump its version and tell the Household's open apps."""
    version = await session.scalar(
        update(Household)
        .where(Household.id == household_id)
        .values(meal_plan_version=Household.meal_plan_version + 1)
        .returning(Household.meal_plan_version)
    )
    assert version is not None
    await notify_change(session, household_id, ENTITY, household_id, version)


async def _mine(session: AsyncSession, ctx: MemberContext, meal_id: uuid.UUID) -> PlannedMeal:
    """A Planned Meal in the caller's Household, locked for the change. Any other id is
    "not found", including another Household's."""
    meal = await session.scalar(
        select(PlannedMeal)
        .where(PlannedMeal.id == meal_id, PlannedMeal.household_id == ctx.household.id)
        .with_for_update(of=PlannedMeal)
    )
    if meal is None:
        raise errors.NotFound("No such Planned Meal in your Household")
    return meal


async def remove(session: AsyncSession, ctx: MemberContext, meal_id: uuid.UUID) -> None:
    """Take a meal off the plan. A Cooked one stays: undo Cooked first, so the Kitchen
    deduction isn't lost track of."""
    meal = await session.scalar(
        select(PlannedMeal)
        .where(PlannedMeal.id == meal_id, PlannedMeal.household_id == ctx.household.id)
        .with_for_update(of=PlannedMeal)
    )
    if meal is None:
        return  # already gone: "it should be gone" is true
    if meal.cooked_at is not None:
        raise errors.Conflict("This meal was Cooked. Undo Cooked before removing it.")
    await session.delete(meal)
    await bump(session, ctx.household.id)
    await audit.record(
        session, ctx.household.id, "meal.removed", "planned_meal", meal.id,
        member_id=ctx.member.id, detail={"date": meal.date.isoformat()},
    )  # fmt: skip


async def mark_cooked(session: AsyncSession, ctx: MemberContext, meal_id: uuid.UUID) -> PlannedMeal:
    """Set, never toggle: Cooked twice deducts once."""
    await kitchen.lock(session, ctx.household.id)  # Kitchen before anything else
    meal = await _mine(session, ctx, meal_id)
    if meal.cooked_at is not None:
        return meal
    meal.cooked_deductions = await kitchen.deduct_cooked(
        session, ctx.household.id, meal.recipe, meal.servings
    )
    meal.cooked_at = utcnow()
    meal.cooked_by = ctx.member.id
    await bump(session, ctx.household.id)
    await audit.record(
        session, ctx.household.id, "meal.cooked", "planned_meal", meal.id,
        member_id=ctx.member.id, detail={"deductions": meal.cooked_deductions},
    )  # fmt: skip
    return meal


async def undo_cooked(session: AsyncSession, ctx: MemberContext, meal_id: uuid.UUID) -> PlannedMeal:
    await kitchen.lock(session, ctx.household.id)
    meal = await _mine(session, ctx, meal_id)
    if meal.cooked_at is None:
        return meal
    await kitchen.restore_cooked(session, ctx.household.id, meal.cooked_deductions or [])
    meal.cooked_at = None
    meal.cooked_by = None
    meal.cooked_deductions = None
    await bump(session, ctx.household.id)
    await audit.record(
        session, ctx.household.id, "meal.uncooked", "planned_meal", meal.id,
        member_id=ctx.member.id,
    )  # fmt: skip
    return meal
