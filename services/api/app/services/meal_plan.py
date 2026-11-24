"""The Meal Plan: the Household's Planned Meals, one dinner per day.

There's no meal_plans table. "This week's Meal Plan" is the Planned Meals between two
dates, and the UNIQUE (household_id, date) constraint is the one-dinner-per-day rule.
"""

import uuid
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors
from app.models import Household, Ingredient, PlannedMeal, utcnow
from app.realtime import notify_change
from app.services import audit, diet, kitchen, kitchen_match, recipes
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


async def kitchen_uses(
    session: AsyncSession, ctx: MemberContext, meals: list[PlannedMeal]
) -> dict[uuid.UUID, list[str]]:
    """What each meal uses from the Kitchen, by meal id (Home's "uses your …", 6c).

    Not cooked yet: worked out from the Kitchen now (`kitchen_match.uses`). Cooked:
    what Mark as Cooked actually took out. The Kitchen has changed by then (a used-up
    item is gone), so working it out again would leave things out."""
    out: dict[uuid.UUID, list[str]] = {}
    planned = [m for m in meals if m.cooked_at is None]
    if planned:
        snap = await kitchen_match.snapshot(session, ctx)
        for meal in planned:
            out[meal.id] = kitchen_match.uses(kitchen_match.lines_of(meal.recipe), snap)
    cooked = [m for m in meals if m.cooked_at is not None]
    ids = {uuid.UUID(c["ingredient_id"]) for m in cooked for c in m.cooked_deductions or []}
    names: dict[uuid.UUID, str] = {}
    if ids:
        found = await session.execute(
            select(Ingredient.id, Ingredient.name).where(Ingredient.id.in_(ids))
        )
        names = {i: name for i, name in found}
    for meal in cooked:
        taken = (uuid.UUID(c["ingredient_id"]) for c in meal.cooked_deductions or [])
        out[meal.id] = [names[i] for i in taken if i in names]
    return out


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


async def set_servings(
    session: AsyncSession, ctx: MemberContext, meal_id: uuid.UUID, servings: int
) -> PlannedMeal:
    """A Cooked meal keeps its servings: they match what Cooked took from the Kitchen."""
    meal = await _mine(session, ctx, meal_id)
    if meal.servings == servings:
        return meal
    if meal.cooked_at is not None:
        raise errors.Conflict("This meal was Cooked. Undo Cooked before changing its servings.")
    meal.servings = servings
    await bump(session, ctx.household.id)
    await audit.record(
        session, ctx.household.id, "meal.servings", "planned_meal", meal.id,
        member_id=ctx.member.id, detail={"servings": servings},
    )  # fmt: skip
    return meal


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


async def plan_day(
    session: AsyncSession,
    ctx: MemberContext,
    day: date,
    recipe_id: uuid.UUID,
    today: date,
    servings: int | None = None,
) -> PlannedMeal:
    """A Member puts a recipe on a day themselves (Dinner Ideas, ADR 0025): no Proposal,
    like editing the plan by hand. The same checks as approving one: the day hasn't
    passed, the recipe passes the Dietary Rules, and a Cooked day isn't replaced."""
    hid = ctx.household.id
    if day < today:
        raise errors.InvalidInput("That day has passed")
    recipe = await recipes.get_recipe(session, hid, recipe_id)
    check = diet.check_recipe(recipe, await diet.get_rules(session, hid))
    if not check.ok:
        raise errors.Conflict(
            f"{recipe.title} breaks your Dietary Rules: {', '.join(check.breaks)}"
        )
    found = await between(session, hid, day, day, for_update=True)
    current = found[0] if found else None
    if current is not None and current.cooked_at is not None:
        raise errors.Conflict(f"{current.recipe.title} was already cooked that day")
    servings = (
        servings or (await diet.get_preferences(session, hid)).household_size or recipe.servings
    )
    if current is None:
        current = PlannedMeal(household_id=hid, date=day, recipe_id=recipe.id, servings=servings)
        session.add(current)
    else:
        current.recipe_id = recipe.id
        current.servings = servings
        current.proposal_id = None
    await session.flush()
    await session.refresh(current, ["recipe"])
    await bump(session, hid)
    await audit.record(
        session, hid, "meal.planned", "planned_meal", current.id,
        member_id=ctx.member.id, detail={"date": day.isoformat(), "recipe_id": str(recipe.id)},
    )  # fmt: skip
    return current
