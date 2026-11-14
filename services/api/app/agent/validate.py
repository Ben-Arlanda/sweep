"""The validate step: deterministic checks on a Draft Plan. No LLM.

The agent can be wrong; this can't be talked out of anything. It runs when the agent
calls propose_plan. Problems go back to the agent to fix (at most 2 times). After that,
the Member sees the best attempt, with any meal that still has a problem taken out and
listed, so a Proposal never contains a recipe that breaks a Dietary Rule.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal

from app.agent.state import Draft
from app.models import Recipe
from app.services.diet import DietaryRules, check_recipe

PLAN_DAYS = 14  # a Draft Plan covers today and the next 13 days
MAX_SERVINGS = 20

ProblemKind = Literal["empty", "unknown_recipe", "rule", "servings", "date"]


@dataclass(frozen=True)
class Problem:
    kind: ProblemKind
    message: str
    date: str | None = None


def validate_draft(
    draft: Draft, recipes: Mapping[str, Recipe], rules: DietaryRules, today: date
) -> list[Problem]:
    """Everything wrong with the draft. `recipes`: the ones this Household can see."""
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
