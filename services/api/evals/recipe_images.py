"""Recipe Image check eval: does Haiku keep misleading photos off recipes? (slice 4f)

    uv run python -m evals.recipe_images --repeats 3 --max-spend 0.50

COSTS MONEY: every case calls Claude (Haiku) for real. Not run in CI.

Cases, one per line in evals/recipe_images.jsonl: a Seed Recipe, one candidate photo
(as the search found it) and what the check should say. "fail" cases are planted: a
photo of another dish, a diet clash (meat on a vegetarian recipe), raw ingredients, a
face. "pass" cases are real matches, labelled by looking at the photo.

The bar was set before the first run (ADR 0027): pooled over every run, no "fail" case
ever passes, and at least 80% of "pass" cases pass.
"""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.data.recipes import load_seed_recipes
from app.llm_costs import cost_usd
from app.services.recipe_image_check import ClaudeImageChecker, passes, title_clash
from scripts.recipe_images import AGENT, Candidate, download, for_checking

HERE = Path(__file__).parent
CASES = HERE / "recipe_images.jsonl"
RESULTS = HERE / "results"
MIN_PASS_RATE = Decimal("0.80")


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]


def score(outcomes: list[tuple[str, bool]]) -> dict[str, Any]:
    """(expected, passed) per answer. A model that couldn't answer counts as a fail."""
    good = [ok for want, ok in outcomes if want == "pass"]
    bad = [ok for want, ok in outcomes if want == "fail"]
    rate = Decimal(sum(good)) / len(good) if good else Decimal(0)
    return {
        "pass_rate": float(rate),
        "false_passes": sum(bad),
        "met": sum(bad) == 0 and rate >= MIN_PASS_RATE,
    }


async def run(repeats: int, max_spend: Decimal) -> int:
    if settings.anthropic_api_key is None:
        sys.exit("ANTHROPIC_API_KEY is not set")
    recipes = {r.slug: r for r in load_seed_recipes()}
    checker = ClaudeImageChecker(settings.anthropic_api_key.get_secret_value(), "claude-haiku-5-5")
    cases, spent = load_cases(), Decimal(0)
    rows: list[dict[str, Any]] = []
    async with httpx.AsyncClient(headers=AGENT, timeout=60, follow_redirects=True) as client:
        for n in range(repeats):
            for case in cases:
                if spent >= max_spend:
                    print(f"stopped: ${spent:.4f} spent")
                    break
                recipe = recipes[case["slug"]]
                candidate = Candidate.model_validate(case["candidate"])
                if why := title_clash(recipe, candidate.title):  # plain code, no model call
                    print(
                        f"{n + 1} {'ok ' if case['expect'] == 'fail' else 'BAD'} "
                        f"{case['name']:34} want {case['expect']:4} got fail  {why}"
                    )
                    rows.append(
                        {
                            "run": n + 1,
                            "name": case["name"],
                            "expect": case["expect"],
                            "passed": False,
                            "check": None,
                            "title_clash": why,
                        }
                    )
                    continue
                data = await download(client, candidate)
                photo = for_checking(data) if data else None
                assert photo, f"{case['name']}: couldn't download the photo"
                result, usage = await checker.check(recipe, photo)
                spent += cost_usd(usage) or Decimal(0)
                ok = bool(result and passes(result))
                mark = "ok " if ok == (case["expect"] == "pass") else "BAD"
                print(
                    f"{n + 1} {mark} {case['name']:34} want {case['expect']:4} "
                    f"got {'pass' if ok else 'fail'}  {result.model_dump() if result else None}"
                )
                rows.append(
                    {
                        "run": n + 1,
                        "name": case["name"],
                        "expect": case["expect"],
                        "passed": ok,
                        "check": result.model_dump() if result else None,
                    }
                )
    summary = score([(r["expect"], r["passed"]) for r in rows])
    print(
        f"pass rate {summary['pass_rate']:.0%}, false passes {summary['false_passes']}, "
        f"bar {'MET' if summary['met'] else 'NOT met'}; ${spent:.4f}"
    )
    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out = RESULTS / f"recipe_images-{stamp}.json"
    out.write_text(json.dumps({"summary": summary, "spent": str(spent), "rows": rows}, indent=1))
    return 0 if summary["met"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-spend", type=Decimal, default=Decimal("0.50"))
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.repeats, args.max_spend)))
