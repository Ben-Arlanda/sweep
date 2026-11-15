"""HTTP routes for the Household's Dietary Rules (hard) and Preferences (soft).

Any Member can change them, not just the Owner: the Member with the allergy is usually
the one who knows about it.
"""

import uuid

from fastapi import APIRouter, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import MemberDep, SessionDep
from app.idempotency import IdempotencyKeyHeader
from app.routes.common import idempotent
from app.schemas import (
    DietaryRulesIn,
    DietaryRulesOut,
    IngredientOut,
    PlanWeekdaysIn,
    PlanWeekdaysOut,
    PreferencesIn,
    PreferencesOut,
)
from app.services import diet
from app.services.diet import DietaryRules

router = APIRouter(prefix="/households/current", tags=["dietary rules"])


async def rules_out(
    session: AsyncSession, household_id: uuid.UUID, rules: DietaryRules
) -> DietaryRulesOut:
    excluded = await diet.excluded_ingredients(session, household_id, rules)
    return DietaryRulesOut(
        diets=sorted(rules.diets),
        excluded_ingredients=[IngredientOut.model_validate(i) for i in excluded],
    )


@router.get("/dietary-rules")
async def get_rules(ctx: MemberDep, session: SessionDep) -> DietaryRulesOut:
    return await rules_out(
        session, ctx.household.id, await diet.get_rules(session, ctx.household.id)
    )


@router.put("/dietary-rules", response_model=DietaryRulesOut)
async def set_rules(
    body: DietaryRulesIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> DietaryRulesOut:
        rules = DietaryRules(frozenset(body.diets), frozenset(body.excluded_ingredient_ids))
        return await rules_out(
            session, ctx.household.id, await diet.set_rules(session, ctx.household.id, rules)
        )

    return await idempotent(request, session, ctx, key, work)


@router.get("/preferences")
async def get_preferences(ctx: MemberDep, session: SessionDep) -> PreferencesOut:
    return PreferencesOut.model_validate(await diet.get_preferences(session, ctx.household.id))


@router.put("/preferences", response_model=PreferencesOut)
async def set_preferences(
    body: PreferencesIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    async def work() -> PreferencesOut:
        row = await diet.set_preferences(session, ctx.household.id, **body.model_dump())
        return PreferencesOut.model_validate(row)

    return await idempotent(request, session, ctx, key, work)


@router.put("/plan-weekdays", response_model=PlanWeekdaysOut)
async def set_plan_weekdays(
    body: PlanWeekdaysIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
    key: IdempotencyKeyHeader,
) -> Response:
    """The days the "Plan my week" sheet starts with ticked (ADR 0015)."""

    async def work() -> PlanWeekdaysOut:
        days = await diet.set_plan_weekdays(session, ctx.household.id, body.weekdays)
        return PlanWeekdaysOut(weekdays=days)

    return await idempotent(request, session, ctx, key, work)
