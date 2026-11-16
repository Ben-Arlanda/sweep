"""Reading a pasted recipe into a draft for the review screen (slice 4d, the Paste door).

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
from app.schemas import ImportedLineIn
from app.services import imported_recipes, recipes

MAX_PASTE = 20_000  # characters; about 5 long recipes. Keeps one call cheap.
MAX_LINES, MAX_STEPS = 60, 40  # the same limits Save has (ImportedRecipeIn)


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
    usage: Usage  # for the daily token budget (step 7)


# --- Cleaning and checking (pure) ---------------------------------------------------


def _one_line(text: str, max_length: int) -> str:
    """Any run of whitespace (newlines too) becomes one space; control characters go."""
    text = "".join(" " if unicodedata.category(ch)[0] in "CZ" else ch for ch in text)
    return " ".join(text.split())[:max_length].strip()


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
    title = _one_line(reading.title, 200)
    lines = [_one_line(line, 300) for line in reading.ingredient_lines]
    lines = [line for line in lines if line][:MAX_LINES]
    if not reading.found_recipe or not title or not lines:
        raise errors.InvalidInput(
            "That doesn't look like a recipe. Paste the title, ingredients and method."
        )

    matched = await imported_recipes.read_lines(
        session, household_id, [ImportedLineIn(raw_text=line) for line in lines]
    )
    method = [step.strip()[:2000] for step in reading.method if step.strip()][:MAX_STEPS]
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
