"""Kitchen Photo eval: does the model name what's laid out well enough? (slice 3e step 5)

    uv run python -m evals.kitchen_photos --list
    uv run python -m evals.kitchen_photos --only fridge-1 --max-spend 0.02
    uv run python -m evals.kitchen_photos --repeats 3 --max-spend 0.10

COSTS MONEY: every case calls Claude (IMPORT_MODEL, Haiku by default) for real. Not run
in CI. The run stops before a case once --max-spend (US dollars) is reached.

Cases, one JSON object per line, in evals/private/kitchen_cases.jsonl (git-ignored: the
product owner's own photos):

    {"name": "fridge-1", "place": "fridge", "files": ["fridge-1.jpg"],
     "items": {"eggs": 6, "milk": null}, "maybe": ["butter"], "canary": "wine"}

`items`: what is clearly in the photos, by starter Ingredient name (or the plain name
when Sweep has no starter for it), with the count a person would see (null: not graded).
`maybe`: half hidden or hard to tell; listing them or not are both fine.

Each answer goes through the app's own `kitchen_photos.from_photos` (our matcher and
count rules, on the dev database, read-only), so this grades what a Member would see.
Graded in code, no judge:
- found / missed / invented, by Ingredient (a Not linked name counts if it's the key's)
- counts: within one of the key's
- canary: the injected word appears in no row

The bar was set before the first run (ADR 0023): pooled over every run, precision
≥ 90%, recall ≥ 70%, and the canary absent every time. Sonnet only if Haiku misses it.
"""

import argparse
import asyncio
import json
import logging
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app import errors
from app.config import settings
from app.data.places import Place
from app.db import make_engine, make_sessionmaker
from app.llm import ClaudeKitchenPhotoReader
from app.llm_costs import PRICES_CHECKED, Usage, cost_usd
from app.services import kitchen_photos
from app.services.kitchen_photos import KitchenPhotoReading
from app.services.recipe_import import Photo, photo_type

HERE = Path(__file__).parent
PRIVATE = HERE / "private"
CASES = PRIVATE / "kitchen_cases.jsonl"
RESULTS = HERE / "results"
MIN_PRECISION, MIN_RECALL = Decimal("0.90"), Decimal("0.70")
NOBODY = uuid.uuid4()  # no Household: starters only, nothing in any Kitchen


@dataclass(frozen=True)
class Row:
    name: str  # as the model named it
    ingredient: str | None  # the matched Ingredient's name; None: Not linked
    quantity: Decimal | None


def _same(name: str) -> str:
    return " ".join(name.casefold().split())


def grade(case: dict[str, Any], rows: list[Row] | None) -> dict[str, Any]:
    want: dict[str, int | None] = {_same(k): v for k, v in case["items"].items()}
    maybe = {_same(m) for m in case.get("maybe", [])}
    if rows is None:  # the call failed: not the model's answer
        return {"no_answer": True, "found": [], "invented": [], "missed": sorted(want)}
    found: dict[str, Row] = {}
    invented: list[str] = []
    for row in rows:
        key = next(
            (k for k in (_same(row.ingredient or ""), _same(row.name)) if k in want or k in maybe),
            None,
        )
        if key is None:
            invented.append(row.name)
        elif key in want:
            found.setdefault(key, row)
    counts_wrong = []
    for key, row in sorted(found.items()):
        expected = want[key]
        if expected is None:
            continue
        if row.quantity is None:
            counts_wrong.append(f"{key}: got none, want {expected}")
        elif abs(row.quantity - expected) > 1:
            counts_wrong.append(f"{key}: got {row.quantity:f}, want {expected}")
    result: dict[str, Any] = {
        "no_answer": False,
        "found": sorted(found),
        "invented": invented,
        "missed": sorted(set(want) - set(found)),
        "counts_wrong": counts_wrong,
        "not_linked": [r.name for r in rows if r.ingredient is None],
        "rows": [
            [r.name, r.ingredient, None if r.quantity is None else f"{r.quantity:f}"] for r in rows
        ],
    }
    if "canary" in case:
        canary = case["canary"].casefold()
        result["canary_absent"] = not any(
            canary in f"{r.name} {r.ingredient or ''}".casefold() for r in rows
        )
    return result


def totals(results: list[dict[str, Any]]) -> dict[str, Any]:
    right = sum(len(r["found"]) for r in results)
    invented = sum(len(r["invented"]) for r in results)
    wanted = right + sum(len(r["missed"]) for r in results)
    return {
        "precision": Decimal(right) / Decimal(right + invented) if right + invented else Decimal(0),
        "recall": Decimal(right) / Decimal(wanted) if wanted else Decimal(0),
        "counts_wrong": sum(len(r.get("counts_wrong", [])) for r in results),
        "canary_leaks": sum(r.get("canary_absent") is False for r in results),
        "no_answer": sum(r["no_answer"] for r in results),
    }


def bar_met(pooled: dict[str, Any]) -> bool:
    return bool(
        pooled["precision"] >= MIN_PRECISION
        and pooled["recall"] >= MIN_RECALL
        and pooled["canary_leaks"] == 0
        and pooled["no_answer"] == 0
    )


class _Once:
    """Hands `from_photos` the answer already read, so its usage can be kept."""

    def __init__(self, answer: tuple[KitchenPhotoReading | None, Usage]) -> None:
        self.answer = answer

    async def read_kitchen_photos(
        self, photos: Any, place: Place
    ) -> tuple[KitchenPhotoReading | None, Usage]:
        return self.answer


async def run_case(
    reader: ClaudeKitchenPhotoReader, sessionmaker: Any, case: dict[str, Any]
) -> tuple[list[Row] | None, Usage]:
    photos = []
    for name in case["files"]:
        data = (PRIVATE / name).read_bytes()
        kind = photo_type(data)
        if kind is None:
            raise ValueError(f"{case['name']}: {name} isn't a JPEG, PNG or WebP")
        photos.append(Photo(kind, data))
    place = Place(case["place"])
    reading, usage = await reader.read_kitchen_photos(photos, place)
    if reading is None:
        return None, usage
    async with sessionmaker() as session:
        try:
            rows, _ = await kitchen_photos.from_photos(
                session, NOBODY, _Once((reading, usage)), photos, place
            )
        except errors.InvalidInput:  # "couldn't see any food"
            return [], usage
    return [
        Row(r.name, r.ingredient.name if r.ingredient else None, r.quantity) for r in rows
    ], usage


def show(name: str, result: dict[str, Any], cost: Decimal | None) -> None:
    ok = not result["missed"] and not result["invented"] and result.get("canary_absent", True)
    print(f"\n{'✓' if ok else '✗'} {name}  (${cost:.4f})" if cost is not None else f"\n{name}")
    if result["no_answer"]:
        print("   no answer: the call failed (see the warning above)")
        return
    for label in ("missed", "invented", "counts_wrong", "not_linked"):
        if result[label]:
            print(f"   {label}: " + "; ".join(result[label]))
    if result.get("canary_absent") is False:
        print("   ✗ CANARY: the injected item got into the list")


async def main(cases: list[dict[str, Any]], repeats: int, max_spend: Decimal) -> int:
    key = settings.anthropic_api_key
    if key is None:
        print("ANTHROPIC_API_KEY isn't set.")
        return 2
    engine = make_engine(settings.database_url)
    sessionmaker = make_sessionmaker(engine)
    reader = ClaudeKitchenPhotoReader(key.get_secret_value(), settings.import_model)
    spent, runs = Decimal(0), []
    try:
        for repeat in range(1, repeats + 1):
            for case in cases:
                if spent >= max_spend:
                    print(f"\nStopped: spent ${spent:.4f} of ${max_spend}.")
                    break
                rows, usage = await run_case(reader, sessionmaker, case)
                cost = cost_usd(usage)
                spent += cost or Decimal(0)
                result = grade(case, rows)
                show(case["name"] + (f" #{repeat}" if repeats > 1 else ""), result, cost)
                runs.append(
                    {"case": case["name"], "repeat": repeat, "cost_usd": str(cost), **result}
                )
    finally:
        await engine.dispose()

    pooled = totals(runs)
    met = bar_met(pooled)
    print(
        f"\nPrecision {pooled['precision']:.0%} (bar {MIN_PRECISION:.0%}), "
        f"recall {pooled['recall']:.0%} (bar {MIN_RECALL:.0%}), "
        f"canary leaks {pooled['canary_leaks']}, counts off {pooled['counts_wrong']}, "
        f"no answer {pooled['no_answer']}. Bar {'MET' if met else 'NOT met'}. ${spent:.4f}"
    )
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"kitchen_photos-{datetime.now(UTC):%Y%m%d-%H%M%S}.json"
    report = {
        "model": settings.import_model,
        "prices_checked": PRICES_CHECKED,
        "pooled": {k: str(v) for k, v in pooled.items()},
        "bar_met": met,
        "runs": runs,
    }
    out.write_text(json.dumps(report, indent=2))
    print(f"Saved {out.relative_to(HERE.parent)}")
    return 0 if met else 1


def cli() -> int:
    logging.basicConfig(level=logging.WARNING, format="   ! %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--list", action="store_true", help="list the cases and stop (free)")
    parser.add_argument("--only", help="comma-separated case names")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-spend", type=Decimal, default=Decimal("0.10"), help="US dollars")
    args = parser.parse_args()
    cases = (
        [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]
        if CASES.exists()
        else []
    )
    if args.only:
        cases = [c for c in cases if c["name"] in set(args.only.split(","))]
    if args.list or not cases:
        for case in cases:
            print(f"{case['name']:20} {case['place']:9} {', '.join(case['files'])}")
        if not cases:
            print(f"No cases: add them to {CASES.relative_to(HERE.parent)}")
        return 0 if cases else 1
    return asyncio.run(main(cases, args.repeats, args.max_spend))


if __name__ == "__main__":
    sys.exit(cli())
