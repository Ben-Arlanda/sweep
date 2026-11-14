"""Quantity maths is deterministic code, never the LLM (ADR 0003)."""

from decimal import Decimal

import pytest

from app.units import convert, parse_item_text

D = Decimal


@pytest.mark.parametrize(
    ("quantity", "unit", "default_unit", "grams_per_ml", "expected"),
    [
        (D("1.5"), "kg", "g", None, D("1500")),
        (D("500"), "g", "g", None, D("500")),
        (D("2"), "L", "ml", None, D("2000")),
        (D("250"), "ml", "g", D("0.53"), D("132.5")),  # a cup-ish of flour, by density
        (D("6"), None, "count", None, D("6")),
        (D("6"), "each", "count", None, D("6")),
    ],
)
def test_converts_into_the_ingredients_unit(
    quantity: Decimal,
    unit: str | None,
    default_unit: str,
    grams_per_ml: Decimal | None,
    expected: Decimal,
) -> None:
    assert convert(quantity, unit, default_unit, grams_per_ml) == expected


@pytest.mark.parametrize(
    ("unit", "default_unit", "grams_per_ml"),
    [
        ("ml", "g", None),  # no density known: refuse to guess
        (None, "g", None),  # "2 chicken breasts" is not a weight
        ("kg", "count", None),
        ("bunch", "g", None),  # unknown unit
    ],
)
def test_refuses_conversions_it_cannot_do_honestly(
    unit: str | None, default_unit: str, grams_per_ml: Decimal | None
) -> None:
    assert convert(D("2"), unit, default_unit, grams_per_ml) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("500g pasta", ("pasta", D("500"), "g")),
        ("2 kg chicken thighs", ("chicken thighs", D("2"), "kg")),
        ("1.5L Milk", ("Milk", D("1.5"), "l")),
        ("6 eggs", ("eggs", D("6"), None)),
        ("2 lemons", ("lemons", D("2"), None)),
        ("Milk", ("Milk", None, None)),
        ("7up", ("7up", None, None)),  # a number glued to a word that isn't a unit
        ("500g", ("500g", None, None)),  # nothing left to be the name
    ],
)
def test_reads_a_leading_amount_off_what_was_typed(
    text: str, expected: tuple[str, Decimal | None, str | None]
) -> None:
    assert parse_item_text(text) == expected
