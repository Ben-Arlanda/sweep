"""Reading a recipe's facts from the schema.org data a page embeds (the Link door).

Recipe sites put a JSON block in their pages for search engines:
<script type="application/ld+json">{"@type": "Recipe", "name": …, "recipeIngredient": […]}
This reads that block with plain code (no model), and keeps only the facts: title,
servings, time, Course hint, cuisine and ingredient lines. The method stays on the
site (plan: "Method on example.com").

Real pages are messy, so every value is read defensively. A value we can't read
becomes None for the Member to fill in, never a guess.
"""

import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from app.models import Course
from app.schemas import MAX_RECIPE_LINES
from app.text import clean_line

MAX_BLOCKS = 20  # JSON-LD blocks read per page
MAX_DEPTH = 6  # how deep into nested objects we look for a Recipe


@dataclass(frozen=True)
class LinkedRecipe:
    title: str
    servings: int | None
    total_minutes: int | None
    course: Course
    cuisine: str | None
    ingredient_lines: list[str]
    more_recipes: bool


class _LdScripts(HTMLParser):
    """Collects the text of every <script type="application/ld+json">. The standard
    library parser treats script contents as raw text, so nothing inside runs or nests."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._current: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        kind = (dict(attrs).get("type") or "").strip().lower()
        if tag == "script" and kind == "application/ld+json" and len(self.blocks) < MAX_BLOCKS:
            self._current = []

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._current is not None:
            self.blocks.append("".join(self._current))
            self._current = None


def _is_recipe(node: dict[str, Any]) -> bool:
    kinds = node.get("@type")
    kinds = kinds if isinstance(kinds, list) else [kinds]
    # "Recipe", "schema:Recipe" and "https://schema.org/Recipe" all mean the same.
    return any(isinstance(k, str) and re.split(r"[/:]", k)[-1] == "Recipe" for k in kinds)


def _recipes(node: Any, depth: int = 0) -> list[dict[str, Any]]:
    if depth > MAX_DEPTH:
        return []
    if isinstance(node, list):
        return [r for item in node for r in _recipes(item, depth + 1)]
    if not isinstance(node, dict):
        return []
    if _is_recipe(node):
        return [node]
    found = []
    for key in ("@graph", "mainEntity", "mainEntityOfPage", "itemListElement", "item"):
        found += _recipes(node.get(key), depth + 1)
    return found


def _text(value: Any) -> str:
    """A string field, which sites also send as a list or an object with a name."""
    if isinstance(value, list):
        value = next((v for v in value if isinstance(v, str | dict)), "")
    if isinstance(value, dict):
        value = value.get("name") or value.get("@value") or ""
    if not isinstance(value, str):
        return ""
    return re.sub(r"<[^>]*>", " ", html.unescape(value))


def _servings(value: Any) -> int | None:
    for item in value if isinstance(value, list) else [value]:
        if isinstance(item, int) and not isinstance(item, bool):
            number = item
        elif isinstance(item, str) and (match := re.search(r"\d+", item)):
            number = int(match.group())
        else:
            continue
        return number if 0 < number <= 50 else None
    return None


_DURATION = re.compile(
    r"P(?:(?P<d>\d+)D)?(?:T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+(?:\.\d+)?)S)?)?"
)


def minutes(value: Any) -> int | None:
    """An ISO 8601 duration ("PT1H30M") in whole minutes, or None."""
    match = _DURATION.fullmatch(value.strip()) if isinstance(value, str) else None
    if match is None:
        return None
    parts = {k: float(v) for k, v in match.groupdict().items() if v}
    total = round(
        parts.get("d", 0) * 1440
        + parts.get("h", 0) * 60
        + parts.get("m", 0)
        + parts.get("s", 0) / 60
    )
    return total if 0 < total <= 1440 else None


_COURSES = [  # first match wins; anything else is a main (plans offer mains)
    (Course.DESSERT, ("dessert", "cake", "baking", "biscuit", "cookie", "sweet", "snack")),
    (Course.BREAKFAST, ("breakfast", "brunch")),
    (Course.LUNCH, ("lunch", "sandwich", "wrap")),
    (Course.SIDE, ("side", "salad dressing", "sauce", "condiment")),
]


def _course(value: Any) -> Course:
    words = " ".join(_text(v) for v in (value if isinstance(value, list) else [value])).lower()
    for course, hints in _COURSES:
        if any(hint in words for hint in hints):
            return course
    return Course.MAIN


def _total_minutes(recipe: dict[str, Any]) -> int | None:
    total = minutes(recipe.get("totalTime"))
    if total is not None:
        return total
    parts = [minutes(recipe.get(k)) for k in ("prepTime", "cookTime")]
    known = [p for p in parts if p is not None]
    return sum(known) if known else None


def read_recipe(page: str, cuisines: list[str]) -> LinkedRecipe | None:
    """The first Recipe on the page with a title and ingredient lines, or None."""
    parser = _LdScripts()
    parser.feed(page)
    found: list[dict[str, Any]] = []
    for block in parser.blocks:
        try:
            found += _recipes(json.loads(block, strict=False))
        except (ValueError, RecursionError):
            continue  # one broken block doesn't stop the others
    for n, recipe in enumerate(found):
        title = clean_line(_text(recipe.get("name")), 200)
        raw = recipe.get("recipeIngredient") or recipe.get("ingredients") or []
        lines = [clean_line(_text(line), 300) for line in (raw if isinstance(raw, list) else [])]
        lines = [line for line in lines if line][:MAX_RECIPE_LINES]
        if not title or not lines:
            continue
        cuisine = clean_line(_text(recipe.get("recipeCuisine")), 40).lower()
        return LinkedRecipe(
            title=title,
            servings=_servings(recipe.get("recipeYield")),
            total_minutes=_total_minutes(recipe),
            course=_course(recipe.get("recipeCategory")),
            cuisine=cuisine if cuisine in cuisines else None,
            ingredient_lines=lines,
            more_recipes=len(found) > n + 1,
        )
    return None
