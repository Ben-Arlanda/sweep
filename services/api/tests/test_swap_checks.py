"""The Swap checks (slice 5e step 2, ADR 0021). Pure: no database, no model.

The model writes each replacement line; these checks decide whether it's allowed.
"""

import uuid

from app.data.diet import Diet
from app.models import Ingredient, ParseMethod, RecipeIngredient
from app.services.diet import DietaryRules
from app.services.swap_checks import check

HOUSEHOLD = uuid.uuid4()


def ingredient(name: str, household: bool = False) -> Ingredient:
    return Ingredient(
        id=uuid.uuid4(),
        name=name,
        household_id=HOUSEHOLD if household else None,
        category="pantry",
        default_unit="g",
    )


def line(raw_text: str, found: Ingredient | None, needs_review: bool = False) -> RecipeIngredient:
    return RecipeIngredient(
        raw_text=raw_text,
        ingredient=found,
        ingredient_id=found.id if found else None,
        parse_method=ParseMethod.RULE,
        needs_review=needs_review,
        optional=False,
    )


BEEF = line("500 g beef mince", ingredient("beef mince"))
ONION = line("1 onion, diced", ingredient("brown onion"))
LENTILS = line("2 x 400g cans lentils", ingredient("brown lentils"))
NONE = DietaryRules()
VEGETARIAN = DietaryRules(diets=frozenset({Diet.VEGETARIAN}))


def test_a_meat_free_swap_that_fixes_the_rule_passes() -> None:
    assert check([(BEEF, LENTILS)], [LENTILS, ONION], VEGETARIAN) == []


def test_a_replacement_must_link_to_a_known_ingredient() -> None:
    mystery = line("1 jar zorblax relish", None, needs_review=True)
    assert check([(BEEF, mystery)], [mystery, ONION], NONE) == [
        '"1 jar zorblax relish" isn\'t an Ingredient Sweep knows'
    ]


def test_a_household_ingredient_cant_be_checked_so_it_cant_be_a_replacement() -> None:
    """Fail closed: Sweep doesn't know what a Member's "satay sauce" contains, so it
    can't tell whether it brings in meat, even with no Rules set."""
    satay = line("3 tbsp satay sauce", ingredient("satay sauce", household=True))
    assert check([(BEEF, satay)], [satay, ONION], NONE) == [
        '"3 tbsp satay sauce" uses satay sauce, which Sweep can\'t check'
    ]


def test_a_swap_must_change_the_ingredient() -> None:
    """ "For two" is a Planned Meal's servings, not an Adaptation (ADR 0021)."""
    less = line("250 g beef mince", ingredient("beef mince"))
    assert check([(BEEF, less)], [less, ONION], NONE) == [
        '"250 g beef mince" is still beef mince: a Swap must change the ingredient'
    ]


def test_no_new_meat_seafood_or_egg_the_method_wasnt_written_for() -> None:
    tofu = line("400 g firm tofu", ingredient("tofu"))
    chicken = line("500 g chicken thigh", ingredient("chicken thigh"))
    prawns = line("300 g prawns", ingredient("prawns"))
    eggs = line("4 eggs", ingredient("eggs"))
    assert check([(tofu, chicken)], [chicken], NONE) == [
        '"500 g chicken thigh" adds meat, which the method wasn\'t written for'
    ]
    # Meat for seafood is still something new: different cooking times.
    assert check([(BEEF, prawns)], [prawns], NONE) == [
        '"300 g prawns" adds seafood, which the method wasn\'t written for'
    ]
    assert check([(ONION, eggs)], [BEEF, eggs], NONE) == [
        '"4 eggs" adds egg, which the method wasn\'t written for'
    ]
    # An unlinked line could have been anything: it can't vouch for meat either.
    mystery = line("1 packet mystery mix", None, needs_review=True)
    assert check([(mystery, chicken)], [chicken], NONE) != []


def test_meat_for_meat_is_fine() -> None:
    breast = line("500 g chicken breast", ingredient("chicken breast"))
    thigh = line("500 g chicken thigh", ingredient("chicken thigh"))
    assert check([(thigh, breast)], [breast, ONION], NONE) == []


def test_the_adapted_recipe_must_pass_the_rules_as_a_whole() -> None:
    """Fixing one line isn't enough when another still breaks the Rule."""
    bacon = line("4 rashers bacon", ingredient("bacon"))
    assert check([(BEEF, LENTILS)], [LENTILS, bacon, ONION], VEGETARIAN) == [
        "The recipe still breaks the Dietary Rules: bacon (vegetarian)"
    ]


def test_every_problem_is_reported_at_once() -> None:
    """So the agent can fix them all in one more try."""
    mystery = line("1 jar zorblax relish", None, needs_review=True)
    less = line("250 g brown onion", ingredient("brown onion"))
    problems = check([(BEEF, mystery), (ONION, less)], [mystery, less], VEGETARIAN)
    assert len(problems) == 3  # unknown, same Ingredient, and Rules: couldn't check
