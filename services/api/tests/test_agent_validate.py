"""The validate step: plain code that checks a Draft Plan before anyone sees it."""

import uuid
from datetime import date

from app.agent.state import Draft
from app.agent.validate import build_proposal, validate_draft
from app.data.diet import Diet
from app.models import Ingredient, Recipe, RecipeIngredient
from app.services.diet import DietaryRules

TODAY = date(2026, 11, 16)  # a Monday


def recipe(title: str, *ingredients: str) -> Recipe:
    return Recipe(
        id=uuid.uuid4(),
        title=title,
        servings=4,
        ingredients=[
            RecipeIngredient(
                position=n,
                raw_text=name,
                ingredient=Ingredient(id=uuid.uuid4(), name=name),
                needs_review=False,
                optional=False,
            )
            for n, name in enumerate(ingredients)
        ],
    )


CURRY = recipe("Chicken curry", "chicken thigh", "onion")
DAL = recipe("Dal", "red lentils", "onion", "stock cubes")
RECIPES = {str(r.id): r for r in (CURRY, DAL)}
VEGETARIAN = DietaryRules(frozenset({Diet.VEGETARIAN}))


def draft(**meals: tuple[Recipe | str, int]) -> Draft:
    """draft(mon=(DAL, 2)): meals keyed by weekday offset name, for readability."""
    offsets = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "far": 30, "past": -1}
    return Draft(
        meals={
            date.fromordinal(TODAY.toordinal() + offsets[day]).isoformat(): {
                "recipe_id": r if isinstance(r, str) else str(r.id),
                "servings": servings,
            }
            for day, (r, servings) in meals.items()
        },
        list_additions=[],
    )


NO_RULES = DietaryRules()


def kinds(d: Draft, rules: DietaryRules = NO_RULES) -> list[str]:
    return [p.kind for p in validate_draft(d, RECIPES, rules, TODAY)]


def test_a_good_plan_has_no_problems() -> None:
    assert kinds(draft(mon=(DAL, 2), tue=(CURRY, 4))) == []


def test_an_empty_plan_is_a_problem() -> None:
    assert kinds(draft()) == ["empty"]


def test_a_recipe_that_isnt_in_the_knowledge_base_fails_grounding() -> None:
    assert kinds(draft(mon=(str(uuid.uuid4()), 2))) == ["unknown_recipe"]


def test_a_meal_that_breaks_a_dietary_rule_is_caught() -> None:
    problems = validate_draft(draft(mon=(CURRY, 2)), RECIPES, VEGETARIAN, TODAY)
    assert [p.kind for p in problems] == ["rule"]
    assert "chicken thigh (vegetarian)" in problems[0].message


def test_servings_and_dates_must_be_sensible() -> None:
    assert kinds(draft(mon=(DAL, 0))) == ["servings"]
    assert kinds(draft(far=(DAL, 2))) == ["date"]
    assert kinds(draft(past=(DAL, 2))) == ["date"]


def test_the_proposal_drops_meals_that_still_have_problems() -> None:
    # After the replans run out: show the best attempt, never a meal that breaks a Rule.
    d = draft(mon=(DAL, 2), tue=(CURRY, 2))
    problems = validate_draft(d, RECIPES, VEGETARIAN, TODAY)
    proposal = build_proposal(d, RECIPES, VEGETARIAN, problems, "Two dinners")

    assert [m["title"] for m in proposal["meals"]] == ["Dal"]
    assert proposal["dropped"] == [problems[0].message]
    # Brand-dependent ingredients are surfaced, not hidden.
    assert proposal["check_label"] == ["Dal: stock cubes (vegetarian)"]
    assert build_proposal(d, RECIPES, DietaryRules(), [], "x")["check_label"] == []
