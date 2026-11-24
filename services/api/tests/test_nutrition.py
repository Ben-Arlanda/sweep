"""A recipe's Nutrition per serve, added up from its lines (ADR 0035). Plain maths, no DB."""

from decimal import Decimal
from types import SimpleNamespace as NS
from typing import Any

from app.services.nutrition import nutrition_per_serve

PER_100G = dict.fromkeys(
    ("energy_kj", "protein_g", "fat_g", "saturated_fat_g", "carbs_g", "sugars_g", "fibre_g"), 0.0
) | {"sodium_mg": 0.0}


def food(**values: float) -> dict[str, Any]:
    return {"per_100g": PER_100G | values, "grams_per_ml": None, "grams_per": {}}


TABLE = {
    "chicken thigh": food(energy_kj=600, protein_g=20, fat_g=5),
    "olive oil": food(energy_kj=3700, fat_g=100) | {"grams_per_ml": 0.92},
    "onion": food(energy_kj=136, carbs_g=6) | {"grams_per": {"each": 142}},
    "garlic": food(energy_kj=400) | {"grams_per": {"clove": 5}},
    "salt": food(sodium_mg=38000),
}


def line(name: str | None, qty: str | None, unit: str | None = None, **kw: Any) -> NS:
    category = kw.pop("category", "pantry")
    ingredient = name and NS(name=name, category=category, default_unit=kw.pop("base", "g"))
    base = kw.pop("base_quantity", qty if unit in (None, "g") else None)
    return NS(
        raw_text=kw.pop("raw", f"{qty} {unit or ''} {name}"),
        ingredient=ingredient,
        quantity=Decimal(qty) if qty else None,
        unit=unit,
        base_quantity=Decimal(base) if base else None,
        optional=kw.pop("optional", False),
        needs_review=kw.pop("needs_review", name is None),
    )


def test_adds_up_each_line_and_divides_by_the_servings() -> None:
    lines = [
        line("chicken thigh", "800", "g"),
        line("olive oil", "1", "tbsp", base="ml", base_quantity="20"),
        line("onion", "2", base="count", base_quantity="2"),
    ]
    n = nutrition_per_serve(lines, servings=4, table=TABLE)
    assert n.available
    # chicken 800 g = 4800 kJ; oil 20 ml × 0.92 = 18.4 g = 680.8 kJ; onion 284 g = 386.24 kJ
    assert n.per_serve is not None
    assert n.per_serve.energy_kj == round((4800 + 680.8 + 386.24) / 4, 1)
    assert n.per_serve.protein_g == 40
    assert n.left_out == []


def test_a_unit_with_no_fixed_size_uses_the_ingredients_own_measure() -> None:
    n = nutrition_per_serve([line("garlic", "3", "clove", base_quantity=None)], 1, TABLE)
    assert n.per_serve is not None and n.per_serve.energy_kj == 60  # 3 × 5 g × 4 kJ/g


def test_to_taste_optional_and_pinch_lines_are_left_out_quietly() -> None:
    lines = [
        line("chicken thigh", "500", "g"),
        line("salt", None, raw="Salt, to taste"),
        line("onion", "1", base="count", optional=True),
        line("salt", "1", "pinch", base_quantity=None),
    ]
    n = nutrition_per_serve(lines, 1, TABLE)
    assert n.available and n.left_out == []
    assert n.per_serve is not None and n.per_serve.sodium_mg == 0


def test_a_small_line_with_no_values_is_named_but_the_rest_still_shows() -> None:
    lines = [line("chicken thigh", "800", "g"), line("nonna's chilli oil", "1", "tbsp")]
    n = nutrition_per_serve(lines, 4, TABLE)
    assert n.available
    assert n.left_out == ["nonna's chilli oil"]


def test_an_unknown_main_protein_makes_it_unavailable() -> None:
    lines = [line("kangaroo fillet", "2", category="meat"), line("onion", "1", base="count")]
    n = nutrition_per_serve(lines, 4, TABLE)
    assert not n.available and n.per_serve is None
    assert n.left_out == ["kangaroo fillet"]


def test_a_heavy_unknown_line_makes_it_unavailable() -> None:
    lines = [line("chicken thigh", "500", "g"), line("mystery grain", "200", "g")]
    assert not nutrition_per_serve(lines, 4, TABLE).available  # 200 of 700 g is over 15%


def test_a_line_matched_to_nothing_is_named_by_its_text() -> None:
    lines = [line("chicken thigh", "500", "g"), line(None, "1", "tsp", raw="1 tsp zorblax")]
    assert nutrition_per_serve(lines, 2, TABLE).left_out == ["1 tsp zorblax"]


def test_no_lines_with_values_is_unavailable() -> None:
    n = nutrition_per_serve([line("salt", None, raw="Salt, to taste")], 2, TABLE)
    assert not n.available


def test_water_counts_as_nothing() -> None:
    water = line(None, "400", "ml", raw="400 ml water", needs_review=False)
    n = nutrition_per_serve([line("chicken thigh", "500", "g"), water], 2, TABLE)
    assert n.available and n.left_out == []


def test_only_a_tenth_of_deep_frying_oil_is_eaten() -> None:
    oil = line(
        "olive oil", "1", "l", base="ml", base_quantity="1000", raw="1 l oil, for deep-frying"
    )
    n = nutrition_per_serve([line("chicken thigh", "500", "g"), oil], 1, TABLE)
    assert n.per_serve is not None and n.per_serve.fat_g == round(25 + 92, 1)  # 920 g × 10%


def test_a_big_oil_line_is_frying_oil_even_unsaid() -> None:
    oil = line("olive oil", "750", "ml", base="ml", base_quantity="750", raw="750 ml olive oil")
    n = nutrition_per_serve([line("chicken thigh", "500", "g"), oil], 1, TABLE)
    assert n.per_serve is not None and n.per_serve.fat_g == round(25 + 69, 1)  # 690 g × 10%


def test_a_spoon_of_oil_is_eaten_whole() -> None:
    oil = line("olive oil", "2", "tbsp", base="ml", base_quantity="40", raw="2 tbsp olive oil")
    n = nutrition_per_serve([line("chicken thigh", "500", "g"), oil], 1, TABLE)
    assert n.per_serve is not None and n.per_serve.fat_g == round(25 + 36.8, 1)
