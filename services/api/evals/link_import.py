"""Link import on real pages: the safe fetcher and the JSON-LD reader (slice 4d).

    uv run python -m evals.link_import https://example.com/some-recipe [more links…]
    uv run python -m evals.link_import --keyed          # the links in link_import.jsonl

FREE: no model is called. It does fetch each link once, for real, as SweepBot/1.0, and
obeys robots.txt exactly like the app. Tests use made-up pages; this shows what real
sites publish, and how many of their lines our matcher can link.

Per link it prints what the Link door would put on the review screen, each line's
Ingredient (or "Not linked"), and anything that went wrong. With --keyed, each link in
evals/link_import.jsonl is graded against its answer key:
    {"url": "...", "title": "...", "servings": 4, "total_minutes": 135, "lines": 9}
(any of the keys after url may be left out).

Results go to evals/results/ (git-ignored) as JSON. The pages themselves are never
saved: they're someone else's work.
"""

import argparse
import asyncio
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app import errors
from app.config import settings
from app.db import make_engine, make_sessionmaker
from app.services import recipes
from app.services.ingredient_lines import index_from_db, parse_line
from app.services.recipe_jsonld import read_recipe
from app.web_fetch import SafeFetcher

HERE = Path(__file__).parent
KEYS = HERE / "link_import.jsonl"
RESULTS = HERE / "results"


async def run_one(
    url: str, fetcher: SafeFetcher, index: Any, cuisines: list[str]
) -> dict[str, Any]:
    result: dict[str, Any] = {"url": url}
    try:
        page = await fetcher.fetch(url)
    except errors.DomainError as error:
        return result | {"error": f"{type(error).__name__}: {error.message}"}
    result["final_url"] = page.url
    found = read_recipe(page.html, cuisines)
    if found is None:
        return result | {"error": "no Recipe JSON-LD with a title and ingredient lines"}
    lines = []
    for raw in found.ingredient_lines:
        parsed = parse_line(raw, index)  # starters only: a new Household has no links yet
        lines.append(
            {
                "raw": raw,
                "ingredient": parsed.ingredient.name if parsed.ingredient else None,
                "quantity": str(parsed.quantity) if parsed.quantity is not None else None,
                "unit": parsed.unit,
                "not_linked": parsed.needs_review,
            }
        )
    return result | {
        "title": found.title,
        "servings": found.servings,
        "total_minutes": found.total_minutes,
        "course": found.course.value,
        "cuisine": found.cuisine,
        "more_recipes": found.more_recipes,
        "lines": lines,
    }


def grade(result: dict[str, Any], key: dict[str, Any]) -> list[str]:
    """What didn't match the answer key (empty: all good)."""
    misses = []
    for field in ("title", "servings", "total_minutes"):
        if field in key and result.get(field) != key[field]:
            misses.append(f"{field}: got {result.get(field)!r}, expected {key[field]!r}")
    if "lines" in key and len(result.get("lines", [])) != key["lines"]:
        misses.append(f"lines: got {len(result.get('lines', []))}, expected {key['lines']}")
    return misses


def show(result: dict[str, Any], misses: list[str] | None) -> None:
    print(f"\n── {result['url']}")
    if "error" in result:
        print(f"   ✗ {result['error']}")
        return
    if result["final_url"] != result["url"]:
        print(f"   → redirected to {result['final_url']}")
    print(f"   title     {result['title']}")
    print(f"   servings  {result['servings']}   minutes {result['total_minutes']}")
    print(f"   course    {result['course']} (a guess)   cuisine {result['cuisine']}")
    if result["more_recipes"]:
        print("   ⚠ more than one recipe on the page: took the first")
    lines = result["lines"]
    for line in lines:
        target = line["ingredient"] or "— Not linked"
        print(f"   {'·' if not line['not_linked'] else '?'} {line['raw'][:60]:<60} {target}")
    not_linked = sum(line["not_linked"] for line in lines)
    print(f"   {len(lines)} lines, {not_linked} Not linked")
    if misses is not None:
        print("   ✓ matches the answer key" if not misses else "   ✗ " + "; ".join(misses))


async def main(urls: list[str], keys: dict[str, dict[str, Any]]) -> int:
    engine = make_engine(settings.database_url)  # dev: read-only use, starters and cuisines
    async with make_sessionmaker(engine)() as session:
        index = await index_from_db(session)
        cuisines = await recipes.cuisines(session, uuid.uuid4())  # Seed Recipes' cuisines
    await engine.dispose()

    fetcher = SafeFetcher()
    results, failed = [], 0
    for url in urls:
        result = await run_one(url, fetcher, index, cuisines)
        misses = grade(result, keys[url]) if url in keys else None
        failed += "error" in result or bool(misses)
        results.append(result | ({"misses": misses} if misses is not None else {}))
        show(result, misses)

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"link_import-{datetime.now(UTC):%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\n{len(urls) - failed}/{len(urls)} OK. Saved {out.relative_to(HERE.parent)}")
    return 1 if failed else 0


def cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("urls", nargs="*", help="links to recipe pages")
    parser.add_argument("--keyed", action="store_true", help=f"also run the links in {KEYS.name}")
    args = parser.parse_args()
    keys: dict[str, dict[str, Any]] = {}
    if args.keyed and KEYS.exists():
        for line in KEYS.read_text().splitlines():
            if line.strip():
                key = json.loads(line)
                keys[key["url"]] = key
    urls = list(dict.fromkeys([*args.urls, *keys]))  # in order, no repeats
    if not urls:
        parser.error("give at least one link, or --keyed with links in link_import.jsonl")
    return asyncio.run(main(urls, keys))


if __name__ == "__main__":
    sys.exit(cli())
