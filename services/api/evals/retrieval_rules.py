"""Labels for the Retrieval Set's "rule" queries, written as plain code over the Seed
Recipes' lines, so they can be made again for any library (slice 4g). Free.

    uv run python -m evals.retrieval_rules          # rewrite those labels in the file

A rule query judges every Seed Recipe: each one is relevant or not by its rule. The
"hand" queries are pooled and labelled by reading (`evals.retrieval --pool`). The 4g
library has no sweet potato main and no halloumi, so those two queries were dropped.
"""

import json
import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.data.ingredients import INGREDIENTS
from app.data.recipes import SeedRecipe, load_seed_recipes
from app.models import Course
from app.services.ingredient_lines import parse_line
from app.services.recipe_checks import INDEX
from evals.retrieval import QUERIES


@dataclass(frozen=True)
class Card:
    recipe: SeedRecipe
    names: frozenset[str]  # its lines' Ingredient names
    words: str  # title and summary, lower case

    def has(self, *names: str) -> bool:
        return bool(self.names & set(names))

    @property
    def main(self) -> bool:
        return self.recipe.course == Course.MAIN


def card(recipe: SeedRecipe) -> Card:
    lines = [parse_line(text, INDEX) for text in recipe.ingredients]
    names = frozenset(line.ingredient.name for line in lines if line.ingredient)
    return Card(recipe, names, f"{recipe.title} {recipe.summary}".lower())


CHICKEN = (
    *("chicken thigh", "chicken breast", "chicken drumsticks", "chicken wings"),
    *("chicken mince", "whole chicken", "chicken pieces", "barbecue chicken"),
)
PASTA = ("pasta", "lasagne sheets", "cannelloni tubes")
MUSHROOMS = ("mushrooms", "shiitake mushrooms")
COCONUT = ("coconut milk", "coconut cream", "desiccated coconut")
# "curry leaves" season many dishes that aren't curries (upma, dhokla).
CURRY = re.compile(
    r"curry(?! leaves)|masala(?! dosa)|korma|vindaloo|madras|rogan josh|\bdh?al\b|\bw[oa]t\b"
)
SOUP = re.compile(r"\bsoups?\b|chowder|\bbroth\b")
NOT_SOUPS = {"kabocha-nimono", "revithada"}  # simmered in a broth, served without it
# Meat and seafood; tofu shares their category but is neither.
FLESH = {i.name for i in INGREDIENTS if i.category in ("meat", "seafood") and "tofu" not in i.name}

RULES: dict[str, Callable[[Card], bool]] = {
    "ing-01": lambda c: c.main and c.has(*CHICKEN),
    "ing-02": lambda c: c.has("chickpeas"),
    "ing-03": lambda c: c.has("salmon fillet", "smoked salmon"),
    "ing-04": lambda c: c.has("pork mince"),
    "ing-05": lambda c: c.has("tofu", "silken tofu", "tofu puffs"),
    "ing-07": lambda c: c.has("prawns", "cooked prawns"),
    "ing-08": lambda c: c.has("red lentils", "brown lentils", "green lentils"),
    "words-01": lambda c: c.has("eggplant"),
    "words-02": lambda c: c.has("capsicum"),
    "words-03": lambda c: c.has("zucchini"),
    "words-04": lambda c: c.has("coriander") and c.has("limes"),
    "words-05": lambda c: c.main and c.has("beef mince"),
    "words-06": lambda c: c.has("prawns", "cooked prawns"),
    "words-08": lambda c: c.has("chickpeas"),
    "neg-01": lambda c: c.has(*PASTA) and not c.has(*MUSHROOMS),
    "neg-02": lambda c: bool(CURRY.search(c.words)) and not c.has(*COCONUT),
    "neg-03": lambda c: (
        c.recipe.course != Course.DESSERT
        and bool(SOUP.search(c.words))
        and c.recipe.slug not in NOT_SOUPS
        and not c.names & FLESH
    ),
}


def labels(recipes: Sequence[SeedRecipe]) -> dict[str, list[str]]:
    cards = [card(r) for r in recipes]
    return {qid: sorted(c.recipe.slug for c in cards if rule(c)) for qid, rule in RULES.items()}


def main() -> int:
    recipes = load_seed_recipes()
    every = sorted(r.slug for r in recipes)
    found = labels(recipes)
    rows = [json.loads(line) for line in QUERIES.read_text().splitlines() if line.strip()]
    for row in rows:
        if row["id"] in found:
            row |= {"labelled_by": "rule", "relevant": found[row["id"]], "judged": every}
            print(f"{row['id']:9} {len(found[row['id']]):3} relevant  {row['query']}")
    QUERIES.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
