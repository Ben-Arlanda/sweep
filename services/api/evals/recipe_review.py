"""How good is the recipe reviewer? LLM-as-judge, measured before it's trusted.

    uv run python -m evals.recipe_review --llm      # calls the API: about 14 reviews

Without --llm it only checks the dataset loads (free). The dataset (recipe_review.jsonl)
has sound recipes and recipes with one mistake planted on purpose, each labelled with
the kind of mistake. Add your own: a person's labels are the ground truth.

Scores:
- caught: planted mistakes the reviewer flagged. Missing one means a bad recipe could
  reach the library, so this is the one that matters most.
- right kind: of those caught, how many it named correctly (food_safety, quantity...).
- false alarms: sound recipes it flagged anyway. Each one costs a person's time, so a
  reviewer that flags everything is useless even if it "catches" everything.
"""

import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.data.recipes import SeedRecipe
from app.llm import ClaudeRecipeReviewer
from app.services.recipe_review import RecipeReviewer, Review

DATASET = Path(__file__).with_name("recipe_review.jsonl")


@dataclass(frozen=True)
class Case:
    recipe: SeedRecipe
    planted: str | None  # the kind of mistake, or None for a sound recipe
    note: str


def load_cases(path: Path = DATASET) -> list[Case]:
    cases = []
    for line in path.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            cases.append(Case(SeedRecipe(**row["recipe"]), row["planted"], row["note"]))
    return cases


@dataclass(frozen=True)
class Score:
    planted: int
    caught: int
    right_kind: int
    sound: int
    false_alarms: int
    no_answer: int


def score(cases: list[Case], reviews: dict[str, Review | None]) -> Score:
    planted = [c for c in cases if c.planted]
    sound = [c for c in cases if not c.planted]
    caught = [c for c in planted if (r := reviews[c.recipe.slug]) and r.flagged]
    return Score(
        planted=len(planted),
        caught=len(caught),
        right_kind=sum(
            any(i.kind == c.planted for i in reviews[c.recipe.slug].issues)  # type: ignore[union-attr]
            for c in caught
        ),
        sound=len(sound),
        false_alarms=sum(bool((r := reviews[c.recipe.slug]) and r.flagged) for c in sound),
        no_answer=sum(reviews[c.recipe.slug] is None for c in cases),
    )


async def run(reviewer: RecipeReviewer, cases: list[Case]) -> dict[str, Review | None]:
    return {c.recipe.slug: await reviewer.review(c.recipe) for c in cases}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true", help="call the API (costs money)")
    args = parser.parse_args()

    cases = load_cases()
    print(f"{len(cases)} cases: {sum(bool(c.planted) for c in cases)} with a planted mistake")
    if not args.llm:
        print("Not calling the reviewer. Pass --llm to run it (it costs money).")
        return
    if settings.anthropic_api_key is None:
        raise SystemExit("ANTHROPIC_API_KEY is not set")

    reviewer = ClaudeRecipeReviewer(
        settings.anthropic_api_key.get_secret_value(), settings.review_model
    )
    reviews = await run(reviewer, cases)
    for c in cases:
        review = reviews[c.recipe.slug]
        found = (
            "no answer"
            if review is None
            else "; ".join(f"{i.kind}: {i.detail}" for i in review.issues) or "ok"
        )
        print(f"- {c.recipe.slug} [{c.planted or 'sound'}] → {found}")
    s = score(cases, reviews)
    print(
        f"\n{settings.review_model}: caught {s.caught}/{s.planted}, right kind {s.right_kind}"
        f"/{s.caught}, false alarms {s.false_alarms}/{s.sound}, no answer {s.no_answer}"
    )


if __name__ == "__main__":
    asyncio.run(main())
