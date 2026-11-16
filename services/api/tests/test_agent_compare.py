"""The comparison report (slice 8b): blinded, fair, reproducible. No model calls."""

from typing import Any

from evals.compare import review, shared_scenarios, summary


def run(scenario: str, title: str, passed: bool = True) -> dict[str, Any]:
    meal = {"date": "2026-11-17", "title": title, "to_buy": 2}
    return {
        "passed": passed,
        "measures": {"to_buy_per_meal": 2.0, "seconds": 5.0, "cost_usd": "0.01"},
        "record": {
            "scenario": scenario,
            "turns": [{"said": "Plan new recipes to shop for, for Tue 17 Nov."}],
            "proposals": [{"meals": [meal]}],
        },
    }


COLUMNS = {
    "agent · sonnet 5.5": [run("week-new-recipes", "Pho"), run("just-tonight", "Dhal")],
    "baseline · haiku 5.5": [run("week-new-recipes", "Tacos")],
}


def test_only_scenarios_every_column_ran_are_compared() -> None:
    # The baseline skips follow-ups; comparing them would compare nothing.
    assert shared_scenarios(COLUMNS) == ["week-new-recipes"]
    assert "1/1" in summary(COLUMNS, ["week-new-recipes"])


def test_the_review_hides_who_made_each_plan_behind_a_letter() -> None:
    [item] = review(COLUMNS, ["week-new-recipes"])["scenarios"]
    assert [p["label"] for p in item["plans"]] == ["A", "B"]
    assert {p["made_by"] for p in item["plans"]} == set(COLUMNS)
    assert item["plans"][0]["meals"][0]["day"] == "Tue"
    assert item["mode"] == "New recipes"  # what the Member asked for, to judge against


def test_the_shuffle_is_the_same_every_time() -> None:
    first = review(COLUMNS, ["week-new-recipes"])
    assert review(COLUMNS, ["week-new-recipes"]) == first
