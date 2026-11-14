"""Check every Seed Recipe and show how the library is spread. Free: no API calls.

    uv run python -m app.check_recipes

Exits with 1 if any recipe has a problem, so it can gate a script or a commit.
"""

import sys
from collections import Counter

from app.data.recipes import load_seed_recipes
from app.services.recipe_checks import check_recipes


def band(minutes: int) -> str:
    return next((f"≤{m} min" for m in (20, 30, 45) if minutes <= m), ">45 min")


def main() -> int:
    recipes = load_seed_recipes()
    problems = check_recipes(recipes)

    print(f"{len(recipes)} Seed Recipes")
    print(
        "By cuisine:",
        ", ".join(f"{c} {n}" for c, n in Counter(r.cuisine for r in recipes).most_common()),
    )
    print(
        "By time:",
        ", ".join(f"{b} {n}" for b, n in sorted(Counter(band(r.minutes) for r in recipes).items())),
    )
    for p in problems:
        print(f"  {p.slug}: {p.check}: {p.message}")
    print(f"{len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
