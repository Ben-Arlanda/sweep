"""The Kitchen Photo eval's grading (free, no model): what counts as found, invented,
missed, and whether the pre-set bar is met (ADR 0023)."""

from decimal import Decimal
from typing import Any

from evals.kitchen_photos import Row, bar_met, grade, totals

CASE: dict[str, Any] = {
    "name": "fridge-1",
    "items": {"eggs": 6, "milk": None, "greek yoghurt": None},
    "maybe": ["butter"],  # half hidden: listing it or not are both fine
}


def test_found_invented_and_missed_are_by_ingredient() -> None:
    rows = [
        Row("free range eggs", "eggs", Decimal(6)),  # named differently, same Ingredient
        Row("butter", "butter", None),  # a maybe: neither right nor wrong
        Row("sponge", None, None),  # not food: invented
    ]

    result = grade(CASE, rows)

    assert result["found"] == ["eggs"]
    assert result["invented"] == ["sponge"]
    assert result["missed"] == ["greek yoghurt", "milk"]


def test_a_not_linked_name_still_counts_when_it_matches_the_key() -> None:
    # The model was right; our matcher just doesn't know the name (a starter to add).
    result = grade(CASE, [Row("Greek yoghurt", None, None)])

    assert result["found"] == ["greek yoghurt"]
    assert result["not_linked"] == ["Greek yoghurt"]


def test_counts_are_right_within_one() -> None:
    assert grade(CASE, [Row("eggs", "eggs", Decimal(5))])["counts_wrong"] == []
    wrong = grade(CASE, [Row("eggs", "eggs", Decimal(12))])["counts_wrong"]
    assert wrong == ["eggs: got 12, want 6"]
    # No count where one was wanted is wrong too: the Member would have to type it.
    assert grade(CASE, [Row("eggs", "eggs", None)])["counts_wrong"] == ["eggs: got none, want 6"]


def test_the_canary_must_be_absent() -> None:
    case = CASE | {"canary": "wine"}

    assert grade(case, [Row("eggs", "eggs", Decimal(6))])["canary_absent"] is True
    assert grade(case, [Row("red wine", None, Decimal(20))])["canary_absent"] is False


def test_no_answer_is_its_own_failure() -> None:
    result = grade(CASE, None)

    assert result["no_answer"] is True
    assert result["missed"] == ["eggs", "greek yoghurt", "milk"]


def test_the_bar_is_pooled_over_every_run() -> None:
    good = grade(CASE, [Row("eggs", "eggs", Decimal(6)), Row("milk", "milk", None)])
    poor = grade(CASE, [Row("sponge", None, None)])

    pooled = totals([good, good, poor])

    assert pooled["precision"] == Decimal(4) / Decimal(5)  # 4 right, 1 invented
    assert pooled["recall"] == Decimal(4) / Decimal(9)  # 4 of 3 × 3 items
    assert bar_met(pooled) is False
    assert bar_met(totals([good, good])) is False  # recall 2/3 < 70%
    full = grade(CASE, [Row(n, n, Decimal(6) if n == "eggs" else None) for n in CASE["items"]])
    assert bar_met(totals([full, full])) is True


def test_one_canary_leak_fails_the_bar() -> None:
    case = CASE | {"canary": "wine"}
    full = [Row(n, n, Decimal(6) if n == "eggs" else None) for n in CASE["items"]]
    leaked = grade(case, [*full, Row("wine", None, Decimal(20))])

    assert bar_met(totals([grade(case, full), grade(case, full), leaked])) is False


def test_a_key_can_name_alternatives_and_counts_once() -> None:
    # Not linked items are graded by name, and a model may say either.
    case = {"name": "c", "items": {"bread|gluten free bread": None, "goat cheese|chevre": None}}

    result = grade(case, [Row("Gluten-free bread", None, None), Row("chevre", None, None)])

    assert result["found"] == ["bread", "goat cheese"]
    assert result["invented"] == []
