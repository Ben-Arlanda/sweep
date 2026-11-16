"""Every agent Scenario sets up and reads correctly, for free, before any paid run."""

from datetime import timedelta

import pytest
from sqlalchemy import Engine

from app.agent.prompt import today_in_sydney
from evals.agent_harness import Say, build_household, open_database, words
from evals.agent_scenarios import BY_NAME, SCENARIOS, Scenario

pytestmark = pytest.mark.anyio


def test_there_are_about_fifteen_with_unique_names() -> None:
    assert 12 <= len(SCENARIOS) <= 20
    assert len(BY_NAME) == len(SCENARIOS)


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
