"""Reading a recipe into a draft for the review screen (slice 4d: the Paste and Link doors).

Link: plain code reads the page's schema.org data (app.services.recipe_jsonld); no
model ever reads a web page. Paste:

One model call turns messy text into fields (`RecipeReader`, in app.llm). Then plain
code takes over, and trusts the answer only as far as it can check it:

- every value is cleaned to our rules (one line, lengths, sensible numbers), because a
  structured output guarantees the shape of the answer, not that the values are sensible
- every ingredient line must appear in the pasted text, word for word, or it's marked
  "Check": the model may only copy lines, never write them
- lines are matched to Ingredients by our own matcher, never by the model

Nothing is stored. The Member fixes the draft on the review screen and saves it through
app.services.imported_recipes, the same as a typed recipe.
"""

import unicodedata
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors
from app.llm_costs import Usage
from app.models import Course, RecipeIngredient
from app.schemas import MAX_METHOD_STEPS, MAX_RECIPE_LINES, ImportedLineIn
from app.services import imported_recipes, recipe_jsonld, recipes
from app.text import clean_line
from app.web_fetch import Page, check_url


class RecipeReading(BaseModel):
    """The shape the model must answer in (a structured output)."""

    found_recipe: bool  # false: the text isn't a recipe
    more_recipes: bool  # the text holds more than one; only the first was read
    title: str
    servings: int | None
    total_minutes: int | None
    course: Course  # a guess: the review screen pre-selects it and says so
    cuisine: str | None  # one of the cuisines it was given, or null
    ingredient_lines: list[str]  # copied exactly as written
    method: list[str]


class PageFetcher(Protocol):
    async def fetch(self, url: str) -> Page: ...


class RecipeReader(Protocol):
    async def read(
        self, text: str, cuisines: Sequence[str]
    ) -> tuple[RecipeReading | None, Usage]: ...


@dataclass(frozen=True)
class Draft:
    title: str
    servings: int | None
    total_minutes: int | None
    course: Course
    cuisine: str | None
    lines: list[RecipeIngredient]  # read and matched, not saved
    check: list[bool]  # per line: True = not found word for word in the text
    method: list[str] | None
    more_recipes: bool
    usage: Usage | None  # for the daily token budget (step 7); None: no model was used
    source_url: str | None = None


# --- Cleaning and checking (pure) ---------------------------------------------------


def _comparable(text: str) -> str:
    # NFKC folds look-alike characters together (full-width digits, "ﬁ"); casefold is
    # lower-case for every language. Spacing is ignored; every other character counts.
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def appears_in(line: str, text: str) -> bool:
    """Is this line in the text, word for word (ignoring case and spacing)?

    Strict on purpose. "500 g" for "500g" fails, and that's fine: it only adds a
    "Check" mark for a person to look at. What it must never do is pass a line the
    model made up ("50 saffron threads"), and a strict check can't.
    """
    wanted = _comparable(line)
    return bool(wanted) and wanted in _comparable(text)


def _in_range(value: int | None, high: int) -> int | None:
    return value if value is not None and 0 < value <= high else None


# --- The pipeline ----------------------------------------------------------------------


async def from_paste(
    session: AsyncSession,
    household_id: uuid.UUID,
    reader: RecipeReader,
    text: str,
) -> Draft:
    text = text.strip()
    known = await recipes.cuisines(session, household_id)
    reading, usage = await reader.read(text, known)
    if reading is None:
        raise errors.Unavailable(
            "Sweep couldn't read that recipe just now. Try again, or type it in."
        )
    title = clean_line(reading.title, 200)
    lines = [clean_line(line, 300) for line in reading.ingredient_lines]
    lines = [line for line in lines if line][:MAX_RECIPE_LINES]
    if not reading.found_recipe or not title or not lines:
        raise errors.InvalidInput(
            "That doesn't look like a recipe. Paste the title, ingredients and method."
        )

    matched = await imported_recipes.read_lines(
        session, household_id, [ImportedLineIn(raw_text=line) for line in lines]
    )
    method = [step.strip()[:2000] for step in reading.method if step.strip()][:MAX_METHOD_STEPS]
    cuisine = reading.cuisine.strip().lower() if reading.cuisine else None
    return Draft(
        title=title,
        servings=_in_range(reading.servings, 50),
        total_minutes=_in_range(reading.total_minutes, 1440),
        course=reading.course,
        cuisine=cuisine if cuisine in known else None,
        lines=matched,
        check=[not appears_in(line, text) for line in lines],
        method=method or None,
        more_recipes=reading.more_recipes,
        usage=usage,
    )


async def from_link(
    session: AsyncSession,
    household_id: uuid.UUID,
    fetcher: PageFetcher,
    url: str,
) -> Draft:
    """The facts from the page's own recipe data, and where it came from. No method:
    that stays on the site. No model either, so nothing on the page can instruct one."""
    try:
        url = check_url(url)  # before any fetcher sees it (the real one checks again)
    except ValueError as error:
        raise errors.InvalidInput(str(error)) from error
    page = await fetcher.fetch(url)
    found = recipe_jsonld.read_recipe(page.html, await recipes.cuisines(session, household_id))
    if found is None:
        raise errors.InvalidInput(
            "We couldn't find a recipe on that page. Paste the recipe text instead."
        )
    lines = await imported_recipes.read_lines(
        session, household_id, [ImportedLineIn(raw_text=line) for line in found.ingredient_lines]
    )
    return Draft(
        title=found.title,
        servings=found.servings,
        total_minutes=found.total_minutes,
        course=found.course,
        cuisine=found.cuisine,
        lines=lines,
        check=[False] * len(lines),  # the site's own data, copied by code: nothing to check
        method=None,
        more_recipes=found.more_recipes,
        usage=None,
        source_url=page.url,
    )
