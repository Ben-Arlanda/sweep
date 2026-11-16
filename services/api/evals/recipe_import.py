"""Recipe import eval: how well the model reads pastes, photos and PDFs (slice 4d step 8).

    uv run python -m evals.recipe_import --list
    uv run python -m evals.recipe_import --only kurhi --max-spend 0.05
    uv run python -m evals.recipe_import --repeats 3 --max-spend 0.20

COSTS MONEY: every case calls Claude (IMPORT_MODEL, Haiku by default) for real. Not run
in CI. Ask before running. The run stops before a case once --max-spend (US dollars,
estimated from tokens) is reached.

Cases, one JSON object per line, from two files:
- evals/recipe_import.jsonl: made-up pastes, safe to commit
- evals/private/cases.jsonl: the product owner's own photos and PDFs (git-ignored)

    {"name": "kurhi", "door": "photo", "files": ["kurhi-1.jpg", "kurhi-2.jpg"],
     "title": "...", "servings": 2, "total_minutes": null, "more_recipes": false,
     "lines": ["1/2 onion", ...], "canary": "saffron"}

`door` is paste (with "text"), photo (with "files") or file (one PDF in "files").
Graded in code, no LLM judge:
- read: an answer that is a recipe
- title, servings, total_minutes, more_recipes: exactly the key (null = must not guess)
- lines: none missed, none invented (case and spacing ignored, order not graded)
- linked: how many lines our matcher can't link (reported, not graded)
- canary: the injected word appears nowhere in the answer

Text PDFs are read the way the app reads them (pypdf in a child process, then the
Paste prompt), so this measures what a Member would get.
"""

import argparse
import asyncio
import json
import sys
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app import pdf_text
from app.config import settings
from app.db import make_engine, make_sessionmaker
from app.llm import ClaudeRecipeReader
from app.llm_costs import PRICES_CHECKED, Usage, cost_usd
from app.services.ingredient_lines import IngredientIndex, index_from_db, parse_line
from app.services.recipe_import import (
    MIN_PDF_TEXT,
    Photo,
    RecipeReading,
    photo_type,
)
from app.text import clean_line

HERE = Path(__file__).parent
PRIVATE = HERE / "private"
CASE_FILES = [HERE / "recipe_import.jsonl", PRIVATE / "cases.jsonl"]
RESULTS = HERE / "results"
# The cuisines Seed Recipes use, as the app would offer them.
CUISINES = ["australian", "british", "chinese", "indian", "italian", "mexican", "thai"]


def load_cases() -> list[dict[str, Any]]:
    cases = []
    for path in CASE_FILES:
        if path.exists():
            cases += [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return cases


def _same(text: str) -> str:
    """For comparing lines: look-alike characters folded, case and spacing ignored."""
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


async def read(
    reader: ClaudeRecipeReader, case: dict[str, Any]
) -> tuple[RecipeReading | None, Usage, str]:
    """The model's reading, its usage, and how it was read (for the report)."""
    if case["door"] == "paste":
        reading, usage = await reader.read(case["text"], CUISINES)
        return reading, usage, "paste"
    files = [(PRIVATE / name).read_bytes() for name in case["files"]]
    if case["door"] == "photo":
        photos = []
        for data in files:
            kind = photo_type(data)
            if kind is None:
                raise ValueError(f"{case['name']}: not a JPEG, PNG or WebP")
            photos.append(Photo(kind, data))
        reading, usage = await reader.read_photos(photos, CUISINES)
        return reading, usage, f"{len(photos)} photo(s)"
    contents = await pdf_text.read_pdf(files[0])
    text = contents.text.strip()
    if len("".join(text.split())) >= MIN_PDF_TEXT:
        reading, usage = await reader.read(text, CUISINES)
        return reading, usage, f"PDF text ({contents.pages} pages)"
    reading, usage = await reader.read_document(contents.first_pages, CUISINES)
    return reading, usage, f"scanned PDF ({contents.pages} pages)"


def grade(
    case: dict[str, Any], reading: RecipeReading | None, index: IngredientIndex
) -> dict[str, Any]:
    if reading is None or not reading.found_recipe:
        return {"read": False}
    lines = [clean_line(line, 300) for line in reading.ingredient_lines if line.strip()]
    got = {_same(line): line for line in lines}
    want = {_same(line): line for line in case.get("lines", [])}
    result: dict[str, Any] = {
        "read": True,
        "title": _same(clean_line(reading.title, 200)) == _same(case["title"]),
        "servings": reading.servings == case.get("servings"),
        "total_minutes": reading.total_minutes == case.get("total_minutes"),
        "more_recipes": reading.more_recipes == case.get("more_recipes", False),
        "missed": [want[k] for k in want if k not in got],
        "invented": [got[k] for k in got if k not in want],
        "not_linked": [line for line in lines if parse_line(line, index).needs_review],
        "answer": reading.model_dump(mode="json"),
    }
    if "canary" in case:
        everything = json.dumps(result["answer"]).casefold()
        result["canary_absent"] = case["canary"].casefold() not in everything
    return result


def passed(result: dict[str, Any]) -> bool:
    checks = ("read", "title", "servings", "total_minutes", "more_recipes")
    return (
        all(result.get(c) for c in checks)
        and not result.get("missed")
        and not result.get("invented")
        and result.get("canary_absent", True)
    )


def show(name: str, how: str, result: dict[str, Any], cost: Decimal | None) -> None:
    mark = "✓" if passed(result) else "✗"
    price = f"${cost:.4f}" if cost is not None else "$?"
    print(f"\n{mark} {name}  ({how}, {price})")
    if not result["read"]:
        print("   no recipe in the answer")
        return
    for field in ("title", "servings", "total_minutes", "more_recipes"):
        if not result[field]:
            print(f"   ✗ {field}: got {result['answer'][field]!r}")
    for line in result["missed"]:
        print(f"   ✗ missed:   {line}")
    for line in result["invented"]:
        print(f"   ✗ invented: {line}")
    if result.get("canary_absent") is False:
        print("   ✗ CANARY: the injected instruction got into the answer")
    if result["not_linked"]:
        print(f"   · Not linked ({len(result['not_linked'])}): " + "; ".join(result["not_linked"]))


async def main(cases: list[dict[str, Any]], repeats: int, max_spend: Decimal) -> int:
    key = settings.anthropic_api_key
    if key is None:
        print("ANTHROPIC_API_KEY isn't set.")
        return 2
    engine = make_engine(settings.database_url)  # dev, read-only: starters for matching
    async with make_sessionmaker(engine)() as session:
        index = await index_from_db(session)
    await engine.dispose()

    reader = ClaudeRecipeReader(key.get_secret_value(), settings.import_model)
    spent, runs, failures = Decimal(0), [], 0
    for repeat in range(1, repeats + 1):
        for case in cases:
            if spent >= max_spend:
                print(f"\nStopped: spent ${spent:.4f} of ${max_spend}.")
                break
            reading, usage, how = await read(reader, case)
            cost = cost_usd(usage)
            spent += cost or Decimal(0)
            result = grade(case, reading, index)
            failures += not passed(result)
            show(case["name"] + (f" #{repeat}" if repeats > 1 else ""), how, result, cost)
            runs.append(
                {
                    "case": case["name"],
                    "repeat": repeat,
                    "how": how,
                    "input_tokens": usage.all_input,
                    "output_tokens": usage.output_tokens,
                    "cost_usd": str(cost),
                    **result,
                }
            )

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"recipe_import-{datetime.now(UTC):%Y%m%d-%H%M%S}.json"
    out.write_text(
        json.dumps(
            {"model": settings.import_model, "prices_checked": PRICES_CHECKED, "runs": runs},
            indent=2,
        )
    )
    print(
        f"\n{len(runs) - failures}/{len(runs)} passed, ${spent:.4f}. "
        f"Saved {out.relative_to(HERE.parent)}"
    )
    return 1 if failures else 0


def cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--list", action="store_true", help="list the cases and stop (free)")
    parser.add_argument("--only", help="comma-separated case names")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-spend", type=Decimal, default=Decimal("0.10"), help="US dollars")
    args = parser.parse_args()
    cases = load_cases()
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c["name"] in wanted]
    if args.list or not cases:
        for case in cases:
            print(f"{case['name']:24} {case['door']:6} {case.get('files') or 'text'}")
        return 0 if cases else 1
    return asyncio.run(main(cases, args.repeats, args.max_spend))


if __name__ == "__main__":
    sys.exit(cli())
