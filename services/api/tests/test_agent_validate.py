"""The validate step: plain code that checks a Draft Plan before anyone sees it."""

import uuid
from datetime import date

from app.agent.state import Draft, DraftAddition
from app.agent.validate import build_proposal, explain_additions, validate_draft
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


# --- List Addition reasons (slice 10) ----------------------------------------------------


def addition(name: str, ingredient: Ingredient | None = None) -> DraftAddition:
    return DraftAddition(
        name=name,
        quantity=None,
        unit=None,
        ingredient_id=str(ingredient.id) if ingredient else None,
    )


def ingredient_of(r: Recipe, name: str) -> Ingredient:
    found = next(
        line.ingredient
        for line in r.ingredients
        if line.ingredient is not None and line.ingredient.name == name
    )
    assert found is not None
    return found


def reasons(
    *additions: DraftAddition, said: tuple[str, ...] = ("plan two dinners",)
) -> list[tuple[str, list[str]]]:
    meals = [("2026-11-16", CURRY), ("2026-11-17", DAL)]
    names = {
        str(line.ingredient.id): line.ingredient.name
        for _, r in meals
        for line in r.ingredients
        if line.ingredient
    }
    explained = explain_additions(list(additions), meals, list(said), names)
    return [(a["reason"], a["for_meals"]) for a in explained]


def test_an_addition_a_planned_meal_uses_is_for_that_meal() -> None:
    onion = ingredient_of(CURRY, "onion")
    lentils = ingredient_of(DAL, "red lentils")

    got = reasons(addition("brown onion", onion), addition("lentils", lentils))

    # Matched by the Ingredient, not the words: the agent wrote "brown onion".
    assert got == [("meal", ["Chicken curry"]), ("meal", ["Dal"])]


def test_an_ingredient_used_by_two_meals_names_both() -> None:
    # CURRY and DAL are different Recipe objects with their own "onion" Ingredient; the
    # app shares one Ingredient row, so give DAL's onion the same id here.
    onion = ingredient_of(CURRY, "onion")
    ingredient_of(DAL, "onion").id = onion.id

    assert reasons(addition("onion", onion)) == [("meal", ["Chicken curry", "Dal"])]


def test_an_addition_the_member_asked_for_is_explained() -> None:
    said = ("plan two dinners", "Also add MILK and a couple of avocados please")

    got = reasons(addition("milk"), addition("avocado"), addition("Bananas"), said=said)

    assert got == [("asked", []), ("asked", []), ("unexplained", [])]


def test_asked_for_means_whole_words() -> None:
    """ "rice" is not asked for by "price" or "licorice"."""
    said = ("keep the price down, and the kids like licorice",)

    assert reasons(addition("rice"), said=said) == [("unexplained", [])]


def test_an_injected_addition_is_unexplained() -> None:
    """Planted text asked for wine. The Member didn't, and no meal uses it."""
    assert reasons(addition("wine")) == [("unexplained", [])]


# --- Recipe Adaptations (slice 5e, ADR 0021) -------------------------------------------


def adapted_curry_draft() -> Draft:
    d = draft(mon=(CURRY, 2))
    [meal] = d["meals"].values()
    meal["adaptation"] = {"label": "with tofu", "swaps": [{"position": 0, "raw_text": "tofu"}]}
    return d


def test_an_adapted_meal_is_checked_as_adapted_not_as_its_parent() -> None:
    d = adapted_curry_draft()
    [day] = d["meals"]
    tofu_curry = recipe("Chicken curry · with tofu", "tofu", "onion")
    tofu_curry.ingredients[0].replaces = "chicken thigh"
    problems = validate_draft(d, RECIPES, VEGETARIAN, TODAY, adapted={day: tofu_curry})
    assert problems == []
    [meal] = build_proposal(d, RECIPES, VEGETARIAN, [], "x", {day: tofu_curry})["meals"]
    assert (meal["title"], meal["recipe_id"]) == ("Chicken curry · with tofu", str(CURRY.id))
    assert meal["adaptation"]["swaps"] == [
        {"position": 0, "replaces": "chicken thigh", "raw_text": "tofu"}
    ]


def test_an_adapted_meal_never_falls_back_to_its_parent_as_written() -> None:
    """With no adapted recipe for the day (it couldn't be built), it isn't the parent."""
    assert [p.kind for p in validate_draft(adapted_curry_draft(), RECIPES, NO_RULES, TODAY)] == [
        "unknown_recipe"
    ]


def test_refused_swaps_are_a_problem_for_that_day() -> None:
    d = adapted_curry_draft()
    [day] = d["meals"]
    problems = validate_draft(d, RECIPES, NO_RULES, TODAY, refused={day: '"x" adds meat'})
    assert [(p.kind, p.message) for p in problems] == [
        ("swap", f'{day}: Swaps refused: "x" adds meat')
    ]
