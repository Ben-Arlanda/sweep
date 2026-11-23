"""HTTP routes for the Meal Plan: read a week (Mon–Sun by default), Dinner Ideas and
putting one on a day, remove a meal, Mark as Cooked and undo.

Cooked is a sub-resource (`/planned-meals/{id}/cooked`): POST sets it, DELETE undoes
it. Both are "set", never "toggle", so a repeated tap can't flip it back.
"""

import uuid
from datetime import date, timedelta
from typing import Annotated, cast

from fastapi import APIRouter, Query, Request, Response, status

from app import errors
from app.agent.prompt import today_in_sydney
from app.deps import MemberDep, SessionDep
from app.embeddings import Embedder
from app.idempotency import IdempotencyKeyHeader
from app.models import Household, PlannedMeal
from app.routes.common import idempotent
from app.schemas import (
    DinnerIdeaOut,
    MealPlanOut,
    PlanDayIn,
    PlannedMealIn,
    PlannedMealOut,
    RecipeSummaryOut,
    image_out,
)
from app.services import dinner_ideas, meal_plan
from app.services.dinner_ideas import MAX_IDEAS, Mood

router = APIRouter(tags=["meal-plan"])
WEEK = timedelta(days=6)  # start plus six more days


async def meals_out(
    session: SessionDep, ctx: MemberDep, meals: list[PlannedMeal]
) -> list[PlannedMealOut]:
    uses = await meal_plan.kitchen_uses(session, ctx, meals)
    return [_meal_out(m, uses[m.id]) for m in meals]


def _meal_out(meal: PlannedMeal, kitchen_uses: list[str]) -> PlannedMealOut:
    return PlannedMealOut(
        id=meal.id,
        date=meal.date,
        recipe_id=meal.recipe_id,
        title=meal.recipe.title,
        servings=meal.servings,
        total_minutes=meal.recipe.total_minutes,
        cooked_at=meal.cooked_at,
        cooked_by=meal.cooked_by,
        image=image_out(meal.recipe.image),
        kitchen_uses=kitchen_uses,
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
        meals=await meals_out(session, ctx, meals),
    )


@router.get("/dinner-ideas")
async def get_dinner_ideas(
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    max_minutes: Annotated[int | None, Query(gt=0, le=1440)] = None,
    nothing_to_buy: bool = False,
    exclude: Annotated[list[uuid.UUID], Query(max_length=60)] = [],  # noqa: B006
    limit: Annotated[int, Query(gt=0, le=MAX_IDEAS)] = 3,
    mood: Mood = Mood.KITCHEN,
    q: Annotated[str, Query(max_length=200)] = "",
    vegetarian: bool = False,
) -> list[DinnerIdeaOut]:
    """Tonight's best Kitchen Matches, chosen by code (ADR 0025). No AI, no limits."""
    if mood == Mood.SPECIFIC and not q.strip():
        raise errors.InvalidInput("Say what you're in the mood for")
    found = await dinner_ideas.for_mood(
        session,
        ctx,
        cast(Embedder | None, request.app.state.embedder),
        mood,
        today=today_in_sydney(),
        q=q.strip(),
        max_minutes=max_minutes,
        nothing_to_buy=nothing_to_buy,
        vegetarian=vegetarian,
        exclude=exclude,
        limit=limit,
    )
    return ideas_out(found)


def ideas_out(found: list[dinner_ideas.Idea]) -> list[DinnerIdeaOut]:
    return [
        DinnerIdeaOut(
            **RecipeSummaryOut.model_validate(i.recipe).model_dump(exclude={"favourite"}),
            favourite=i.favourite,
            have=list(i.match.have),
            maybe=list(i.match.maybe),
            missing=list(i.match.missing),
            kitchen_uses=i.kitchen_uses,
        )
        for i in found
    ]


@router.put("/meal-plan/days/{day}", response_model=PlannedMealOut)
async def plan_day(
    day: date,
    body: PlanDayIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    """A Member picks a recipe for a day (a Dinner Idea): planned directly, no Proposal."""

    async def work() -> PlannedMealOut:
        meal = await meal_plan.plan_day(
            session, ctx, day, body.recipe_id, today_in_sydney(), servings=body.servings
        )
        [out] = await meals_out(session, ctx, [meal])
        return out

    return await idempotent(request, session, ctx, key, work)


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


@router.patch("/planned-meals/{meal_id}", response_model=PlannedMealOut)
async def change(
    meal_id: uuid.UUID,
    body: PlannedMealIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> PlannedMealOut:
        meal = await meal_plan.set_servings(session, ctx, meal_id, body.servings)
        [out] = await meals_out(session, ctx, [meal])
        return out

    return await idempotent(request, session, ctx, key, work)


@router.post("/planned-meals/{meal_id}/cooked", response_model=PlannedMealOut)
async def mark_cooked(
    meal_id: uuid.UUID,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> PlannedMealOut:
        [out] = await meals_out(session, ctx, [await meal_plan.mark_cooked(session, ctx, meal_id)])
        return out

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
        [out] = await meals_out(session, ctx, [await meal_plan.undo_cooked(session, ctx, meal_id)])
        return out

    return await idempotent(request, session, ctx, key, work)
