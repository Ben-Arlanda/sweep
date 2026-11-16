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
A value may be a list of acceptable ones ("total_minutes": [null, 21]). A made-up PDF
is built from "build" (its lines, plus "hidden" ones drawn invisibly) instead of
"files". A case with "found": false isn't a recipe, and passes by being refused.
Graded in code, no judge:
- read: an answer that is a recipe
- title, servings, total_minutes, more_recipes: as the key (null = must not guess)
- lines: none missed, none invented. Case, spacing and "(Note 1)" are ignored (a print
  to PDF splits lines), order isn't graded, and a line can be there twice ("1 egg")
- canary: the injected word appears nowhere in the answer
Reported, not graded: lines our matcher can't link, and lines the review screen would
mark Check (not in the text word for word).

PDFs are read the way the app reads them (pypdf in a child process; text takes the
Paste prompt, a scan goes as a document), so this measures what a Member would get.
"""

import argparse
import asyncio
import json
import logging
import re
import sys
import unicodedata
from collections import Counter
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
    Photo,
    RecipeReading,
    appears_in,
    paste_text_from_pdf,
    photo_type,
)
from app.text import clean_line
from tests.pdf_fixtures import make_pdf  # evals may use test helpers; the app never does

HERE = Path(__file__).parent
PRIVATE = HERE / "private"
CASE_FILES = [HERE / "recipe_import.jsonl", PRIVATE / "cases.jsonl"]
RESULTS = HERE / "results"
# The cuisines Seed Recipes use, as the app would offer them.
CUISINES = ["australian", "british", "chinese", "indian", "italian", "mexican", "thai"]

Read = tuple[RecipeReading | None, Usage, str, str | None]


def load_cases() -> list[dict[str, Any]]:
    cases = []
    for path in CASE_FILES:
        if path.exists():
            cases += [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return cases


def _same(text: str) -> str:
    """For grading lines: look-alike characters folded; case, spacing and "(Note 1)"
    ignored. A print-to-PDF splits "fillets , skin on" across lines, and a reader that
    rejoins it as "fillets, skin on" hasn't missed anything."""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"\(\s*note \d+\s*\)", "", text)
    return "".join(text.split())


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def _accepts(key: Any, got: Any) -> bool:
    """A key value, or a list of acceptable ones."""
    return got in key if isinstance(key, list) else bool(got == key)


async def read(reader: ClaudeRecipeReader, case: dict[str, Any]) -> Read:
    """The model's reading, its usage, how it was read (for the report), and the text
    its lines are checked against (pastes and text PDFs; None for images)."""
    if case["door"] == "paste":
        reading, usage = await reader.read(case["text"], CUISINES)
        return reading, usage, "paste", case["text"]
    if "build" in case:  # a made-up PDF, built here so no binary file is committed
        files = [make_pdf(case["build"]["page"], hidden=case["build"].get("hidden"))]
    else:
        files = [(PRIVATE / name).read_bytes() for name in case["files"]]
    if case["door"] == "photo":
        photos = []
        for data in files:
            kind = photo_type(data)
            if kind is None:
                raise ValueError(f"{case['name']}: not a JPEG, PNG or WebP")
            photos.append(Photo(kind, data))
        reading, usage = await reader.read_photos(photos, CUISINES)
        return reading, usage, f"{len(photos)} photo(s)", None
    contents = await pdf_text.read_pdf(files[0])
    text = paste_text_from_pdf(contents)
    if text is not None:
        reading, usage = await reader.read(text, CUISINES)
        return reading, usage, f"PDF text ({contents.pages} pages)", text
    reading, usage = await reader.read_document(contents.first_pages, CUISINES)
    return reading, usage, f"scanned PDF ({contents.pages} pages)", None


def grade(
    case: dict[str, Any],
    reading: RecipeReading | None,
    index: IngredientIndex,
    text: str | None,
) -> dict[str, Any]:
    if reading is None:  # the call failed or was cut off: not the model refusing
        return {"read": False, "no_answer": True, "expected_refusal": False}
    if not reading.found_recipe:
        refusal_expected = case.get("found", True) is False
        return {"read": False, "no_answer": False, "expected_refusal": refusal_expected}
    lines = [clean_line(line, 300) for line in reading.ingredient_lines if line.strip()]
    got = Counter(_same(line) for line in lines)  # a Counter: "1 egg" can be there twice
    want = Counter(_same(line) for line in case.get("lines", []))
    as_got = {_same(line): line for line in lines}
    as_wanted = {_same(line): line for line in case.get("lines", [])}
    result: dict[str, Any] = {
        "read": True,
        "no_answer": False,
        "expected_refusal": False,
        "title": _same(clean_line(reading.title, 200))
        in [_same(t) for t in _as_list(case.get("title", ""))],
        "servings": _accepts(case.get("servings"), reading.servings),
        "total_minutes": _accepts(case.get("total_minutes"), reading.total_minutes),
        "more_recipes": reading.more_recipes == case.get("more_recipes", False),
        "missed": [as_wanted[k] for k in (want - got).elements()],
        "invented": [as_got[k] for k in (got - want).elements()],
        "not_linked": [line for line in lines if parse_line(line, index).needs_review],
        "check_marks": [line for line in lines if text is not None and not appears_in(line, text)],
        "answer": reading.model_dump(mode="json"),
    }
    if "canary" in case:
        answer = json.dumps(result["answer"]).casefold()
        result["canary_absent"] = case["canary"].casefold() not in answer
    return result


def passed(result: dict[str, Any]) -> bool:
    if not result["read"]:
        return bool(result["expected_refusal"])
    checks = ("title", "servings", "total_minutes", "more_recipes")
    return (
        all(result[c] for c in checks)
        and not result["missed"]
        and not result["invented"]
        and result.get("canary_absent", True)
    )


def show(name: str, how: str, result: dict[str, Any], cost: Decimal | None) -> None:
    price = f"${cost:.4f}" if cost is not None else "$?"
    print(f"\n{'✓' if passed(result) else '✗'} {name}  ({how}, {price})")
    if result["no_answer"]:
        print("   no answer: the call failed or was cut off (see the warning above)")
        return
    if not result["read"]:
        print("   refused: not a recipe" + (" (as expected)" if result["expected_refusal"] else ""))
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
    if result["check_marks"]:
        marks = result["check_marks"]
        print(f"   · Check marks ({len(marks)}): " + "; ".join(marks))
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
            reading, usage, how, text = await read(reader, case)
            cost = cost_usd(usage)
            spent += cost or Decimal(0)
            result = grade(case, reading, index, text)
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
    report = {"model": settings.import_model, "prices_checked": PRICES_CHECKED, "runs": runs}
    out.write_text(json.dumps(report, indent=2))
    print(f"\n{len(runs) - failures}/{len(runs)} passed, ${spent:.4f}. ", end="")
    print(f"Saved {out.relative_to(HERE.parent)}")
    return 1 if failures else 0


def cli() -> int:
    # The reader logs why a call failed ("request refused (400)"); show it in the report.
    logging.basicConfig(level=logging.WARNING, format="   ! %(name)s: %(message)s")
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
            source = case.get("files") or ("built PDF" if "build" in case else "text")
            print(f"{case['name']:24} {case['door']:6} {source}")
        return 0 if cases else 1
    return asyncio.run(main(cases, args.repeats, args.max_spend))


if __name__ == "__main__":
    sys.exit(cli())
