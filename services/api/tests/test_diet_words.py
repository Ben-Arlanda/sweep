"""Judging a food Sweep doesn't know by the words in its name (ADR 0032). No database."""

import pytest

from app.data.diet import Contains
from app.data.diet_words import judge, names_food

M, S, D, E, G, A = (
    Contains.MEAT,
    Contains.SEAFOOD,
    Contains.DAIRY,
    Contains.EGG,
    Contains.GLUTEN,
    Contains.ANIMAL,
)


@pytest.mark.parametrize(
    ("name", "likely", "check_label"),
    [
        # Words that name a risky food: held back
        ("andouille sausage", {M}, {G}),
        ("tiger prawns", {S}, set()),
        ("smoked cheddar", {D}, set()),
        ("duck eggs", {M, E}, set()),
        ("spelt flour", {G}, set()),
        ("sourdough bread", {G}, set()),
        ("manuka honey", {A}, set()),
        ("buttermilk", {D}, set()),
        # Depends on the brand: check the label
        ("satay sauce", set(), {G}),
        ("massaman curry paste", set(), {S, G}),
        ("cajun seasoning", set(), {G}),
        ("mushroom stock", set(), {M, G}),
        # Nothing risky named: passes
        ("finger limes", set(), set()),
        ("zorblax relish", set(), set()),
        ("eggplant", set(), set()),  # whole words: not egg
        ("butternut pumpkin", set(), set()),
        ("nutmeg", set(), set()),
    ],
)
def test_a_new_food_is_judged_by_its_words(
    name: str, likely: set[Contains], check_label: set[Contains]
) -> None:
    assert judge(name) == (frozenset(likely), frozenset(check_label))


@pytest.mark.parametrize(
    ("name", "likely"),
    [
        # Foods that only look risky
        ("peanut butter", set()),
        ("coconut cream", set()),
        ("oat milk", set()),
        ("rice noodles", set()),
        ("oyster mushrooms", set()),
        ("cream of tartar", set()),
        ("beef tomatoes", set()),
        ("corn tortillas", set()),
        # ...but anything else in the name still counts
        ("peanut butter cheesecake", {D, G}),
        # Qualifiers say what it's free of
        ("gluten free bread", set()),
        ("gluten-free spaghetti", set()),
        ("vegan cheese", set()),
        ("dairy free chocolate", set()),
        ("plant-based sausages", set()),
    ],
)
def test_exceptions_and_qualifiers(name: str, likely: set[Contains]) -> None:
    assert judge(name)[0] == frozenset(likely)


@pytest.mark.parametrize(
    ("name", "food", "named"),
    [
        ("shiitake mushrooms", "mushrooms", True),
        ("mushroom sauce", "mushrooms", True),  # plurals ignored
        ("button mushroom", "mushroom", True),
        ("coconut milk", "milk", False),  # an exception isn't the food
        ("peanut butter", "butter", False),
        ("eggplant", "eggs", False),  # whole words only
        ("pine nuts", "nuts", True),
        ("nutmeg", "nuts", False),
        ("mushrooms", "mushrooms", True),
        ("mixed berry jam", "berries", True),
        ("berries", "berry", True),
        ("cherry tomato", "tomatoes", True),
    ],
)
def test_an_excluded_food_matches_names_that_contain_it(name: str, food: str, named: bool) -> None:
    assert names_food(name, food) is named
