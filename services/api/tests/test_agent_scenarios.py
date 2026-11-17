"""Every agent Scenario sets up and reads correctly, for free, before any paid run."""

from datetime import timedelta

import pytest
from sqlalchemy import Engine

from app.agent.prompt import today_in_sydney
from evals.agent_harness import Say, build_household, open_database, words
from evals.agent_scenarios import ADAPTATIONS, BY_NAME, INJECTIONS, SCENARIOS, Scenario

pytestmark = pytest.mark.anyio


def test_about_fifteen_planning_scenarios_plus_the_injections() -> None:
    assert 12 <= len(SCENARIOS) - len(INJECTIONS) - len(ADAPTATIONS) <= 20
    assert len(INJECTIONS) == 8  # seven Injection Scenarios and one clean twin
    assert len(ADAPTATIONS) == 4  # slice 5e: favourite, Kitchen swap, no reason, wine
    assert len(BY_NAME) == len(SCENARIOS)


def test_every_injection_scenario_has_a_canary_or_rule_to_check() -> None:
    for scenario in INJECTIONS:
        names = " ".join(c.__name__ for c in scenario.all_checks)
        assert "follows_rules" in names  # every Scenario gets it
        if scenario.setup.planted and scenario.setup.diets == frozenset():
            assert "canary_absent" in names or "at_most_once" in names, scenario.name


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
async def test_each_scenario_builds_its_household(
    scenario: Scenario, database_url: str, db: Engine
) -> None:
    today = today_in_sydney()
    async with open_database(database_url) as eval_db, eval_db.sessionmaker() as session:
        _, ctx, _ = await build_household(session, scenario.setup, today)
        await session.rollback()
    days = (
        [today + timedelta(days=d) for d in scenario.setup.days]
        if scenario.setup.days is not None
        else None
    )
    for step in scenario.steps:
        if isinstance(step, Say):
            said = words(step, days)  # every {0}, {1}, {days} has a value
            assert "{" not in said
    assert scenario.about


def test_the_baseline_can_try_the_single_message_ones() -> None:
    single = [s.name for s in SCENARIOS if s.single_message]
    assert "week-new-recipes" in single
    assert "swap-one-day-then-approve" not in single
    assert len(single) >= 10


def test_every_scenario_wants_mains_unless_it_asks_for_more() -> None:
    for scenario in SCENARIOS:
        names = [c.__name__ for c in scenario.all_checks]
        expected = (
            "only_courses(main, breakfast)"
            if scenario.name == "pancakes-on-a-day"
            else ("only_courses(main)")
        )
        assert expected in names, scenario.name
