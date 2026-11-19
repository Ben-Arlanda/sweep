"""Seed Recipes: written for Sweep (ADR 0002, ADR 0028), stored as JSON files in this folder.

JSON because a recipe has nested Recipe Stages (TOML made those awkward). Each file is a
list of recipes; see any file here for the shape. Ingredient lines are written the way a
person would ("1 onion, finely diced"): the loader parses them with the same rules as
everything else, and a test makes sure every line parses.

Each recipe has two views of one method: `stages` (the Detailed View) and `method`, 3–6
short steps (the Quick View) that the agent, Adaptations and Kitchen Match read.
"""

import json
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import Course, Difficulty

DIR = Path(__file__).parent
LICENCE = "Sweep original"
ATTRIBUTION = "Sweep"


class RecipeStage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1, max_length=100)
    minutes: int = Field(ge=0, le=24 * 60)
    steps: list[str] = Field(min_length=1)


class SeedRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=100)
    title: str = Field(min_length=1, max_length=200)
    cuisine: str = Field(pattern=r"^[a-z-]+$", max_length=40)
    course: Course
    servings: int = Field(gt=0, le=24)
    prep_minutes: int = Field(ge=0, le=24 * 60)
    cook_minutes: int = Field(ge=0, le=24 * 60)
    difficulty: Difficulty
    summary: str = Field(min_length=1, max_length=500)
    ingredients: list[str] = Field(min_length=1)
    method: list[str] = Field(min_length=1)
    stages: list[RecipeStage] = Field(min_length=1)
    tips: list[str] = []
    variations: list[str] = []
    storage: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _takes_some_time(self) -> Self:
        if self.minutes <= 0:
            raise ValueError("prep_minutes + cook_minutes must be more than 0")
        return self

    @property
    def minutes(self) -> int:
        return self.prep_minutes + self.cook_minutes

    def detailed(self) -> "SeedRecipe":
        """This recipe with its stage steps as the method, so the checks can read the
        Detailed View the same way as the Quick View."""
        return self.model_copy(update={"method": [s for st in self.stages for s in st.steps]})


def load_seed_recipes(directory: Path = DIR) -> list[SeedRecipe]:
    recipes: list[SeedRecipe] = []
    for path in sorted(directory.glob("*.json")):
        recipes += [SeedRecipe.model_validate(r) for r in json.loads(path.read_text())]
    slugs = [r.slug for r in recipes]
    duplicates = {s for s in slugs if slugs.count(s) > 1}
    if duplicates:
        raise ValueError(f"duplicate Seed Recipe slugs: {sorted(duplicates)}")
    return recipes
