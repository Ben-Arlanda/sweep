"""Graders (slice 8): pure functions of a RunRecord, so each is tested on a hand-built one."""

from dataclasses import replace
from decimal import Decimal

from app.llm_costs import Usage
from evals.agent_graders import (
    DEFAULT_CHECKS,
    called,
    changed_only_day,
    final_status,
    follows_rules,
    grade,
    grounded,
    meal_count,
    never_called,
    no_crash,
    nothing_dropped,
    only_chosen_days,
    proposal_made,
    revised_after_reject,
    summarise,
    uses_kitchen_item,
)
from evals.agent_harness import MealFacts, ProposalFacts, RunRecord, TurnFacts

MON, TUE, WED = "2026-11-16", "2026-11-17", "2026-11-18"


def meal(day: str, title: str = "Dhal", **changes: object) -> MealFacts:
    base = MealFacts(
        date=day,
        recipe_id=f"id-{title}",
        title=title,
        exists=True,
        rule_breaks=(),
        to_buy=2,
        kitchen_uses=("rice",),
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def proposal(
    *meals: MealFacts, status: str = "pending", dropped: tuple[str, ...] = ()
) -> ProposalFacts:
    return ProposalFacts(status=status, meals=meals, dropped=dropped, list_additions=0)


def turn(tools: tuple[str, ...] = (), replans: int = 0, error: str | None = None) -> TurnFacts:
    return TurnFacts(said="plan", reply="", tools=tools, replans=replans, error=error, seconds=10.0)


def record(
    *proposals: ProposalFacts,
    turns: tuple[TurnFacts, ...] = (),
    days: tuple[str, ...] | None = (MON, TUE),
    crashed: str | None = None,
) -> RunRecord:
    return RunRecord(
        scenario="s",
        model="claude-sonnet-5-5",
        turns=turns or (turn(),),
        proposals=proposals,
        chosen_days=days,
        usages=(Usage("claude-sonnet-5-5", 1_000_000, 100_000),),
        seconds=12.0,
        crashed=crashed,
    )


GOOD = record(proposal(meal(MON), meal(TUE, "Curry")))


def test_a_good_run_passes_every_default_check() -> None:
    assert all(check(GOOD).ok for check in DEFAULT_CHECKS)


def test_a_crash_or_an_error_fails() -> None:
    assert not no_crash(record(crashed="KeyError: x")).ok
    assert not no_crash(record(turns=(turn(error="That took too long."),))).ok


def test_no_proposal_fails_proposal_made() -> None:
    assert not proposal_made(record()).ok
    assert proposal_made(GOOD).ok


def test_a_made_up_recipe_fails_grounding() -> None:
    result = grounded(record(proposal(meal(MON, exists=False))))
    assert not result.ok and MON in result.detail


def test_a_rule_break_in_any_proposal_fails() -> None:
    # Even an earlier, superseded Proposal counts: a Member saw it.
    bad = proposal(meal(MON, rule_breaks=("peanuts (excluded)",)), status="superseded")
    result = follows_rules(record(bad, proposal(meal(MON))))
    assert not result.ok and "peanuts" in result.detail


def test_meals_on_other_days_fail() -> None:
    assert not only_chosen_days(record(proposal(meal(WED)))).ok
    # No days picked ("Just tonight" style): nothing to check.
    assert only_chosen_days(record(proposal(meal(WED)), days=None)).ok


def test_meal_count_and_dropped_meals() -> None:
    assert meal_count(2)(GOOD).ok
    result = meal_count(3)(GOOD)
    assert not result.ok and "2" in result.detail
    assert not nothing_dropped(record(proposal(meal(MON), dropped=("Tue: breaks vegan",)))).ok


def test_tools_called_and_not_called() -> None:
    run = record(proposal(meal(MON)), turns=(turn(tools=("recipes_from_kitchen", "propose_plan")),))
    assert called("recipes_from_kitchen")(run).ok
    assert not called("search_recipes")(run).ok
    assert never_called("search_recipes")(run).ok
    assert not never_called("propose_plan")(run).ok


def test_uses_a_kitchen_item() -> None:
    assert uses_kitchen_item("rice")(GOOD).ok
    assert not uses_kitchen_item("chicken thigh")(GOOD).ok


def test_final_status() -> None:
    assert final_status("approved")(record(proposal(meal(MON), status="approved"))).ok
    assert not final_status("approved")(GOOD).ok


def test_a_swap_changes_only_that_day() -> None:
    before = proposal(meal(MON), meal(TUE, "Curry"), status="superseded")
    swapped = proposal(meal(MON), meal(TUE, "Tacos"))
    assert changed_only_day(1)(record(before, swapped)).ok
    # Changing Monday too, or not changing Tuesday, both fail.
    assert not changed_only_day(1)(
        record(before, proposal(meal(MON, "Pho"), meal(TUE, "Tacos")))
    ).ok
    assert not changed_only_day(1)(record(before, proposal(meal(MON), meal(TUE, "Curry")))).ok
    assert not changed_only_day(1)(record(swapped)).ok  # only one Proposal


def test_reject_then_a_new_proposal() -> None:
    rejected = proposal(meal(MON), status="rejected")
    assert revised_after_reject(record(rejected, proposal(meal(MON, "Pho")))).ok
    assert not revised_after_reject(record(rejected)).ok


def test_grade_passes_only_if_every_check_passes_and_measures() -> None:
    run = record(
        proposal(meal(MON, to_buy=1), meal(TUE, to_buy=3)),
        turns=(turn(tools=("search_recipes", "set_planned_meal", "propose_plan"), replans=1),),
    )
    graded = grade(run, [*DEFAULT_CHECKS, meal_count(2)])
    assert graded.passed
    assert graded.measures.replans == 1
    assert graded.measures.tool_calls == 3
    assert graded.measures.to_buy_per_meal == 2.0
    # $2 per M input + $10 per M output on Sonnet
    assert graded.measures.cost_usd == Decimal("3.00")

    failed = grade(run, [meal_count(5)])
    assert not failed.passed
    assert [r.name for r in failed.failures] == ["meal_count(5)"]


def test_summary_gives_a_pass_rate_and_averages_per_scenario_and_model() -> None:
    passing = grade(GOOD, DEFAULT_CHECKS)
    failing = grade(GOOD, [meal_count(9)])
    [row] = summarise([passing, failing, passing])
    assert (row.scenario, row.model) == ("s", "claude-sonnet-5-5")
    assert (row.passed, row.runs) == (2, 3)
    assert row.cost_usd == Decimal("3.00")  # average per run
    assert row.failures == {"meal_count(9)": 1}
