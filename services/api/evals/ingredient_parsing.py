"""How well do we read messy ingredient lines? Rules alone vs rules + the LLM fallback.

    uv run python -m evals.ingredient_parsing          # rules only: free, offline
    uv run python -m evals.ingredient_parsing --llm    # adds one Claude call (~0.1¢)

The dataset (ingredient_lines.jsonl) is US-style lines from the kind of pages URL import
will see, each labelled with the right answer. It includes lines that must NOT match
(an ingredient we don't stock, a prompt-injection attempt): for those, "no match" is the
correct answer, and a confident wrong match counts as an error.

Scores:
- ingredient: the line was linked to the right Ingredient (or correctly left unlinked).
  This is the one that matters: a wrong link puts the wrong thing on a Shopping List.
- wrong links: linked to an Ingredient, but the wrong one. Should be 0.
- amount: quantity and unit both right, among lines whose ingredient was right.
"""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from app.config import settings
from app.data.ingredients import INGREDIENTS
from app.llm import ClaudeLineParser
from app.services.ingredient_lines import IngredientIndex, LineParser, normalise_lines

DATASET = Path(__file__).with_name("ingredient_lines.jsonl")


def ingredient_ok(expected: str | list[str] | None, got: str | None) -> bool:
    if isinstance(expected, list):
        return got in expected
    return got == expected


async def run(llm: LineParser | None) -> dict[str, Any]:
    cases = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    index = IngredientIndex.from_seed(INGREDIENTS)
    parsed = await normalise_lines([c["text"] for c in cases], index, llm)

    right = wrong_links = amount_right = 0
    misses = []
    for case, line in zip(cases, parsed, strict=True):
        got = line.ingredient.name if line.ingredient else None
        if ingredient_ok(case["ingredient"], got):
            right += 1
            quantity = float(line.quantity) if line.quantity is not None else None
            if (quantity, line.unit) == (case["quantity"], case["unit"]):
                amount_right += 1
            else:
                misses.append(f"  amount  {case['text']!r}: got {quantity} {line.unit}")
        else:
            if got is not None:
                wrong_links += 1
            misses.append(f"  {'WRONG' if got else 'missed'}  {case['text']!r}: got {got}")
    return {
        "cases": len(cases),
        "ingredient": right / len(cases),
        "wrong_links": wrong_links,
        "amount": amount_right / max(right, 1),
        "misses": misses,
    }


def report(name: str, result: dict[str, Any]) -> None:
    print(
        f"{name}: ingredient {result['ingredient']:.0%} · wrong links {result['wrong_links']}"
        f" · amount {result['amount']:.0%}  ({result['cases']} lines)"
    )
    for miss in result["misses"]:
        print(miss)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true", help="also run with the Claude fallback")
    args = parser.parse_args()

    report("rules", await run(None))
    if args.llm:
        if settings.anthropic_api_key is None:
            raise SystemExit("ANTHROPIC_API_KEY is not set")
        llm = ClaudeLineParser(
            settings.anthropic_api_key.get_secret_value(), settings.parsing_model
        )
        print()
        report(f"rules + {settings.parsing_model}", await run(llm))


if __name__ == "__main__":
    asyncio.run(main())
