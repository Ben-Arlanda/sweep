"""Reading recipe ingredient lines with plain rules (no database, no LLM)."""

from collections.abc import Sequence
from decimal import Decimal

import pytest

from app.data.ingredients import INGREDIENTS
from app.models import ParseMethod
from app.services.ingredient_lines import (
    IngredientIndex,
    LineReading,
    normalise_lines,
    parse_line,
)

D = Decimal
INDEX = IngredientIndex.from_seed(INGREDIENTS)


@pytest.mark.parametrize(
    ("text", "ingredient", "quantity", "unit", "note"),
    [
        ("500 g beef mince", "beef mince", D("500"), "g", None),
        ("500g beef mince", "beef mince", D("500"), "g", None),
        ("1 onion, finely diced", "onion", D("1"), None, "finely diced"),
        ("2 tbsp olive oil", "olive oil", D("2"), "tbsp", None),
        ("2 tablespoons olive oil", "olive oil", D("2"), "tbsp", None),
        ("1 1/2 cups plain flour", "plain flour", D("1.5"), "cup", None),
        ("1½ cups plain flour", "plain flour", D("1.5"), "cup", None),
        ("½ tsp ground cumin", "ground cumin", D("0.5"), "tsp", None),
        # "garlic cloves" is also an alias, but garlic is counted in bulbs: 3 cloves ≠ 3 bulbs
        ("3 garlic cloves, crushed", "garlic", D("3"), "clove", "crushed"),
        ("3 cloves garlic, crushed", "garlic", D("3"), "clove", "crushed"),
        ("400 g can chickpeas, drained", "chickpeas", D("400"), "g", "drained"),
        ("2 x 400 g cans canned tomatoes", "canned tomatoes", D("800"), "g", None),
        ("2-3 large potatoes", "potatoes", D("3"), None, None),  # a range: buy for the top
        ("1 bunch coriander (leaves picked)", "coriander", D("1"), "bunch", "leaves picked"),
        ("1 lemon, juiced", "lemons", D("1"), None, "juiced"),
        ("salt, to taste", "salt", None, None, "to taste"),
        ("2 sticks celery, diced", "celery", D("2"), "stick", "diced"),
        ("4 lettuce leaves", "lettuce", D("4"), "leaf", None),
        ("2 bay leaves", "bay leaves", D("2"), None, None),  # "leaves" is part of the name
        ("1 loaf crusty bread", "bread", D("1"), "loaf", None),
        ("3 sheets puff pastry", "puff pastry", D("3"), "sheet", None),
        ("300 g cooked prawns", "cooked prawns", D("300"), "g", None),  # sold cooked
        ("Eggs", "eggs", None, None, None),
    ],
)
def test_reads_quantity_unit_name_and_note(
    text: str, ingredient: str, quantity: Decimal | None, unit: str | None, note: str | None
) -> None:
    line = parse_line(text, INDEX)
    assert line.ingredient is not None, f"no Ingredient for {text!r}"
    assert line.ingredient.name == ingredient
    assert (line.quantity, line.unit, line.note) == (quantity, unit, note)
    assert line.method == ParseMethod.RULE
    assert not line.needs_review


@pytest.mark.parametrize(
    ("text", "base_quantity"),
    [
        ("2 tbsp olive oil", D("40")),  # Australian tablespoon = 20 ml; olive oil is kept in ml
        ("1 cup plain flour", D("132.5")),  # 250 ml × 0.53 g/ml
        ("1 kg potatoes", D("1000")),
        ("2 eggs", D("2")),
        ("1 tsp ground cumin", None),  # no density for cumin: don't guess grams
        ("3 cloves garlic", None),  # garlic is counted in bulbs; cloves don't convert
        ("2 potatoes", None),  # potatoes are weighed; a count isn't a weight
        ("1 lb beef mince", D("453.592")),  # US recipes, via URL import
        ("8 oz. mushrooms", D("226.796")),
        ("3 sheets puff pastry", D("3")),  # pastry is counted in sheets
        # 4 cups of *cooked* rice is about 1⅓ cups dry: matching rice is right, but the
        # amount isn't an amount of what you'd buy.
        ("4 cups cooked rice", None),
    ],
)
def test_converts_to_the_ingredients_own_unit_only_when_honest(
    text: str, base_quantity: Decimal | None
) -> None:
    assert parse_line(text, INDEX).base_quantity == base_quantity


def test_flags_lines_it_cannot_match_instead_of_guessing() -> None:
    line = parse_line("1 cup unobtainium shavings", INDEX)
    assert line.ingredient is None
    assert line.needs_review
    assert (line.quantity, line.unit) == (D("1"), "cup")


def test_water_is_not_something_you_shop_for() -> None:
    line = parse_line("1 cup boiling water", INDEX)
    assert line.ingredient is None
    assert not line.needs_review


def test_marks_optional_lines() -> None:
    assert parse_line("1 tsp chilli flakes (optional)", INDEX).optional
    assert not parse_line("1 tsp chilli flakes", INDEX).optional


class ScriptedParser:
    """A fake LLM: returns readings we choose, and records what it was asked."""

    def __init__(self, readings: list[LineReading]) -> None:
        self.readings = readings
        self.asked: list[str] = []

    async def read_lines(
        self, lines: Sequence[str], ingredient_names: Sequence[str], units: Sequence[str]
    ) -> list[LineReading]:
        self.asked = list(lines)
        return self.readings


@pytest.mark.anyio
async def test_only_lines_the_rules_missed_go_to_the_llm() -> None:
    llm = ScriptedParser(
        [LineReading(line=0, quantity=1, unit=None, ingredient="lemons", note="juice only")]
    )
    lines = ["2 eggs", "juice of 1 lemon"]
    eggs, lemon = await normalise_lines(lines, INDEX, llm)

    assert llm.asked == ["juice of 1 lemon"]
    assert eggs.method == ParseMethod.RULE
    assert lemon.method == ParseMethod.LLM
    assert lemon.ingredient is not None and lemon.ingredient.name == "lemons"
    assert (lemon.quantity, lemon.base_quantity, lemon.note) == (D("1"), D("1"), "juice only")
    assert not lemon.needs_review


@pytest.mark.anyio
async def test_llm_answers_are_checked_against_our_lists() -> None:
    llm = ScriptedParser(
        [
            # Not one of our Ingredients: refused, the line stays flagged.
            LineReading(line=0, quantity=2, unit="cup", ingredient="dragon fruit", note=None),
            # Ours, but with a unit we don't know: keep the Ingredient, drop the unit.
            LineReading(line=1, quantity=3, unit="smidgen", ingredient="butter", note=None),
            # A line number we never sent: ignored.
            LineReading(line=7, quantity=1, unit=None, ingredient="salt", note=None),
        ]
    )
    dragon, butter = await normalise_lines(["2 c. pitaya", "3 knobs of butta"], INDEX, llm)
    assert dragon.ingredient is None and dragon.needs_review
    assert butter.ingredient is not None and butter.ingredient.name == "butter"
    assert (butter.unit, butter.base_quantity) == (None, None)  # 3 of what? we don't know
