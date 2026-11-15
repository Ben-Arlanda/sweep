"""Does Kitchen-first planning (ADR 0013) actually plan from what you have?

    uv run python -m evals.kitchen_first

Offline and free: the real Seed Recipes, parsed by the same rules as the app, against a
few hand-written Kitchens. No database, no embeddings, no model calls.

For each Kitchen it plans 5 dinners two ways:
- Kitchen-first: the top 5 by Kitchen Match (fewest things to buy).
- Kitchen-blind: 5 recipes picked at random, averaged over many draws. That's what a plan
  amounts to when nothing looks at the Kitchen (the agent before 5c, unless the Member
  happened to name ingredients).

Scores (per plan of 5):
- to buy / meal: average missing ingredients per dinner. Lower is better.
- cook now: dinners needing nothing bought. Higher is better.
- Kitchen used: share of the Kitchen's Tracked items that at least one dinner uses.
  Higher is better: the point is to use what you bought.
"""

import random
import uuid
from dataclasses import dataclass
from statistics import mean

from app.data.ingredients import INGREDIENTS
from app.data.recipes import SeedRecipe, load_seed_recipes
from app.services.ingredient_lines import IngredientIndex, parse_line
from app.services.kitchen_match import KitchenSnapshot, Line, Match, match, rank_key

PLAN_SIZE = 5
DRAWS = 300

# Hand-written, typical Australian Kitchens. Names must be starter Ingredient names.
KITCHENS: dict[str, list[str]] = {
    "after a big shop": [
        "chicken thigh",
        "beef mince",
        "pasta",
        "rice",
        "onion",
        "carrots",
        "broccoli",
        "tomatoes",
        "eggs",
        "milk",
        "cheddar cheese",
        "butter",
        "potatoes",
        "lemons",
    ],
    "end of the week": ["rice", "eggs", "onion", "canned tomatoes", "pasta", "frozen peas"],
    "vegetarian": [
        "chickpeas",
        "red lentils",
        "baby spinach",
        "tomatoes",
        "capsicum",
        "rice",
        "eggs",
        "feta",
        "zucchini",
        "onion",
    ],
    "asian pantry": [
        "rice",
        "rice noodles",
        "tofu",
        "bok choy",
        "ginger",
        "spring onions",
        "eggs",
        "chicken thigh",
    ],
    "nearly empty": ["eggs", "bread", "onion"],
}

NAMES = {s.name for s in INGREDIENTS}
STAPLES = {s.name for s in INGREDIENTS if s.is_default_staple}
INDEX = IngredientIndex.from_seed(INGREDIENTS)


def _id(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_OID, name)  # stable fake ids: names are unique


@dataclass(frozen=True)
class Scores:
    to_buy_per_meal: float
    cook_now: float
    kitchen_used: float


@dataclass(frozen=True)
class Result:
    kitchen: str
    first: Scores
    blind: Scores


def recipe_lines(recipe: SeedRecipe) -> list[Line]:
    lines = []
    for text in recipe.ingredients:
        parsed = parse_line(text, INDEX)
        name = parsed.ingredient.name if parsed.ingredient else None
        lines.append(Line(_id(name) if name else None, name, text, parsed.optional))
    return lines


def snapshot(tracked: list[str]) -> KitchenSnapshot:
    unknown = sorted(set(tracked) - NAMES)
    if unknown:
        raise SystemExit(f"Not starter Ingredients: {unknown}")
    ids = frozenset(_id(n) for n in tracked)
    return KitchenSnapshot(
        have=ids | {_id(n) for n in STAPLES}, maybe=frozenset(), tracked=ids, own_names={}
    )


def score(plan: list[Match], tracked: list[str]) -> Scores:
    used = set().union(*(set(m.have) | set(m.maybe) for m in plan)) & set(tracked)
    return Scores(
        to_buy_per_meal=mean(len(m.missing) for m in plan),
        cook_now=sum(1 for m in plan if not m.missing),
        kitchen_used=len(used) / len(tracked),
    )


def evaluate(
    kitchens: dict[str, list[str]], recipes: list[SeedRecipe], seed: int = 0
) -> list[Result]:
    parsed = [(r.title, recipe_lines(r)) for r in recipes]
    rng = random.Random(seed)  # repeatable
    results = []
    for name, tracked in kitchens.items():
        snap = snapshot(tracked)
        matches = [(title, match(lines, snap)) for title, lines in parsed]
        best = sorted(matches, key=lambda tm: rank_key(*tm))[:PLAN_SIZE]
        first = score([m for _, m in best], tracked)
        draws = [
            score([m for _, m in rng.sample(matches, PLAN_SIZE)], tracked) for _ in range(DRAWS)
        ]
        blind = Scores(
            mean(d.to_buy_per_meal for d in draws),
            mean(d.cook_now for d in draws),
            mean(d.kitchen_used for d in draws),
        )
        results.append(Result(name, first, blind))
    return results


def main() -> None:
    recipes = load_seed_recipes()
    print(f"{len(recipes)} Seed Recipes, plans of {PLAN_SIZE} dinners\n")
    header = f"{'Kitchen':<18}{'to buy / meal':>22}{'cook now':>16}{'Kitchen used':>20}"
    print(
        header + "\n" + " " * 18 + f"{'first   blind':>22}{'first  blind':>16}{'first  blind':>20}"
    )
    for r in evaluate(KITCHENS, recipes):
        print(
            f"{r.kitchen:<18}"
            f"{r.first.to_buy_per_meal:>14.1f}{r.blind.to_buy_per_meal:>8.1f}"
            f"{r.first.cook_now:>9.0f}{r.blind.cook_now:>7.1f}"
            f"{r.first.kitchen_used:>13.0%}{r.blind.kitchen_used:>7.0%}"
        )


if __name__ == "__main__":
    main()
