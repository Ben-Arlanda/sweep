"""Quantity maths is deterministic code, never the LLM (ADR 0003)."""

from decimal import Decimal

import pytest

from app.units import convert, parse_item_text, top_up

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


# --- topping up a list item (slice 6d) -----------------------------------------------


@pytest.mark.parametrize(
    ("have", "have_unit", "extra", "extra_unit", "base", "density", "expected"),
    [
        (D("4"), None, D("4"), None, "count", None, D("8")),  # 4 sausages + 4 more
        (D("500"), "g", D("300"), "g", "g", None, D("800")),
        (D("1"), "kg", D("500"), "g", "g", None, D("1.5")),  # kept in the list's unit
        (D("2"), "bunch", D("1"), "bunch", "count", None, D("3")),
        # Agent additions and list items can carry the base unit's own name, "count".
        (D("6"), "count", D("6"), "count", "count", None, D("12")),
        (D("1"), "L", D("250"), "ml", "ml", None, D("1.25")),
    ],
)
def test_adds_an_extra_amount_in_the_list_items_own_unit(
    have: Decimal,
    have_unit: str | None,
    extra: Decimal,
    extra_unit: str | None,
    base: str,
    density: Decimal | None,
    expected: Decimal,
) -> None:
    assert top_up(have, have_unit, extra, extra_unit, base, density) == expected


@pytest.mark.parametrize(
    ("have", "have_unit", "extra", "extra_unit", "base"),
    [
        (None, None, D("4"), None, "count"),  # "Sausages" with no amount: how many is that?
        (D("4"), None, None, None, "count"),  # nothing to add
        (D("1"), "jar", D("100"), "g", "g"),  # unknown unit: refuse to guess
        (D("1"), "bunch", D("200"), "g", "g"),
    ],
)
def test_refuses_to_add_amounts_it_cant_combine_honestly(
    have: Decimal | None,
    have_unit: str | None,
    extra: Decimal | None,
    extra_unit: str | None,
    base: str,
) -> None:
    assert top_up(have, have_unit, extra, extra_unit, base, None) is None
