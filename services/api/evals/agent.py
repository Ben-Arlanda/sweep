"""Agent evals: run the Scenarios on the real model and grade them (slice 8).

    uv run python -m evals.agent --model sonnet --repeats 3 --max-spend 5
    uv run python -m evals.agent --model haiku --only just-tonight,vegan-steak
    uv run python -m evals.agent --planner baseline --model sonnet --repeats 3
    uv run python -m evals.agent --list

COSTS MONEY: every Scenario calls Claude for real. Not run in CI. The run stops before
starting a Scenario once --max-spend (US dollars, estimated from tokens) is reached, so
the total can go over by up to one run. Repeats are the outer loop: if the cap stops
the run, every Scenario has still run the same number of times, give or take one.

Results go to evals/results/ (git-ignored) as JSON, with the price date, so two runs
can be compared later. The terminal table is the summary.

Eval-only settings, and why:
- `sweep_eval` database, emptied of Households each run, recipes and vectors from dev.
- Search-text vectors cached in evals/.cache/ (Voyage free tier: 3 requests a minute).
- The 60 s turn timeout is raised to 10 minutes and Voyage retries patiently: on the
  free tier a rate-limited search waits 20 s or more, and that's our account, not the
  agent. The time spent waiting is taken off the "seconds" measure.
"""

import argparse
import asyncio
import json
import logging
import sys
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app import tracing
from app.config import settings
from app.embeddings import VoyageEmbedder
from app.llm import ClaudeAgentModel, ClaudeStructured
from app.llm_costs import PRICES_CHECKED
from app.services import conversations
from evals.agent_graders import Graded, Summary, grade, summarise
from evals.agent_harness import (
    CachedEmbedder,
    load_recipes,
    open_database,
    prepare_eval_database,
    run_scenario,
)
from evals.agent_scenarios import BY_NAME, SCENARIOS, Scenario
from evals.baseline import run_baseline

EVALS = Path(__file__).resolve().parent
MODELS = {"sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}
EVAL_TURN_TIMEOUT = 600


def _money(value: Decimal | None) -> str:
    return "?" if value is None else f"${value:.3f}"


def table(rows: Sequence[Summary]) -> str:
    """The terminal summary: one line per Scenario × model."""
    head = (
        f"{'scenario':<32} {'planner':<8} {'model':<18} {'pass':>5} {'replan':>6} {'tools':>5} "
        f"{'buy/meal':>8} {'secs':>5} {'cost':>7} {'seen':>5}  failed checks"
    )
    lines = [head, "-" * len(head)]
    for r in rows:
        buy = "-" if r.to_buy_per_meal is None else f"{r.to_buy_per_meal:.1f}"
        failed = ", ".join(f"{name} ×{n}" for name, n in r.failures.items())
        # Injection Scenarios: in how many runs the model saw the planted text at all.
        seen = "-" if r.planted_seen is None else f"{r.planted_seen}/{r.runs}"
        lines.append(
            f"{r.scenario:<32} {r.planner:<8} {r.model:<18} {f'{r.passed}/{r.runs}':>5} "
            f"{r.replans:>6.1f} {r.tool_calls:>5.1f} {buy:>8} {r.seconds:>5.0f} "
            f"{_money(r.cost_usd):>7} {seen:>5}  {failed}"
        )
    return "\n".join(lines)


def totals(graded: Sequence[Graded]) -> str:
    runs = len(graded)
    passed = sum(g.passed for g in graded)
    costs = [g.measures.cost_usd for g in graded if g.measures.cost_usd is not None]
    spent = sum(costs, Decimal(0))
    per_pass = _money(spent / passed) if passed else "n/a"
    return (
        f"{passed}/{runs} runs passed ({passed / runs:.0%}). Spent about {_money(spent)}; "
        f"{per_pass} per passing run. Prices as of {PRICES_CHECKED}: an estimate, not an "
        "invoice."
        if runs
        else "No runs."
    )


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    return value


def results_json(graded: Sequence[Graded], meta: dict[str, Any]) -> str:
    runs = [
        {
            "passed": g.passed,
            "checks": [asdict(r) for r in g.results],
            "measures": asdict(g.measures),
            "record": asdict(g.record),
        }
        for g in graded
    ]
    body = {"meta": meta, "summary": [asdict(s) for s in summarise(graded)], "runs": runs}
    return json.dumps(_plain(body), indent=2)


async def run(
    model_id: str,
    scenarios: Sequence[Scenario],
    repeats: int,
    cap: Decimal,
    planner: str = "agent",
) -> int:
    anthropic_key, voyage_key = settings.anthropic_api_key, settings.voyage_api_key
    if anthropic_key is None or voyage_key is None:
        print("ANTHROPIC_API_KEY and VOYAGE_API_KEY must be set in services/api/.env")
        return 2
    conversations.TURN_TIMEOUT_SECONDS = EVAL_TURN_TIMEOUT  # see the module docstring
    # Eval traces get their own environment, so they never mix into dev dashboards.
    traced = tracing.configure(settings.model_copy(update={"langfuse_environment": "eval"}))

    prepare_eval_database(
        settings.eval_database_url, settings.database_url, settings.embedding_model
    )
    model = ClaudeAgentModel(anthropic_key.get_secret_value(), model_id, settings.agent_effort)
    picker = ClaudeStructured(anthropic_key.get_secret_value(), model_id, settings.agent_effort)
    if planner == "baseline":
        skipped = [s.name for s in scenarios if not s.single_message]
        scenarios = [s for s in scenarios if s.single_message]
        if skipped:
            print(f"Baseline skips follow-up Scenarios (n/a): {', '.join(skipped)}")
    voyage = VoyageEmbedder(
        voyage_key.get_secret_value(), settings.embedding_model, retries=6, backoff=20.0
    )
    embedder = CachedEmbedder(voyage, EVALS / ".cache" / f"queries-{voyage.model}.json")
    started = datetime.now(UTC)
    graded: list[Graded] = []
    spent = Decimal(0)
    stopped = False

    async with open_database(settings.eval_database_url) as db:
        loaded, vectors = await load_recipes(db, settings.database_url, settings.embedding_model)
        print(f"sweep_eval: {loaded} recipes, {vectors} vectors. Model {model_id}.\n")
        for repeat in range(1, repeats + 1):
            for scenario in scenarios:
                if spent >= cap:
                    stopped = True
                    break
                if planner == "baseline":
                    record = await run_baseline(db, picker, scenario)
                else:
                    record = await run_scenario(
                        db,
                        model,
                        embedder,
                        scenario.name,
                        scenario.setup,
                        scenario.steps,
                        trace_metadata={
                            "eval_run": f"{started:%Y%m%d-%H%M%S}",
                            "repeat": repeat,
                        },
                    )
                g = grade(record, scenario.checks_for(planner))
                graded.append(g)
                spent += g.measures.cost_usd or Decimal(0)
                mark = "pass" if g.passed else "FAIL " + ", ".join(r.name for r in g.failures)
                if not g.passed and traced:
                    mark += f"  [Langfuse session {record.session_id}]"
                print(
                    f"[{repeat}/{repeats}] {scenario.name:<32} {mark}  "
                    f"({g.measures.seconds:.0f}s, {_money(g.measures.cost_usd)})"
                )
            if stopped:
                print(f"\nStopped: --max-spend {_money(cap)} reached.")
                break

    tracing.flush()  # before exit, or the last traces are lost
    print()
    print(table(summarise(graded)))
    print()
    print(totals(graded))
    print(f"Embedding cache: {embedder.hits} hits, {embedder.misses} Voyage calls.")

    meta = {
        "planner": planner,
        "model": model_id,
        "effort": settings.agent_effort,
        "repeats": repeats,
        "max_spend": str(cap),
        "stopped_by_cap": stopped,
        "prices_checked": PRICES_CHECKED,
        "started": started.isoformat(),
        "scenarios": [s.name for s in scenarios],
    }
    out = EVALS / "results" / f"{started:%Y%m%d-%H%M%S}-{planner}-{model_id}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(results_json(graded, meta))
    print(f"Saved {out.relative_to(EVALS.parent)}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--model", default="sonnet", help="sonnet, haiku or a model id")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-spend", type=Decimal, default=Decimal(5), help="US dollars")
    parser.add_argument("--only", help="comma-separated Scenario names")
    parser.add_argument("--list", action="store_true", help="list the Scenarios and stop")
    parser.add_argument("--planner", choices=["agent", "baseline"], default="agent")
    parser.add_argument("--verbose", action="store_true", help="show each model call")
    args = parser.parse_args(argv)

    if args.list:
        for s in SCENARIOS:
            print(f"{s.name:<32} {s.about}")
        return 0
    try:
        chosen = [BY_NAME[n] for n in args.only.split(",")] if args.only else list(SCENARIOS)
    except KeyError as error:
        print(f"No Scenario {error}. Try --list.")
        return 2
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    model_id = MODELS.get(args.model, args.model)
    return asyncio.run(run(model_id, chosen, args.repeats, args.max_spend, args.planner))


if __name__ == "__main__":
    sys.exit(main())
