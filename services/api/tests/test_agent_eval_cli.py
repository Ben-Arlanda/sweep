"""The agent eval's report (slice 8): table, totals and saved JSON. No model calls."""

import json
from dataclasses import replace

from evals.agent import main, results_json, table, totals
from evals.agent_graders import DEFAULT_CHECKS, grade, meal_count, summarise
from tests.test_agent_graders import GOOD


def test_the_table_and_totals_read_well() -> None:
    graded = [grade(GOOD, DEFAULT_CHECKS), grade(GOOD, [meal_count(9)])]
    text = table(summarise(graded))
    assert "1/2" in text and "meal_count(9) ×1" in text and "$3.000" in text
    assert totals(graded).startswith("1/2 runs passed (50%). Spent about $6.000; $6.000 per")
    assert totals([]) == "No runs."


def test_the_table_says_how_often_a_plant_was_seen() -> None:
    planted = [grade(replace(GOOD, planted_seen=seen), []) for seen in (True, False, True)]
    assert " 2/3 " in table(summarise(planted))
    assert " - " in table(summarise([grade(GOOD, [])]))  # nothing planted


def test_results_save_as_plain_json() -> None:
    saved = json.loads(results_json([grade(GOOD, DEFAULT_CHECKS)], {"model": "x"}))
    assert saved["meta"] == {"model": "x"}
    assert saved["summary"][0]["passed"] == 1
    assert saved["runs"][0]["measures"]["cost_usd"] == "3.00"
    assert saved["runs"][0]["record"]["proposals"][0]["meals"][0]["title"] == "Dhal"


def test_list_and_a_wrong_name_cost_nothing(capsys: object) -> None:
    assert main(["--list"]) == 0
    assert main(["--only", "no-such-scenario"]) == 2
