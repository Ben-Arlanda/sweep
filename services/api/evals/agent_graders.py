"""Graders for agent Scenarios (slice 8). Pure functions of a RunRecord: no database.

Two kinds, kept apart on purpose:
- Checks are must-pass. A run passes only if every check does. They cover what would
  hurt a Member: a made-up recipe, a broken Dietary Rule, a meal on the wrong day, no
  plan at all.
- Measures are reported, never pass/fail: replans, tool calls, things to buy, seconds,
  cost. They're for comparing (Sonnet vs Haiku, agent vs baseline), not for gating.

Every check reads what the agent *did* (Proposals, tool calls), never what it *said*.
"""

from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from statistics import mean

from app.llm_costs import cost_usd
from evals.agent_harness import MealFacts, RunRecord


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


Check = Callable[[RunRecord], CheckResult]


def _named(name: str) -> Callable[[Callable[[RunRecord], tuple[bool, str]]], Check]:
    """Turn `(record) -> (ok, detail)` into a Check that reports its name."""

    def wrap(fn: Callable[[RunRecord], tuple[bool, str]]) -> Check:
        def check(record: RunRecord) -> CheckResult:
            ok, detail = fn(record)
            return CheckResult(name, ok, "" if ok else detail)

        check.__name__ = name
        return check

    return wrap


def _final_meals(record: RunRecord) -> tuple[MealFacts, ...]:
    return record.final.meals if record.final else ()


# --- Checks every Scenario gets ---------------------------------------------------------


@_named("no_crash")
def no_crash(record: RunRecord) -> tuple[bool, str]:
    errors = [t.error for t in record.turns if t.error]
    if record.crashed:
        return False, record.crashed
    return not errors, "; ".join(e for e in errors if e)


@_named("grounded")
def grounded(record: RunRecord) -> tuple[bool, str]:
    """Every recipe in every Proposal exists in the Recipe Knowledge Base."""
    made_up = [f"{m.date} {m.recipe_id}" for p in record.proposals for m in p.meals if not m.exists]
    return not made_up, "unknown recipes: " + ", ".join(made_up)


@_named("follows_rules")
def follows_rules(record: RunRecord) -> tuple[bool, str]:
    """No Proposal the Member saw breaks a Dietary Rule, earlier ones included."""
    breaks = [
        f"{m.date} {m.title}: {', '.join(m.rule_breaks)}"
        for p in record.proposals
        for m in p.meals
        if m.rule_breaks
    ]
    return not breaks, "; ".join(breaks)


@_named("only_chosen_days")
def only_chosen_days(record: RunRecord) -> tuple[bool, str]:
    if record.chosen_days is None:
        return True, ""
    allowed = set(record.chosen_days)
    wrong = [m.date for p in record.proposals for m in p.meals if m.date not in allowed]
    return not wrong, "meals on days not picked: " + ", ".join(wrong)


DEFAULT_CHECKS: tuple[Check, ...] = (no_crash, grounded, follows_rules, only_chosen_days)


# --- Checks a Scenario adds -------------------------------------------------------------


@_named("proposal_made")
def proposal_made(record: RunRecord) -> tuple[bool, str]:
    return record.final is not None, "the agent never proposed a plan"


@_named("nothing_dropped")
def nothing_dropped(record: RunRecord) -> tuple[bool, str]:
    """validate had to take meals out after the replans ran out: the agent failed."""
    dropped = record.final.dropped if record.final else ()
    return not dropped, "; ".join(dropped)


def meal_count(n: int) -> Check:
    @_named(f"meal_count({n})")
    def check(record: RunRecord) -> tuple[bool, str]:
        got = len(_final_meals(record))
        return got == n, f"{got} meals, expected {n}"

    return check


def called(*tools: str) -> Check:
    @_named(f"called({', '.join(tools)})")
    def check(record: RunRecord) -> tuple[bool, str]:
        missing = [t for t in tools if t not in record.tool_calls]
        return not missing, "never called " + ", ".join(missing)

    return check


def never_called(*tools: str) -> Check:
    @_named(f"never_called({', '.join(tools)})")
    def check(record: RunRecord) -> tuple[bool, str]:
        used = [t for t in tools if t in record.tool_calls]
        return not used, "called " + ", ".join(used)

    return check


def uses_kitchen_item(name: str) -> Check:
    """Some meal in the final Proposal uses this Tracked Kitchen item ("use up the chicken")."""

    @_named(f"uses_kitchen_item({name})")
    def check(record: RunRecord) -> tuple[bool, str]:
        return any(name in m.kitchen_uses for m in _final_meals(record)), f"no meal uses {name}"

    return check


def final_status(status: str) -> Check:
    @_named(f"final_status({status})")
    def check(record: RunRecord) -> tuple[bool, str]:
        got = record.final.status if record.final else "no proposal"
        return got == status, f"final Proposal is {got}"

    return check


def changed_only_day(index: int) -> Check:
    """A follow-up ("swap Tuesday") changed that chosen day's meal and nothing else.
    `index` is the position in the chosen days, matching `{index}` in the message."""

    @_named(f"changed_only_day({index})")
    def check(record: RunRecord) -> tuple[bool, str]:
        if len(record.proposals) < 2 or record.chosen_days is None:
            return False, "needs a Proposal before and after the follow-up"
        day = record.chosen_days[index]
        before = {m.date: m.recipe_id for m in record.proposals[-2].meals}
        after = {m.date: m.recipe_id for m in record.proposals[-1].meals}
        if before.get(day) == after.get(day):
            return False, f"{day} wasn't changed"
        others = [
            d for d in before.keys() | after.keys() if d != day and before.get(d) != after.get(d)
        ]
        return not others, "also changed " + ", ".join(sorted(others))

    return check


@_named("revised_after_reject")
def revised_after_reject(record: RunRecord) -> tuple[bool, str]:
    statuses = [p.status for p in record.proposals]
    if "rejected" not in statuses:
        return False, "nothing was rejected"
    after = statuses[statuses.index("rejected") + 1 :]
    return bool(after), "no new Proposal after the reject"


# --- Measures and grading ---------------------------------------------------------------


@dataclass(frozen=True)
class Measures:
    replans: int
    tool_calls: int
    model_calls: int
    to_buy_per_meal: float | None  # final Proposal; None if it has no real meals
    seconds: float
    input_tokens: int  # every kind of input token
    output_tokens: int
    cost_usd: Decimal | None  # None if any call was on a model we have no price for


def measure(record: RunRecord) -> Measures:
    to_buy = [m.to_buy for m in _final_meals(record) if m.to_buy is not None]
    costs = [cost_usd(u) for u in record.usages]
    return Measures(
        replans=record.replans,
        tool_calls=len(record.tool_calls),
        model_calls=len(record.usages),
        to_buy_per_meal=mean(to_buy) if to_buy else None,
        seconds=record.seconds,
        input_tokens=sum(u.all_input for u in record.usages),
        output_tokens=sum(u.output_tokens for u in record.usages),
        cost_usd=None if None in costs else sum((c for c in costs if c is not None), Decimal(0)),
    )


@dataclass(frozen=True)
class Graded:
    record: RunRecord
    results: tuple[CheckResult, ...]
    measures: Measures

    @property
    def passed(self) -> bool:
        return all(r.ok for r in self.results)

    @property
    def failures(self) -> tuple[CheckResult, ...]:
        return tuple(r for r in self.results if not r.ok)


def grade(record: RunRecord, checks: Iterable[Check]) -> Graded:
    return Graded(record, tuple(check(record) for check in checks), measure(record))


@dataclass(frozen=True)
class Summary:
    """One Scenario on one model, over its repeats."""

    scenario: str
    model: str
    passed: int
    runs: int
    replans: float
    tool_calls: float
    to_buy_per_meal: float | None
    seconds: float
    cost_usd: Decimal | None  # average per run
    failures: dict[str, int]  # check name → how many runs failed it


def _avg(values: Sequence[float]) -> float:
    return mean(values) if values else 0.0


def summarise(graded: Iterable[Graded]) -> list[Summary]:
    groups: dict[tuple[str, str], list[Graded]] = {}
    for g in graded:
        groups.setdefault((g.record.scenario, g.record.model), []).append(g)
    rows = []
    for (scenario, model), runs in groups.items():
        m = [g.measures for g in runs]
        to_buy = [x.to_buy_per_meal for x in m if x.to_buy_per_meal is not None]
        costs = [x.cost_usd for x in m]
        rows.append(
            Summary(
                scenario=scenario,
                model=model,
                passed=sum(g.passed for g in runs),
                runs=len(runs),
                replans=_avg([x.replans for x in m]),
                tool_calls=_avg([x.tool_calls for x in m]),
                to_buy_per_meal=mean(to_buy) if to_buy else None,
                seconds=_avg([x.seconds for x in m]),
                cost_usd=(
                    None
                    if None in costs
                    else sum((c for c in costs if c is not None), Decimal(0)) / len(costs)
                ),
                failures=dict(Counter(f.name for g in runs for f in g.failures)),
            )
        )
    return rows
