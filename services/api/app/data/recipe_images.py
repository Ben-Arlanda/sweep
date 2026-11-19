"""Recipe Images for Seed Recipes (ADR 0029): stock photos the product owner picked.

`recipe_images.json` is written by `scripts/recipe_images.py apply` and committed. Photos
are shown from the source's own image server ("hotlinked"), as Unsplash's API terms
require, resized there by URL, and always credited to the photographer.
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

RECORDS = Path(__file__).parent / "recipe_images.json"
# Unsplash asks every link back to carry these (API guidelines).
UTM = "utm_source=sweep&utm_medium=referral"
WIDTHS = {"hero": 960, "thumb": 360}
SOURCES = {"unsplash": ("Unsplash", "https://unsplash.com/")}


class RecipeImage(BaseModel):
    slug: str
    source: Literal["unsplash"]
    photo_id: str
    raw_url: str = Field(pattern=r"^https://images\.unsplash\.com/[^\s]+\?[^\s]*ixid=")
    author: str = Field(min_length=1, max_length=200)
    author_url: str = Field(pattern=r"^https://unsplash\.com/@[^\s/?]+$")
    photo_url: str = Field(pattern=r"^https://unsplash\.com/photos/[^\s?]+$")


def with_utm(url: str) -> str:
    return f"{url}{'&' if '?' in url else '?'}{UTM}"


def sized(raw_url: str, width: int) -> str:
    """A 4:3 crop at this width, made by Unsplash's image server. Keeps `ixid`, as asked."""
    return f"{raw_url}&w={width}&h={width * 3 // 4}&fit=crop&crop=entropy&fm=webp&q=70"


def load_recipe_images() -> list[RecipeImage]:
    if not RECORDS.exists():
        return []
    return [RecipeImage.model_validate(r) for r in json.loads(RECORDS.read_text())]


def as_stored(image: RecipeImage) -> dict[str, str]:
    """What `recipes.image` holds."""
    return image.model_dump(exclude={"slug"})
