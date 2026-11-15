"""The Meal Plan: the Household's Planned Meals, one dinner per day.

There's no meal_plans table. "This week's Meal Plan" is the Planned Meals between two
dates, and the UNIQUE (household_id, date) constraint is the one-dinner-per-day rule.
"""

import uuid
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Household, PlannedMeal
from app.realtime import notify_change

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
