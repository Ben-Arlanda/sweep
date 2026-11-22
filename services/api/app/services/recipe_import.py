"""Reading a recipe into a draft for the review screen (slice 4d: Paste, Photo, File, Link).

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

import re
import unicodedata
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors, pdf_text
from app.llm_costs import Usage
from app.models import Course, RecipeIngredient
from app.schemas import (
    GROUP_NAME_MAX,
    MAX_METHOD_STEPS,
    MAX_PASTE_CHARS,
    MAX_RECIPE_LINES,
    MAX_SUMMARY,
    ImportedLineIn,
)
from app.services import imported_recipes, recipe_jsonld, recipes
from app.text import clean_line
from app.web_fetch import Page, check_url


class IngredientHeading(BaseModel):
    """An Ingredient Group's heading, by the line it comes before (ADR 0033)."""

    before_line: int  # position in ingredient_lines
    heading: str  # copied as written


class RecipeReading(BaseModel):
    """The shape the model must answer in (a structured output)."""

    found_recipe: bool  # false: the text isn't a recipe
    more_recipes: bool  # the text holds more than one; only the first was read
    title: str
    summary: str | None  # the intro, copied as written, or null
    servings: int | None
    total_minutes: int | None
    course: Course  # a guess: the review screen pre-selects it and says so
    cuisine: str | None  # one of the cuisines it was given, or null
    ingredient_lines: list[str]  # copied exactly as written
    ingredient_headings: list[IngredientHeading] = []  # "Marinade slather:" before line 1
    method: list[str]


MAX_PHOTOS, MAX_PHOTO_BYTES = 3, 5_000_000  # the phone resizes to ~1,600 px first


PhotoType = Literal["image/jpeg", "image/png", "image/webp"]


@dataclass(frozen=True)
class Photo:
    media_type: PhotoType  # from the file's first bytes, never its name or upload type
    data: bytes


def photo_type(data: bytes) -> PhotoType | None:
    """What an image really is, from how the file starts ("magic bytes"). Only the
    types Claude reads; an iPhone's HEIC is turned into JPEG on the phone."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


class PageFetcher(Protocol):
    async def fetch(self, url: str) -> Page: ...


class RecipeReader(Protocol):
    async def read(
        self, text: str, cuisines: Sequence[str], layout: str | None = None
    ) -> tuple[RecipeReading | None, Usage]: ...

    async def read_photos(
        self, photos: Sequence[Photo], cuisines: Sequence[str]
    ) -> tuple[RecipeReading | None, Usage]: ...

    async def read_document(
        self, pdf: bytes, cuisines: Sequence[str]
    ) -> tuple[RecipeReading | None, Usage]: ...


@dataclass(frozen=True)
class Draft:
    title: str
    summary: str | None  # the intro: copied, never written (see _finish)
    servings: int | None
    total_minutes: int | None
    course: Course
    cuisine: str | None
    lines: list[RecipeIngredient]  # read and matched, not saved
    check: list[bool]  # per line as written: True = not found word for word in the text
    method: list[str] | None
    more_recipes: bool
    usage: Usage | None  # for the daily token budget (step 7); None: no model was used
    source_url: str | None = None


# --- Cleaning and checking (pure) ---------------------------------------------------


def _comparable(text: str) -> str:
    # NFKC folds look-alike characters together (full-width digits, "ﬁ"); casefold is
    # lower-case for every language. All spacing is dropped, line breaks too: text from
    # a PDF splits "fillets, skin on" into "fillets ⏎ , skin on". Every other character
    # counts.
    return "".join(unicodedata.normalize("NFKC", text).casefold().split())


def appears_in(line: str, text: str) -> bool:
    """Is this line in the text, character for character (ignoring case and spacing)?

    Strict on purpose. "500 g lamb" for "500g beef" fails, and that's fine: it only
    adds a "Check" mark for a person to look at. What it must never do is pass a line
    the model made up ("50 saffron threads"), and a strict check can't.
    """
    wanted = _comparable(line)
    return bool(wanted) and wanted in _comparable(text)


def _in_range(value: int | None, high: int) -> int | None:
    return value if value is not None and 0 < value <= high else None


def _bare(text: str) -> str:
    """Letters and digits only: "Marinade slather: ▢ 1 tbsp" → "marinadeslather1tbsp"."""
    return "".join(c for c in _comparable(text) if c.isalnum())


def line_groups(
    headings: Sequence[IngredientHeading], lines: Sequence[str], source_text: str | None
) -> list[str | None]:
    """Each line's Ingredient Group (ADR 0033). A heading is kept only if it points at a
    line and, for pasted text, sits right before that line in it: a print-to-PDF's text
    can put every heading above the list, and a wrong group is worse than none. Only
    the start of the line counts ("1 tsp lemon zest"): a PDF's layout text, which has
    the order right, can be missing its light-grey notes ("(1 lemon)")."""
    bare = _bare(source_text) if source_text is not None else None
    starts: dict[int, str] = {}
    for h in headings:
        name = clean_line(h.heading, GROUP_NAME_MAX).rstrip(":").strip()
        if not 0 <= h.before_line < len(lines) or not name or h.before_line in starts:
            continue
        start = re.split(r"[,(]", lines[h.before_line], maxsplit=1)[0]
        if bare is not None and _bare(name + start) not in bare:
            continue
        starts[h.before_line] = name
    out: list[str | None] = []
    for i in range(len(lines)):
        out.append(starts.get(i, out[-1] if out else None))
    return out


# --- The pipeline ----------------------------------------------------------------------


async def from_paste(
    session: AsyncSession,
    household_id: uuid.UUID,
    reader: RecipeReader,
    text: str,
    layout: str | None = None,  # a PDF's text placed by position, for headings
) -> Draft:
    text = text.strip()
    known = await recipes.cuisines(session, household_id)
    reading, usage = await reader.read(text, known, layout)
    # A line not in the text word for word: the model reworded it, or made it up.
    return await _finish(
        session,
        household_id,
        (reading, usage),
        known,
        check=lambda line: not appears_in(line, text),
        not_a_recipe="That doesn't look like a recipe. Paste the title, ingredients and method.",
        source_text=text,
        heading_text=layout,
    )


async def from_photos(
    session: AsyncSession,
    household_id: uuid.UUID,
    reader: RecipeReader,
    photos: Sequence[Photo],
) -> Draft:
    """Read once and never stored: the bytes only live for this request."""
    if not 1 <= len(photos) <= MAX_PHOTOS:
        raise errors.InvalidInput(f"Add 1 to {MAX_PHOTOS} photos of the recipe.")
    known = await recipes.cuisines(session, household_id)
    reading, usage = await reader.read_photos(photos, known)
    # No text to compare against, so every line is for a person to check.
    return await _finish(
        session,
        household_id,
        (reading, usage),
        known,
        check=lambda line: True,
        not_a_recipe="That doesn't look like a recipe. Try a clearer photo, or paste the text.",
    )


# Less text than this is a scan with a stray caption ("Scanned by CamScanner", a page
# number), not a recipe's text. A short recipe card still has more.
MIN_PDF_TEXT = 40  # characters, not counting spaces


def paste_text_from_pdf(contents: pdf_text.PdfContents) -> str | None:
    """The text a PDF sends down the Paste path, or None for a scan (no text layer).
    The eval calls this too, so it grades what the app really does."""
    text = pdf_text.rejoin_split_lines(contents.text.strip())
    return text[:MAX_PASTE_CHARS] if len("".join(text.split())) >= MIN_PDF_TEXT else None


async def from_pdf(
    session: AsyncSession,
    household_id: uuid.UUID,
    reader: RecipeReader,
    data: bytes,
) -> Draft:
    """Read once and never stored. A PDF with text takes the Paste path (every line
    checked against that text); a scanned one goes to the model as a document."""
    contents = await pdf_text.read_pdf(data)
    text = paste_text_from_pdf(contents)
    if text is not None:
        layout = contents.layout_text[:MAX_PASTE_CHARS]
        return await from_paste(session, household_id, reader, text, layout)
    known = await recipes.cuisines(session, household_id)
    reading, usage = await reader.read_document(contents.first_pages, known)
    return await _finish(
        session,
        household_id,
        (reading, usage),
        known,
        check=lambda line: True,  # read from page images: a person checks every line
        not_a_recipe="That doesn't look like a recipe. Try another file, or paste the text.",
    )


async def _finish(
    session: AsyncSession,
    household_id: uuid.UUID,
    answer: tuple[RecipeReading | None, Usage],
    known: list[str],
    *,
    check: Callable[[str], bool],  # per line: True = mark it "Check"
    not_a_recipe: str,
    source_text: str | None = None,  # pasted text; None for images
    heading_text: str | None = None,  # where headings are checked, if not source_text
) -> Draft:
    """What every door that uses the model shares, once it has answered."""
    reading, usage = answer
    if reading is None:
        raise errors.Unavailable(
            "Sweep couldn't read that recipe just now. Try again, or type it in."
        )
    title = clean_line(reading.title, 200)
    read = [clean_line(line, 300) for line in reading.ingredient_lines]
    groups = line_groups(reading.ingredient_headings, read, heading_text or source_text)
    kept = [(line, group) for line, group in zip(read, groups, strict=True) if line]
    kept = kept[:MAX_RECIPE_LINES]
    lines = [line for line, _ in kept]
    if not reading.found_recipe or not title or not lines:
        raise errors.InvalidInput(not_a_recipe)

    matched = await imported_recipes.read_lines(
        session,
        household_id,
        [ImportedLineIn(raw_text=line, group_name=group) for line, group in kept],
    )
    method = [step.strip()[:2000] for step in reading.method if step.strip()][:MAX_METHOD_STEPS]
    cuisine = reading.cuisine.strip().lower() if reading.cuisine else None
    # Copied, never written: a description that isn't in pasted text is dropped. From
    # an image there's nothing to compare, so the review screen shows it to a person.
    summary = clean_line(reading.summary or "", MAX_SUMMARY) or None
    if summary and source_text is not None and not appears_in(summary, source_text):
        summary = None
    return Draft(
        title=title,
        summary=summary,
        servings=_in_range(reading.servings, 50),
        total_minutes=_in_range(reading.total_minutes, 1440),
        course=reading.course,
        cuisine=cuisine if cuisine in known else None,
        lines=matched,
        check=[check(line) for line in lines],
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
        summary=None,  # facts only from a website (ADR 0020): its writing stays there
        servings=found.servings,
        total_minutes=found.total_minutes,
        course=found.course,
        cuisine=found.cuisine,
        lines=lines,
        check=[False] * len(found.ingredient_lines),  # the site's data, copied by code
        method=None,
        more_recipes=found.more_recipes,
        usage=None,
        source_url=page.url,
    )
