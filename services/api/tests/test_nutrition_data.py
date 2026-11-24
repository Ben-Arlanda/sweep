"""Turning AUSNUT rows into our nutrition records. No spreadsheets, no model calls."""

import json

from app.data.ingredients import INGREDIENTS
from scripts.nutrition_data import COLUMNS, MATCHES, OUT, entry, foods_from

HEADER = ("Survey ID", "Public food key", "Derivation", "Food name", *COLUMNS)
ONION = (1, "F1", "Analysed", "Onion, raw", 136, 1.3, 0, 0, 5.8, 5.8, 2.3, 8)
MEASURES = [
    ("Survey ID", "Public food key", "Food name", "Measure ID", "Quantity"),
    (1, "F1", "Onion, raw", 10, 1, "density", None, None, None, 0.56, 0),
    (1, "F1", "Onion, raw", 11, 1, "onion", "medium", None, None, 142, 0),
    (1, "F1", "Onion, raw", 12, 2, "cup", "chopped", None, None, 300, 500),
    (9, "F9", "Not in the profiles", 13, 1, "cup", None, None, None, 100, 250),
]


def test_measures_join_by_survey_id_because_the_food_keys_can_differ() -> None:
    other_key = [MEASURES[0], (1, "F6", "Onion, raw", 11, 1, "onion", "medium", 0, 0, 142, 0)]
    assert foods_from([HEADER, ONION], other_key)["F1"]["measures"]["11"]["grams"] == 142


def test_foods_keep_the_eight_values_and_the_measures_per_one() -> None:
    foods = foods_from([HEADER, ONION], MEASURES)
    onion = foods["F1"]
    assert onion["per_100g"]["energy_kj"] == 136
    assert onion["per_100g"]["sodium_mg"] == 8
    assert onion["density"] == 0.56
    assert onion["measures"]["11"] == {"text": "1 onion medium", "grams": 142, "ml": None}
    assert onion["measures"]["12"] == {"text": "2 cup chopped", "grams": 150, "ml": 250}
    assert "F9" not in foods


def test_a_density_with_a_description_is_still_a_density() -> None:
    chopped = (1, "F1", "Parsley, raw", 10, 1, "density", "chopped", None, None, 0.25, 0)
    parsley = [MEASURES[0], chopped]
    assert foods_from([HEADER, ONION], parsley)["F1"]["density"] == 0.25


def test_an_entry_has_grams_per_unit_from_the_picked_measures() -> None:
    onion = foods_from([HEADER, ONION], MEASURES)["F1"]
    record = entry("F1", onion, {"each": "11", "slice": None})
    assert record["grams_per"] == {"each": 142}
    assert record["grams_per_ml"] == 0.56
    assert record["food"] == "Onion, raw"


def test_density_falls_back_to_a_measure_with_a_volume() -> None:
    onion = foods_from([HEADER, ONION], MEASURES[:1] + MEASURES[3:4])["F1"]
    assert entry("F1", onion, {})["grams_per_ml"] == 0.6


def test_grams_typed_on_the_review_page_win() -> None:
    onion = foods_from([HEADER, ONION], MEASURES)["F1"]
    assert entry("F1", onion, {"each": "g:120"})["grams_per"] == {"each": 120}


def test_every_starter_has_been_matched() -> None:
    """A new starter needs `scripts.nutrition_data match` (and a look on the review page)."""
    done = json.loads(MATCHES.read_text())
    assert [i.name for i in INGREDIENTS if i.name not in done] == []
    table = json.loads(OUT.read_text())
    assert {n for n, m in done.items() if m["food"]} == set(table)
