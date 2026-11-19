"""Recipe Images for Seed Recipes (ADR 0027): the credit record and where the files live.

`recipe_images.json` is written by `scripts/recipe_images.py write` and committed with
the WebP files. One record per recipe that has an approved, openly licensed photo.
"""

import json
from pathlib import Path

from pydantic import BaseModel, Field

HERE = Path(__file__).parent
RECORDS = HERE / "recipe_images.json"
FILES = HERE.parent / "static" / "recipes"
URL_PATH = "/static/recipes"
SIZES = {"hero": (960, 70_000), "thumb": (360, 15_000)}  # width, most bytes
ALLOWED = ("CC0 1.0", "Public Domain", "CC BY", "CC BY-SA")  # never NC or ND


class RecipeImage(BaseModel):
    slug: str
    author: str = Field(max_length=200)
    licence: str = Field(max_length=40)
    licence_url: str | None
    source_url: str  # the photo's page: where the credit links
    seen: str  # the vision check's description, kept with the credit
    dish: str  # "yes" or "close"


def file_name(slug: str, size: str) -> str:
    return f"{slug}-{SIZES[size][0]}.webp"


def load_recipe_images() -> list[RecipeImage]:
    if not RECORDS.exists():
        return []
    return [RecipeImage.model_validate(r) for r in json.loads(RECORDS.read_text())]


def as_stored(image: RecipeImage) -> dict[str, str | None]:
    """What `recipes.image` holds: the files' base name and the credit."""
    return {
        "file": image.slug,
        "author": image.author,
        "licence": image.licence,
        "licence_url": image.licence_url,
        "source_url": image.source_url,
    }
