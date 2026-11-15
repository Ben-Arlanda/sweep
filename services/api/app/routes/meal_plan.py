"""HTTP routes for the Meal Plan: read a week (Mon–Sun by default), remove a meal,
Mark as Cooked and undo.

Cooked is a sub-resource (`/planned-meals/{id}/cooked`): POST sets it, DELETE undoes
it. Both are "set", never "toggle", so a repeated tap can't flip it back.
"""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Request, Response, status

from app.agent.prompt import today_in_sydney
from app.deps import MemberDep, SessionDep
from app.idempotency import IdempotencyKeyHeader
from app.models import Household, PlannedMeal
from app.routes.common import idempotent
from app.schemas import MealPlanOut, PlannedMealOut
from app.services import meal_plan

router = APIRouter(tags=["meal-plan"])
WEEK = timedelta(days=6)  # start plus six more days


def meal_out(meal: PlannedMeal) -> PlannedMealOut:
    return PlannedMealOut(
        id=meal.id,
        date=meal.date,
        recipe_id=meal.recipe_id,
        title=meal.recipe.title,
        servings=meal.servings,
        cooked_at=meal.cooked_at,
        cooked_by=meal.cooked_by,
    )


@router.get("/meal-plan")
async def get_week(ctx: MemberDep, session: SessionDep, start: date | None = None) -> MealPlanOut:
    today = today_in_sydney()
    # Mon–Sun weeks (slice 5d): with no start, this week's Monday.
    first = start or today - timedelta(days=today.weekday())
    household = await session.get_one(Household, ctx.household.id, populate_existing=True)
    meals = await meal_plan.between(session, ctx.household.id, first, first + WEEK)
    return MealPlanOut(
        start=first,
        end=first + WEEK,
        today=today,
        version=household.meal_plan_version,
        meals=[meal_out(m) for m in meals],
    )


@router.delete("/planned-meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(
    meal_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> None:
        await meal_plan.remove(session, ctx, meal_id)

    return await idempotent(request, session, ctx, key, work, status.HTTP_204_NO_CONTENT)


@router.post("/planned-meals/{meal_id}/cooked", response_model=PlannedMealOut)
async def mark_cooked(
    meal_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> PlannedMealOut:
        return meal_out(await meal_plan.mark_cooked(session, ctx, meal_id))

    return await idempotent(request, session, ctx, key, work)


@router.delete("/planned-meals/{meal_id}/cooked", response_model=PlannedMealOut)
async def undo_cooked(
    meal_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> PlannedMealOut:
        return meal_out(await meal_plan.undo_cooked(session, ctx, meal_id))

    return await idempotent(request, session, ctx, key, work)
