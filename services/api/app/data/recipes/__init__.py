"""Seed Recipes: written for Sweep (ADR 0002), stored as TOML files in this folder.

TOML because it's readable, diff-friendly, and Python reads it with no extra library
(`tomllib`). Each file holds `[[recipe]]` tables; see any file here for the shape.
Ingredient lines are written the way a person would ("1 onion, finely diced"): the
loader parses them with the same rules as everything else, and a test makes sure every
line parses.
"""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

DIR = Path(__file__).parent
LICENCE = "Sweep original"
ATTRIBUTION = "Sweep"


class SeedRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=100)
    title: str = Field(min_length=1, max_length=200)
    cuisine: str = Field(pattern=r"^[a-z-]+$", max_length=40)
    servings: int = Field(gt=0, le=24)
    minutes: int = Field(gt=0, le=24 * 60)
    summary: str = Field(min_length=1, max_length=500)
    ingredients: list[str] = Field(min_length=1)
    method: list[str] = Field(min_length=1)


def load_seed_recipes(directory: Path = DIR) -> list[SeedRecipe]:
    recipes: list[SeedRecipe] = []
    for path in sorted(directory.glob("*.toml")):
        with path.open("rb") as f:
            recipes += [SeedRecipe(**r) for r in tomllib.load(f).get("recipe", [])]
    slugs = [r.slug for r in recipes]
    duplicates = {s for s in slugs if slugs.count(s) > 1}
    if duplicates:
        raise ValueError(f"duplicate Seed Recipe slugs: {sorted(duplicates)}")
    return recipes
