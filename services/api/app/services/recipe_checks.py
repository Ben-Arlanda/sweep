"""Automatic checks for Seed Recipes (slice 4c, ADR 0002).

Plain code, no LLM and no database: fast, free and the same answer every time, so they
can run in CI on every recipe. They catch mistakes that have a clear rule. Judgement
calls ("is this sauce too thin?") are left to the reviewer in `recipe_review`.

1. unparsed:   an ingredient line that matches no Ingredient (we can't shop for it).
2. unlisted:   the method uses an Ingredient the list doesn't have.
3. raw_meat:   raw meat or seafood with no cooking step that has a time or a doneness cue.
4. timing:     one step takes longer than the whole recipe says it does.
5. duplicate:  the same title, or nearly the same ingredients in the same cuisine.
6. diet_claim: the summary says vegetarian or vegan, but an ingredient isn't. A hedged
               note ("vegetarian if the paste is") is fine: it's honest.
7. odd_phrase: "X-free <noun>" where X isn't a diet word ("orange-free greens"). A slip
               the drafting model is prone to; real text says gluten-free, dairy-free...
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.data.ingredients import INGREDIENTS
from app.data.recipes import SeedRecipe
from app.services.ingredient_lines import IngredientIndex, parse_line
from app.services.ingredients import _variants, normalise

INDEX = IngredientIndex.from_seed(INGREDIENTS)
CATEGORY = {i.name: i.category for i in INGREDIENTS}


@dataclass(frozen=True)
class Problem:
    slug: str
    check: str
    message: str


# --- unlisted: every name and alias, longest first, so "rice noodles" isn't "rice" ------

# Aliases too vague to point at one Ingredient when they turn up in a method: "cheese"
# could be any cheese, "pepper" could be black pepper or capsicum.
VAGUE = {"cheese", "pepper", "mince", "steak", "cream", "rolls", "wraps", "stock cube"}

_VAGUE_FORMS = {form for term in VAGUE for form in _variants(term)}  # "roll", "wrap" too

_TERMS: dict[str, str] = {}
for _seed in INGREDIENTS:
    for _term in (_seed.name, *_seed.aliases):
        for _form in _variants(normalise(_term)):
            if _form not in _VAGUE_FORMS:
                _TERMS.setdefault(_form, _seed.name)
_TERM_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in sorted(_TERMS, key=len, reverse=True)) + r")\b"
)


def _mentioned(text: str) -> list[str]:
    """Terms for Ingredients in `text`, longest match first, never overlapping.

    "walnut-sized balls" is a size, not walnuts, so a term right before "-size" is skipped.
    """
    text = normalise(text)
    return [m[1] for m in _TERM_PATTERN.finditer(text) if not text.startswith("-size", m.end())]


# --- raw_meat ----------------------------------------------------------------------

READY_TO_EAT = {"ham", "canned tuna", "cooked prawns", "tofu", "silken tofu", "tofu puffs"}
COOKING = re.compile(
    r"\b(cook|fry|fried|frying|roast|bake|grill|griddle|barbecue|bbq|simmer|braise|stew|"
    r"poach|steam|sear|brown|boil|stir-fry|stir-fried|char|sizzle|toast)\w*",
)
DONE = re.compile(
    r"\b\d+[½¼¾]?(?:[-–]\d+)?\s*(?:minutes?|mins?|hours?|hrs?)\b|cooked through|no longer pink|"
    r"until pink|turns? pink|"
    r"until (?:done|golden|browned|charred|opaque|tender|crisp|cooked)|°c|juices run clear",
)


def _needs_cooking(names: set[str]) -> list[str]:
    return sorted(
        n for n in names if CATEGORY.get(n) in {"meat", "seafood"} and n not in READY_TO_EAT
    )


def _cooked(method: Sequence[str]) -> bool:
    return any(COOKING.search(s.lower()) and DONE.search(s.lower()) for s in method)


# --- diet_claim ------------------------------------------------------------------

# Not meat to look at, but usually made with fish, shrimp or meat stock.
HIDDEN_ANIMAL = {
    "fish sauce",
    "oyster sauce",
    "worcestershire sauce",
    "dashi stock",
    "kimchi",
    "chicken stock",
    "beef stock",
    "stock cubes",
    "green curry paste",
    "red curry paste",
    "laksa paste",
    "tom yum paste",
}
NOT_VEGAN = {"eggs", "honey"}
_PLANT_PROTEIN = {"tofu", "silken tofu", "tofu puffs"}  # filed under "meat" in the aisle
_CLAIM = re.compile(r"\b(vegan|vegetarian)\b", re.IGNORECASE)
_HEDGE = re.compile(r"\b(if|check|without)\b", re.IGNORECASE)


def _diet_problem(summary: str, names: set[str]) -> str | None:
    # Only plain claims count. "Vegetarian if the paste is", "check the label if you're
    # vegetarian" and "vegan without the parmesan" are honest, so they're fine.
    sentences = re.split(r"(?<=[.!?;])\s+", summary)
    claims = {m.lower() for s in sentences if not _HEDGE.search(s) for m in _CLAIM.findall(s)}
    if not claims:
        return None
    meat = {n for n in names if CATEGORY.get(n) in {"meat", "seafood"}} - _PLANT_PROTEIN
    not_vegetarian = sorted(meat | (names & HIDDEN_ANIMAL))
    if not_vegetarian:
        claim = "vegan" if "vegan" in claims else "vegetarian"
        return f"says {claim} but has {', '.join(not_vegetarian)}"
    if "vegan" in claims:
        animal = sorted({n for n in names if CATEGORY.get(n) == "dairy"} | (names & NOT_VEGAN))
        if animal:
            return f"says vegan but has {', '.join(animal)}"
    return None


# --- odd_phrase --------------------------------------------------------------------

_ODD_FREE = re.compile(r"\b(?!(?:gluten|dairy|meat|sugar|nut|egg|fat|salt-reduced)-)(\w+)-free \w+")


def _odd_phrases(r: SeedRecipe) -> list[str]:
    text = " ".join([r.title, r.summary, *r.ingredients, *r.method])
    return [m.group(0) for m in _ODD_FREE.finditer(text)]


# --- timing ------------------------------------------------------------------------

_DURATION = re.compile(r"(\d+)([½¼¾]?)(?:\s*[-–]\s*(\d+))?\s*(hours?|hrs?|minutes?|mins?)\b")
_HALF = {"": 0.0, "½": 0.5, "¼": 0.25, "¾": 0.75}


def _longest_step(method: Sequence[str]) -> int:
    longest = 0
    for step in method:
        total = 0
        for low, part, high, unit in _DURATION.findall(step.lower()):
            amount = int(high) if high else int(low) + _HALF[part]  # "1½ hours" = 1.5
            total += round(amount * 60 if unit.startswith("h") else amount)
        longest = max(longest, total)
    return longest


# --- duplicate ---------------------------------------------------------------------


def _similar(a: set[str], b: set[str]) -> bool:
    """Nearly the same shopping: 85% of the combined ingredients are shared."""
    return bool(a and b) and len(a & b) / len(a | b) >= 0.85


def check_recipes(recipes: Sequence[SeedRecipe]) -> list[Problem]:
    problems: list[Problem] = []
    listed: dict[str, set[str]] = {}

    for r in recipes:
        lines = [parse_line(text, INDEX) for text in r.ingredients]
        names = {line.ingredient.name for line in lines if line.ingredient}
        listed[r.slug] = names
        problems += [
            Problem(r.slug, "unparsed", f"'{line.raw_text}' matches no Ingredient")
            for line in lines
            if line.needs_review
        ]

        # A term is fine if it's a listed Ingredient, or a word inside a listed line
        # ("the rice" when the list says "arborio rice", "the onion" for "red onion").
        written = " ".join(normalise(text) for text in r.ingredients)
        reported: set[str] = set()
        for term in _mentioned(" ".join(r.method)):
            name = _TERMS[term]
            in_lines = any(re.search(rf"\b{re.escape(f)}\b", written) for f in _variants(term))
            if name in names or name in reported or in_lines:
                continue
            reported.add(name)
            problems.append(
                Problem(
                    r.slug, "unlisted", f"the method uses {name}, which isn't in the ingredients"
                )
            )

        uncooked = {line.ingredient.name for line in lines if line.ingredient and not line.prepared}
        raw = _needs_cooking(uncooked)
        if raw and not _cooked(r.method):
            problems.append(
                Problem(
                    r.slug,
                    "raw_meat",
                    f"{', '.join(raw)} needs a cooking step with a time or a doneness cue",
                )
            )

        diet = _diet_problem(r.summary, names)
        if diet:
            problems.append(Problem(r.slug, "diet_claim", diet))

        problems += [
            Problem(r.slug, "odd_phrase", f"'{phrase}' reads like a slip")
            for phrase in _odd_phrases(r)
        ]

        longest = _longest_step(r.method)
        if longest > r.minutes:
            problems.append(
                Problem(
                    r.slug,
                    "timing",
                    f"one step takes {longest} min but the recipe says {r.minutes} min in total",
                )
            )

    seen: dict[str, SeedRecipe] = {}
    checked: list[SeedRecipe] = []
    for r in recipes:
        title = normalise(r.title)
        if title in seen:
            problems.append(Problem(r.slug, "duplicate", f"same title as {seen[title].slug}"))
        else:
            twin = next(
                (
                    o
                    for o in checked
                    if o.cuisine == r.cuisine and _similar(listed[o.slug], listed[r.slug])
                ),
                None,
            )
            if twin is not None:
                problems.append(
                    Problem(r.slug, "duplicate", f"nearly the same ingredients as {twin.slug}")
                )
        seen.setdefault(title, r)
        checked.append(r)
    return problems
