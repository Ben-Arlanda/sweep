"""The agent's tools: read, compute and draft (plan §7). Nothing here writes Household data.

Every tool:
- checks its arguments with a Pydantic model (the LLM's JSON is untrusted input)
- gets the Household and Member from the run's context, never from the LLM, so a
  prompt can't point a tool at another Household
- reuses the same services the HTTP routes use, so the rules are in one place
- returns plain JSON; errors go back to the agent as data it can react to

Draft tools only change the Draft Plan in the agent's state. Saving it is slice 6, and
only after the Member approves (ADR 0005).
"""

import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import errors
from app.agent.model import AgentModel
from app.agent.state import Draft, DraftAddition, DraftMeal
from app.embeddings import Embedder, EmbeddingUnavailable
from app.models import Household, Member, Recipe, utcnow
from app.services import diet, ingredients, kitchen, recipes, shopping_lists
from app.services.households import MemberContext

SEARCH_RESULTS = 8


@dataclass(frozen=True)
class AgentContext:
    """Per-run wiring. Not saved in checkpoints: it's rebuilt for every request."""

    sessionmaker: async_sessionmaker[AsyncSession]
    household_id: uuid.UUID
    member_id: uuid.UUID
    model: AgentModel
    embedder: Embedder | None
    today: date
    daily_token_budget: int


@dataclass(frozen=True)
class Call:
    """What a tool gets: a fresh session, the verified caller, and the current draft."""

    session: AsyncSession
    member: MemberContext
    agent: AgentContext
    draft: Draft


@dataclass(frozen=True)
class Outcome:
    result: Any
    draft: Draft | None = None  # set when the tool changed the draft


class ToolError(Exception):
    """A problem the agent should hear about and can fix (bad id, unknown date...)."""


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid")  # an unexpected field is an error, not ignored


# --- read ------------------------------------------------------------------------------


class SearchArgs(Args):
    query: str = Field(min_length=1, max_length=200, description="What to look for")
    max_minutes: int | None = Field(default=None, gt=0, le=1440)
    cuisine: str | None = Field(default=None, max_length=40, description="e.g. italian")
    must_use_ingredients: list[str] = Field(
        default=[], max_length=5, description="Ingredient names every result must use"
    )


def _summary(recipe: Recipe, rules: diet.DietaryRules) -> dict[str, Any]:
    check = diet.check_recipe(recipe, rules)
    return {
        "recipe_id": str(recipe.id),
        "title": recipe.title,
        "cuisine": recipe.cuisine,
        "minutes": recipe.total_minutes,
        "servings": recipe.servings,
        "summary": recipe.summary,
        "check_label": check.check_label,
    }


async def search_recipes(call: Call, args: SearchArgs) -> Outcome:
    """Dietary Rules are applied in SQL by filters_for: the agent never sees a recipe
    that breaks one, so it can't pick one."""
    if call.agent.embedder is None:
        raise ToolError("Recipe search isn't available right now")
    hid = call.agent.household_id
    must: list[uuid.UUID] = []
    for name in args.must_use_ingredients:
        found = await ingredients.resolve(call.session, hid, name, create=False)
        if found is None:
            raise ToolError(f"Unknown ingredient: {name!r}")
        must.append(found.id)
    filters = await recipes.filters_for(call.session, hid, args.max_minutes, args.cuisine)
    try:
        # Fetch extra when filtering afterwards, so we still have enough to return.
        limit = SEARCH_RESULTS * (4 if must else 1)
        found_recipes = await recipes.search(
            call.session, hid, call.agent.embedder, args.query, filters, limit
        )
    except EmbeddingUnavailable as error:
        raise ToolError("Recipe search is unavailable right now") from error
    rules = await diet.get_rules(call.session, hid)
    matches = [
        r
        for r, _score in found_recipes
        if set(must) <= {line.ingredient_id for line in r.ingredients}
    ]
    return Outcome([_summary(r, rules) for r in matches[:SEARCH_RESULTS]])


class RecipeArgs(Args):
    recipe_id: uuid.UUID


async def get_recipe(call: Call, args: RecipeArgs) -> Outcome:
    try:
        recipe = await recipes.get_recipe(call.session, call.agent.household_id, args.recipe_id)
    except errors.NotFound as error:
        raise ToolError(f"No recipe with id {args.recipe_id}") from error
    rules = await diet.get_rules(call.session, call.agent.household_id)
    return Outcome(
        {
            **_summary(recipe, rules),
            "ingredients": [line.raw_text for line in recipe.ingredients],
            "method": recipe.method or [],
        }
    )


class NoArgs(Args):
    pass


async def get_kitchen(call: Call, _args: NoArgs) -> Outcome:
    view = await kitchen.get_kitchen(call.session, call.member)
    now = utcnow()
    return Outcome(
        {
            "tracked": [
                {
                    "ingredient": item.ingredient.name,
                    "quantity": float(item.quantity) if item.quantity is not None else None,
                    "unit": item.ingredient.default_unit,
                    "status": kitchen.status_of(item, now).value,
                }
                for item in view.tracked
            ],
            "staples_run_out": [s.ingredient.name for s in view.staples if s.ran_out_at],
            "note": "Other staples (salt, oil, common spices...) are assumed to be at home.",
        }
    )


async def get_household_preferences(call: Call, _args: NoArgs) -> Outcome:
    hid = call.agent.household_id
    rules = await diet.get_rules(call.session, hid)
    excluded = await diet.excluded_ingredients(call.session, hid, rules)
    prefs = await diet.get_preferences(call.session, hid)
    return Outcome(
        {
            "dietary_rules": {
                "diets": sorted(rules.diets),
                "never_use": [i.name for i in excluded],
                "note": "Enforced by the app. Search already leaves out recipes that break them.",
            },
            "preferences": {
                "household_size": prefs.household_size,
                "cuisines": prefs.cuisines,
            },
        }
    )


async def get_shopping_list(call: Call, _args: NoArgs) -> Outcome:
    view = await shopping_lists.get_household_list(call.session, call.member)
    shop_names = {s.id: s.name for s in view.shops}
    return Outcome(
        {
            "to_buy": [
                {"item": i.text, "shop": shop_names.get(i.shop_id) if i.shop_id else None}
                for i in view.items
                if i.checked_at is None
            ]
        }
    )


# --- compute ---------------------------------------------------------------------------


class MealRef(Args):
    recipe_id: uuid.UUID
    servings: int = Field(gt=0, le=20)


class CoverageArgs(Args):
    meals: list[MealRef] = Field(min_length=1, max_length=14)


async def check_kitchen_coverage(call: Call, args: CoverageArgs) -> Outcome:
    """What these meals need that the Kitchen doesn't have. Deterministic: plain sums."""
    need: dict[str, Decimal] = defaultdict(Decimal)
    units: dict[str, str] = {}
    unmeasured: set[str] = set()  # "salt to taste": needed, amount unknown
    for meal in args.meals:
        try:
            recipe = await recipes.get_recipe(call.session, call.agent.household_id, meal.recipe_id)
        except errors.NotFound as error:
            raise ToolError(f"No recipe with id {meal.recipe_id}") from error
        scale = Decimal(meal.servings) / Decimal(recipe.servings)
        for line in recipe.ingredients:
            if line.ingredient is None or line.optional:
                continue
            name = line.ingredient.name
            units[name] = line.ingredient.default_unit
            if line.base_quantity is None:
                unmeasured.add(name)
            else:
                need[name] += line.base_quantity * scale

    view = await kitchen.get_kitchen(call.session, call.member)
    now = utcnow()
    tracked = {item.ingredient.name: item for item in view.tracked}
    staples = {s.ingredient.name: s for s in view.staples}
    missing: list[dict[str, Any]] = []
    uncertain: list[dict[str, Any]] = []
    covered: list[str] = []
    for name in sorted(set(need) | unmeasured):
        staple = staples.get(name)
        item = tracked.get(name)
        if staple is not None:  # assumed at home unless marked run out; no quantities
            if staple.ran_out_at:
                missing.append({"ingredient": name, "note": "staple, run out"})
            else:
                covered.append(name)
        elif item is None:
            amount = need.get(name)
            missing.append(
                {
                    "ingredient": name,
                    "need": round(float(amount), 1) if amount else None,
                    "unit": units[name],
                }
            )
        else:
            status = kitchen.status_of(item, now).value
            have = item.quantity
            short = need[name] - have if name in need and have is not None else None
            if have is None or status != "confirmed":
                uncertain.append(
                    {
                        "ingredient": name,
                        "have": float(have) if have is not None else None,
                        "status": status,
                    }
                )
            if short is not None and short > 0:
                missing.append(
                    {"ingredient": name, "need": round(float(short), 1), "unit": units[name]}
                )
            elif have is not None and status == "confirmed":
                covered.append(name)
    return Outcome(
        {
            "missing": missing,
            "uncertain": uncertain,
            "covered": covered,
            "note": "Quantities are in each Ingredient's own unit (g, ml or count). "
            "Ask the Member about 'uncertain' items rather than assuming.",
        }
    )


# --- draft ------------------------------------------------------------------------------


class SetMealArgs(Args):
    date: date
    recipe_id: uuid.UUID
    servings: int = Field(gt=0, le=20)


async def set_planned_meal(call: Call, args: SetMealArgs) -> Outcome:
    """Checked straight away, so the agent hears about a broken Rule now, not at the end.
    validate checks everything again anyway."""
    try:
        recipe = await recipes.get_recipe(call.session, call.agent.household_id, args.recipe_id)
    except errors.NotFound as error:
        raise ToolError(f"No recipe with id {args.recipe_id}: use one from search") from error
    check = diet.check_recipe(recipe, await diet.get_rules(call.session, call.agent.household_id))
    if not check.ok:
        raise ToolError(f"{recipe.title} breaks the Dietary Rules: {', '.join(check.breaks)}")
    meals = {
        **call.draft["meals"],
        args.date.isoformat(): DraftMeal(
            recipe_id=str(recipe.id), servings=args.servings, title=recipe.title
        ),
    }
    return Outcome(
        {"ok": True, "date": args.date.isoformat(), "title": recipe.title},
        Draft(meals=meals, list_additions=call.draft["list_additions"]),
    )


class RemoveMealArgs(Args):
    date: date


async def remove_planned_meal(call: Call, args: RemoveMealArgs) -> Outcome:
    meals = dict(call.draft["meals"])
    if meals.pop(args.date.isoformat(), None) is None:
        raise ToolError(f"No meal planned on {args.date}")
    return Outcome({"ok": True}, Draft(meals=meals, list_additions=call.draft["list_additions"]))


class Addition(Args):
    name: str = Field(min_length=1, max_length=200)
    quantity: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=20)


class AdditionsArgs(Args):
    items: list[Addition] = Field(max_length=60, description="The whole list; replaces it")


async def set_list_additions(call: Call, args: AdditionsArgs) -> Outcome:
    additions: list[DraftAddition] = []
    for item in args.items:
        found = await ingredients.resolve(
            call.session, call.agent.household_id, item.name, create=False
        )
        additions.append(
            DraftAddition(
                name=item.name,
                quantity=item.quantity,
                unit=item.unit,
                ingredient_id=str(found.id) if found else None,
            )
        )
    return Outcome(
        {"ok": True, "count": len(additions)},
        Draft(meals=call.draft["meals"], list_additions=additions),
    )


# --- finish -----------------------------------------------------------------------------


class ProposeArgs(Args):
    summary: str = Field(
        min_length=1, max_length=1000, description="A short note to the Member about the plan"
    )


PROPOSE_PLAN = "propose_plan"


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args: type[Args]
    run: Callable[[Call, Any], Awaitable[Outcome]] | None  # None: handled by the graph


TOOLS: tuple[Tool, ...] = (
    Tool(
        "search_recipes",
        "Find recipes by meaning (e.g. 'quick vegetarian pasta'). Only returns recipes "
        "that fit the Household's Dietary Rules.",
        SearchArgs,
        search_recipes,
    ),
    Tool("get_recipe", "Full ingredients and method for one recipe.", RecipeArgs, get_recipe),
    Tool(
        "get_kitchen",
        "What the Household has at home, with how sure we are (confirmed, estimated, unknown).",
        NoArgs,
        get_kitchen,
    ),
    Tool(
        "get_household_preferences",
        "The Household's Dietary Rules (hard) and Preferences (soft).",
        NoArgs,
        get_household_preferences,
    ),
    Tool("get_shopping_list", "Items already on the Shopping Lists.", NoArgs, get_shopping_list),
    Tool(
        "check_kitchen_coverage",
        "For a set of meals, which Ingredients are missing from the Kitchen and how much "
        "to buy. Use this to build list additions; don't guess quantities.",
        CoverageArgs,
        check_kitchen_coverage,
    ),
    Tool(
        "set_planned_meal",
        "Put a recipe on a date in the Draft Plan (replaces that date's meal).",
        SetMealArgs,
        set_planned_meal,
    ),
    Tool(
        "remove_planned_meal",
        "Take the meal off a date in the Draft Plan.",
        RemoveMealArgs,
        remove_planned_meal,
    ),
    Tool(
        "set_list_additions",
        "Set the Shopping List additions in the Draft Plan (the whole list).",
        AdditionsArgs,
        set_list_additions,
    ),
    Tool(
        PROPOSE_PLAN,
        "Show the Draft Plan to the Member for approval. Call it when the plan is ready. "
        "The app checks it first and tells you if anything needs fixing.",
        ProposeArgs,
        None,
    ),
)
BY_NAME = {t.name: t for t in TOOLS}


def specs() -> list[dict[str, Any]]:
    """Tool definitions for the model: name, description, JSON schema of the arguments.
    Sorted by name: a stable order keeps the prompt cache valid."""
    return [
        {"name": t.name, "description": t.description, "input_schema": t.args.model_json_schema()}
        for t in sorted(TOOLS, key=lambda t: t.name)
    ]


async def member_context(session: AsyncSession, agent: AgentContext) -> MemberContext:
    member = await session.get_one(Member, agent.member_id)
    household = await session.get_one(Household, agent.household_id)
    return MemberContext(member=member, household=household)
