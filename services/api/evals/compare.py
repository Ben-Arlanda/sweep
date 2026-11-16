"""Compare saved eval runs side by side (slice 8b). Free: reads results, calls nothing.

    uv run python -m evals.compare evals/results/A.json evals/results/B.json ...
    uv run python -m evals.compare ... --review review.json

Prints one row per (planner, model) over the Scenarios every file covers, then things
to buy per meal by Scenario. With --review, writes each Scenario's plans for a blind
human review: one plan per (planner, model) from the first repeat, shuffled and
labelled A, B, C… so the reader can't tell which approach or model made it. The key is
in the file, for after the ratings.

Why a human review: the checks are a safety floor (real recipes, Rules kept, right
days). They can't tell a good dinner from a side dish and a dessert, which is exactly
what the Baseline Planner's first Thai plan was.
"""

import argparse
import json
import random
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any

from evals.agent_scenarios import BY_NAME

Run = dict[str, Any]


def label(meta: dict[str, Any]) -> str:
    model = meta["model"].removeprefix("claude-").replace("-5-5", " 5.5")
    return f"{meta.get('planner', 'agent')} · {model}"


def load(paths: Sequence[Path]) -> dict[str, list[Run]]:
    columns: dict[str, list[Run]] = {}
    for path in paths:
        body = json.loads(path.read_text())
        columns.setdefault(label(body["meta"]), []).extend(body["runs"])
    return columns


def shared_scenarios(columns: dict[str, list[Run]]) -> list[str]:
    sets = [{r["record"]["scenario"] for r in runs} for runs in columns.values()]
    return sorted(set.intersection(*sets)) if sets else []


def summary(columns: dict[str, list[Run]], scenarios: Sequence[str]) -> str:
    lines = [f"{'':22}{'pass':>8}{'buy/meal':>10}{'secs':>7}{'per plan':>10}"]
    for name, runs in columns.items():
        runs = [r for r in runs if r["record"]["scenario"] in scenarios]
        buys = [r["measures"]["to_buy_per_meal"] for r in runs]
        buys = [b for b in buys if b is not None]
        cost = mean(float(r["measures"]["cost_usd"]) for r in runs)
        lines.append(
            f"{name:22}{f'{sum(r["passed"] for r in runs)}/{len(runs)}':>8}"
            f"{(mean(buys) if buys else 0):>10.1f}"
            f"{mean(r['measures']['seconds'] for r in runs):>7.1f}{cost * 100:>9.2f}¢"
        )
    return "\n".join(lines)


def setup_text(scenario: str) -> dict[str, Any]:
    s = BY_NAME[scenario].setup
    rules = [d.value.replace("_", " ") for d in sorted(s.diets)]
    rules += [f"no {name}" for name in s.excluded]
    return {
        "rules": ", ".join(rules) or "none",
        "likes": ", ".join(s.cuisines) or "none set",
        "kitchen": ", ".join(s.kitchen) or "nothing tracked",
        "mode": {None: "free chat", "kitchen": "Cook from my Kitchen", "new": "New recipes"}[
            s.mode.value if s.mode else None
        ],
    }


def review(
    columns: dict[str, list[Run]], scenarios: Sequence[str], seed: int = 8
) -> dict[str, Any]:
    rng = random.Random(seed)
    items = []
    for scenario in scenarios:
        firsts = [
            (name, next(r for r in runs if r["record"]["scenario"] == scenario))
            for name, runs in columns.items()
        ]
        rng.shuffle(firsts)
        plans = []
        for letter, (name, run) in zip("ABCDEFGH", firsts, strict=False):
            record = run["record"]
            final = record["proposals"][-1] if record["proposals"] else None
            plans.append(
                {
                    "label": letter,
                    "made_by": name,  # the key: hidden until after rating
                    "passed_checks": run["passed"],
                    "meals": [
                        {
                            "day": f"{date.fromisoformat(m['date']):%a}"
                            if len(m["date"]) == 10
                            else m["date"],
                            "title": m["title"],
                            "to_buy": m["to_buy"],
                        }
                        for m in (final["meals"] if final else [])
                    ],
                }
            )
        said = firsts[0][1]["record"]["turns"][0]["said"]
        items.append(
            {
                "scenario": scenario,
                "about": BY_NAME[scenario].about,
                "said": said,
                **setup_text(scenario),
                "plans": plans,
            }
        )
    return {"columns": list(columns), "scenarios": items}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--review", type=Path, help="write a blinded review file here")
    args = parser.parse_args(argv)
    columns = load(args.files)
    scenarios = shared_scenarios(columns)
    print(f"{len(scenarios)} Scenarios in every file.\n")
    print(summary(columns, scenarios))
    if args.review:
        args.review.write_text(json.dumps(review(columns, scenarios), indent=2))
        print(f"\nBlind review written to {args.review}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
