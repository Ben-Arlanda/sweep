"""The Baseline Planner (slice 8b), with a scripted picker: free and repeatable.

The baseline is the no-agent alternative: code filters recipes by the Dietary Rules and
ranks them by Kitchen Match, then one model call picks from the list. No tools, no
replans. Graded by the same graders as the agent, so the comparison is fair.
"""

from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from pydantic import BaseModel
from sqlalchemy import Engine

from app.agent.prompt import today_in_sydney
from app.data.diet import Diet
from app.llm_costs import Usage
from app.models import PlanMode
from evals.agent_graders import called, meal_count, never_called
from evals.agent_harness import Approve, Say, Setup, open_database
from evals.agent_scenarios import SCENARIOS, Scenario
from evals.baseline import BaselinePlan, PlannedPick, run_baseline
from tests.conftest import Loader
from tests.test_agent import rid_in_db
from tests.test_dietary_rules import SALAD
from tests.test_recipes import CURRY, PASTA, STIR_FRY

pytestmark = pytest.mark.anyio

TOMORROW = (today_in_sydney() + timedelta(days=1)).isoformat()


class ScriptedPicker:
    """Returns a fixed plan, or one built from the prompt it was sent."""

    name = "scripted"

    def __init__(self, plan: Any) -> None:
        self.plan = plan
        self.prompts: list[str] = []

    async def parse(
        self, system: str, prompt: str, schema: type[BaseModel]
    ) -> tuple[BaseModel | None, Usage]:
        self.prompts.append(prompt)
        plan = self.plan(prompt) if callable(self.plan) else self.plan
        return plan, Usage(self.name, input_tokens=2000, output_tokens=200)


VEGETARIAN_TOMORROW = Scenario(
    "veg-tomorrow",
    "test",
    Setup(
        diets=frozenset({Diet.VEGETARIAN}),
        kitchen={"chickpeas": Decimal(400)},
        mode=PlanMode.KITCHEN,
        days=(1,),
    ),
    (Say("Plan dinners from what's in my Kitchen, for {days}."),),
    (meal_count(1), called("recipes_from_kitchen")),
)


def pick_line_with(title: str) -> Any:
    """A picker that chooses the candidate whose line names `title`."""

    def plan(prompt: str) -> BaselinePlan:
        [line] = [line for line in prompt.splitlines() if title in line]
        recipe_id = line.removeprefix("- ").split(" | ")[0]
        meal = PlannedPick(date=TOMORROW, recipe_id=recipe_id, servings=2)
        return BaselinePlan(meals=[meal], summary=f"{title} tomorrow.")

    return plan


async def test_the_code_filters_by_rules_before_the_model_sees_anything(
    database_url: str, load: Loader, db: Engine
) -> None:
    await load([CURRY, PASTA, STIR_FRY, SALAD])
    picker = ScriptedPicker(pick_line_with("Chickpea salad"))
    async with open_database(database_url) as eval_db:
        record = await run_baseline(eval_db, picker, VEGETARIAN_TOMORROW)

    [prompt] = picker.prompts
    curry = await rid_in_db(db, "chicken-curry")
    assert curry not in prompt and "Chicken and chickpea curry" not in prompt
    assert "Chickpea salad" in prompt  # rule-safe, and uses the chickpeas
    assert "Plan dinners from what's in my Kitchen, for" in prompt  # the Member's words
    # Ranked by Kitchen Match: the salad (uses the chickpeas) comes before pasta.
    assert prompt.index("Chickpea salad") < prompt.index("Quick tomato pasta")

    assert record.planner == "baseline" and record.model == "scripted"
    [meal] = record.final.meals if record.final else ()
    assert meal.title == "Chickpea salad" and meal.date == TOMORROW and meal.exists
    assert record.tool_calls == () and record.replans == 0
    assert len(record.usages) == 1


async def test_a_bad_pick_is_graded_not_fixed(database_url: str, load: Loader) -> None:
    # No validate and no replans: what one call produces is exactly what's graded.
    await load([CURRY, SALAD])
    made_up = BaselinePlan(
        meals=[PlannedPick(date=TOMORROW, recipe_id="not-a-recipe", servings=2)], summary=""
    )
    async with open_database(database_url) as eval_db:
        record = await run_baseline(eval_db, ScriptedPicker(made_up), VEGETARIAN_TOMORROW)
    [meal] = record.final.meals if record.final else ()
    assert not meal.exists


async def test_no_answer_means_no_proposal(database_url: str, load: Loader) -> None:
    await load([SALAD])
    async with open_database(database_url) as eval_db:
        record = await run_baseline(eval_db, ScriptedPicker(None), VEGETARIAN_TOMORROW)
    assert record.proposals == () and record.crashed is None


def test_tool_checks_do_not_apply_to_the_baseline() -> None:
    # It has no tools, so "called recipes_from_kitchen" would fail it for nothing.
    names = [c.__name__ for c in VEGETARIAN_TOMORROW.checks_for("baseline")]
    assert "called(recipes_from_kitchen)" not in names and "meal_count(1)" in names
    agent = [c.__name__ for c in VEGETARIAN_TOMORROW.checks_for("agent")]
    assert "called(recipes_from_kitchen)" in agent
    assert never_called("x").__name__.startswith("never_called(")


def test_the_baseline_only_runs_single_message_scenarios() -> None:
    multi = Scenario("m", "test", Setup(), (Say("hi"), Approve()))
    assert not multi.single_message
    assert sum(s.single_message for s in SCENARIOS) >= 10
