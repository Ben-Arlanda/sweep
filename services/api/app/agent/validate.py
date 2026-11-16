"""The validate step: deterministic checks on a Draft Plan. No LLM.

The agent can be wrong; this can't be talked out of anything. It runs when the agent
calls propose_plan. Problems go back to the agent to fix (at most 2 times). After that,
the Member sees the best attempt, with any meal that still has a problem taken out and
listed, so a Proposal never contains a recipe that breaks a Dietary Rule.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal

from app.agent.state import Draft, DraftAddition
from app.models import Recipe
from app.services.diet import DietaryRules, check_recipe
from app.services.ingredients import normalise, variants

PLAN_DAYS = 14  # a Draft Plan covers today and the next 13 days
MAX_SERVINGS = 20

ProblemKind = Literal["empty", "unknown_recipe", "rule", "servings", "date"]


@dataclass(frozen=True)
class Problem:
    kind: ProblemKind
    message: str
    date: str | None = None


def validate_draft(
    draft: Draft,
    recipes: Mapping[str, Recipe],
    rules: DietaryRules,
    today: date,
    plan_days: Sequence[date] | None = None,
) -> list[Problem]:
    """Everything wrong with the draft. `recipes`: the ones this Household can see.
    `plan_days`: the days picked in the "Plan my week" sheet, if any (ADR 0015)."""
    picked = {d.isoformat() for d in plan_days} if plan_days is not None else None
    if not draft["meals"] and not draft["list_additions"]:
        return [Problem("empty", "The plan is empty: add meals or list items first.")]

    problems: list[Problem] = []
    last_day = today + timedelta(days=PLAN_DAYS - 1)
    for day, meal in sorted(draft["meals"].items()):
        recipe = recipes.get(meal["recipe_id"])
        if recipe is None:
            # Grounding: only recipes that exist in the Recipe Knowledge Base.
            problems.append(
                Problem("unknown_recipe", f"{day}: recipe {meal['recipe_id']} doesn't exist", day)
            )
            continue
        if not today <= date.fromisoformat(day) <= last_day:
            problems.append(Problem("date", f"{day}: dates must be {today} to {last_day}", day))
        elif picked is not None and day not in picked:
            listed = ", ".join(sorted(picked))
            problems.append(
                Problem("date", f"{day}: not one of the days picked for this plan ({listed})", day)
            )
        if not 1 <= meal["servings"] <= MAX_SERVINGS:
            problems.append(
                Problem("servings", f"{day}: servings must be 1 to {MAX_SERVINGS}", day)
            )
        check = check_recipe(recipe, rules)
        if not check.ok:
            breaks = ", ".join(check.breaks)
            problems.append(Problem("rule", f"{day}: {recipe.title} breaks {breaks}", day))
    return problems


def build_proposal(
    draft: Draft,
    recipes: Mapping[str, Recipe],
    rules: DietaryRules,
    problems: list[Problem],
    summary: str,
) -> dict[str, Any]:
    """What the Member sees. Meals with a problem are left out and listed in `dropped`."""
    bad_days = {p.date for p in problems if p.date is not None}
    meals: list[dict[str, Any]] = []
    check_label: list[str] = []
    for day, meal in sorted(draft["meals"].items()):
        recipe = recipes.get(meal["recipe_id"])
        if day in bad_days or recipe is None:
            continue
        meals.append(
            {
                "date": day,
                "recipe_id": meal["recipe_id"],
                "title": recipe.title,
                "servings": meal["servings"],
            }
        )
        check_label.extend(f"{recipe.title}: {c}" for c in check_recipe(recipe, rules).check_label)
    return {
        "summary": summary,
        "meals": meals,
        "list_additions": draft["list_additions"],
        "check_label": check_label,
        "dropped": [p.message for p in problems if p.kind != "empty"],
    }


def explain_additions(
    additions: Sequence[DraftAddition],
    meals: Sequence[tuple[str, Recipe]],
    said: Sequence[str],
    ingredient_names: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Give every List Addition its reason (slice 10, CONTEXT.md "List Addition"):

    - "meal": a meal in this Proposal uses its Ingredient (`for_meals` names them)
    - "asked": the Member's own words name it
    - "unexplained": neither. Shown unticked on the card; never refused, because
      matching words is fuzzy and a wrong guess should cost a tap, not a replan.

    `meals`: (date, recipe) for the meals the Proposal keeps. `said`: only what the
    Member typed in this Conversation, never context or tool results, which may hold
    planted text. `ingredient_names`: id → name, so "asked" also matches the
    Ingredient's own name when the agent worded the addition differently."""
    words = " ".join(normalise(text) for text in said)
    explained = []
    for item in additions:
        iid = item["ingredient_id"]
        for_meals = [
            recipe.title
            for _, recipe in meals
            if iid is not None
            and any(
                line.ingredient is not None and not line.optional and str(line.ingredient.id) == iid
                for line in recipe.ingredients
            )
        ]
        names = [item["name"]]
        if iid is not None and iid in ingredient_names:
            names.append(ingredient_names[iid])
        if for_meals:
            reason = "meal"
        elif any(_said(name, words) for name in names):
            reason = "asked"
        else:
            reason = "unexplained"
        explained.append({**item, "reason": reason, "for_meals": for_meals})
    return explained


def _said(name: str, words: str) -> bool:
    """Whole words, singular or plural: "avocado" matches "two avocados", "rice" doesn't
    match "price"."""
    return any(
        re.search(rf"(?<!\w){re.escape(form)}(?!\w)", words)
        for form in variants(normalise(name))
        if form
    )
