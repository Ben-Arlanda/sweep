"""Turning a recipe's ingredient lines ("1½ cups plain flour, sifted") into structured data.

Two passes, cheapest and most predictable first:

1. **Rules** (`parse_line`): read the amount, the unit and the name, then look the name
   up in the Ingredient list (exact name, alias, simple plurals). No guessing.
2. **LLM fallback** (`normalise_lines` with a `LineParser`): only for lines the rules
   couldn't match. The model may only pick from our Ingredient names and our units,
   and our code (not the model) does every unit conversion.

Lines nothing could match are kept with `needs_review` set, never silently dropped or
linked to a near-miss. A wrong link would put the wrong thing on a Shopping List.
"""

import re
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Protocol

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.ingredients import SeedIngredient
from app.models import Ingredient, IngredientAlias, ParseMethod
from app.services.ingredients import normalise, variants
from app.units import UNITS, convert


@dataclass(frozen=True)
class KnownIngredient:
    name: str
    default_unit: str
    grams_per_ml: Decimal | None


class IngredientIndex:
    """Every Ingredient name and alias, held in memory for fast, repeatable lookups."""

    def __init__(self, entries: Iterable[tuple[KnownIngredient, Iterable[str]]]) -> None:
        self._by_term: dict[str, KnownIngredient] = {}
        self._by_name: dict[str, KnownIngredient] = {}
        for ingredient, aliases in entries:
            self._by_name[ingredient.name] = ingredient
            for term in (ingredient.name, *aliases):
                self._by_term[normalise(term)] = ingredient

    @classmethod
    def from_seed(cls, seeds: Iterable[SeedIngredient]) -> "IngredientIndex":
        return cls(
            (KnownIngredient(s.name, s.default_unit, s.grams_per_ml), s.aliases) for s in seeds
        )

    @property
    def names(self) -> list[str]:
        return sorted(self._by_name)

    def by_name(self, name: str) -> KnownIngredient | None:
        """The Ingredient with exactly this canonical name (used to check LLM answers)."""
        return self._by_name.get(name)

    def lookup(self, text: str) -> KnownIngredient | None:
        name = core_name(text)
        if not name:
            return None
        for candidate in variants(name):
            if candidate in self._by_term:
                return self._by_term[candidate]
        return None


# Recipe unit words → the one spelling we store. Units in app.units.UNITS convert;
# the rest ("clove", "pinch") are kept as written but have no fixed size.
UNIT_WORDS: dict[str, str] = {
    **{u: u for u in ("g", "kg", "ml", "l", "cup", "tbsp", "tsp", "bunch", "head", "lb", "oz")},
    **dict.fromkeys(("lbs", "pound", "pounds"), "lb"),
    **dict.fromkeys(("ounce", "ounces"), "oz"),
    **dict.fromkeys(("gram", "grams", "gm", "gms"), "g"),  # "gm": common in Australia
    **dict.fromkeys(("kilo", "kilos", "kilogram", "kilograms"), "kg"),
    **dict.fromkeys(("millilitre", "millilitres", "milliliter", "milliliters"), "ml"),
    **dict.fromkeys(("litre", "litres", "liter", "liters"), "l"),
    "cups": "cup",
    **dict.fromkeys(("tablespoon", "tablespoons", "tbs", "tbsps", "tbl"), "tbsp"),
    **dict.fromkeys(("teaspoon", "teaspoons", "tsps"), "tsp"),
    **dict.fromkeys(("bunches",), "bunch"),
    "heads": "head",
    **dict.fromkeys(("clove", "cloves"), "clove"),
    **dict.fromkeys(("pinch", "pinches"), "pinch"),
    **dict.fromkeys(("handful", "handfuls"), "handful"),
    **dict.fromkeys(("slice", "slices"), "slice"),
    **dict.fromkeys(("sprig", "sprigs"), "sprig"),
    **dict.fromkeys(("stalk", "stalks"), "stalk"),
    **dict.fromkeys(("sheet", "sheets"), "sheet"),
    **dict.fromkeys(("rasher", "rashers"), "rasher"),
    **dict.fromkeys(("can", "cans", "tin", "tins"), "can"),
    **dict.fromkeys(("stick", "sticks"), "stick"),
    **dict.fromkeys(("loaf", "loaves"), "loaf"),
}
# Measures that can come *after* the name: "3 garlic cloves", "4 lettuce leaves".
TRAILING_MEASURES = {"clove": "clove", "cloves": "clove", "leaf": "leaf", "leaves": "leaf"}
STORED_UNITS = sorted({*UNIT_WORDS.values(), *TRAILING_MEASURES.values()})
# Words that describe the thing but aren't part of its name.
DESCRIPTORS = {"large", "small", "medium", "fresh", "ripe", "boiling", "cold", "warm", "hot"}
# Container words left in front of the name after a weight: "400 g can chickpeas".
CONTAINERS = {"can", "cans", "tin", "tins", "jar", "jars", "packet", "packets", "of"}
# "4 cups cooked rice": the Ingredient is rice, but the amount isn't an amount you'd buy.
PREPARED = {"cooked", "leftover"}
# Things recipes list but nobody shops for.
NOT_SHOPPED = {"water", "ice", "ice cubes"}
# For the second look only (see _second_look). Preparation, which recipe websites
# often write without a comma ("1 onion finely chopped")...
PREP_WORDS = {
    *("chopped", "diced", "sliced", "crushed", "grated", "minced", "peeled", "zested"),
    *("juiced", "halved", "quartered", "torn", "trimmed", "drained", "rinsed", "shredded"),
    *("cut", "cleaned", "softened", "melted", "beaten", "deseeded", "picked", "washed"),
    *("finely", "roughly", "thinly", "coarsely", "freshly"),
}
# ...and loose words in front of the name: "½ a lemon", "handful of ice", "frozen".
# Not plain DESCRIPTORS: "frozen peas" is a starter, and the first look must find it.
LOOSE_WORDS = {"a", "an", "and", "of", "handful", "handfuls", "pinch", "knob", "splash", "dash"}
LOOSE_WORDS |= {"frozen", "chilled", "mixed"}  # "mixed herbs" is found by the first look


def core_name(text: str) -> str:
    """Normalised, without leading descriptors: "Large  Onion" → "onion"."""
    words = normalise(text).split(" ")
    while words and words[0] in DESCRIPTORS:
        words = words[1:]
    return " ".join(words)


_FRACTIONS = {"½": "1/2", "⅓": "1/3", "⅔": "2/3", "¼": "1/4", "¾": "3/4", "⅛": "1/8"}
# Fractions first, or "1/2" would match as just "1".
_NUMBER = r"\d+/\d+|\d+(?:[.,]\d+)?(?:\s+\d+/\d+)?"
_AMOUNT = re.compile(
    rf"^(?:(?P<times>\d+)\s*x\s+)?(?P<qty>{_NUMBER})(?:\s*(?:-|–|to)\s*(?P<upper>{_NUMBER}))?"
)


@dataclass(frozen=True)
class ParsedLine:
    raw_text: str
    name: str  # what the line called the thing, after removing amount, unit and notes
    quantity: Decimal | None
    unit: str | None
    note: str | None
    optional: bool
    ingredient: KnownIngredient | None
    method: ParseMethod
    prepared: bool = False  # the amount is of the cooked thing, not what you'd buy

    @property
    def needs_review(self) -> bool:
        return self.ingredient is None and core_name(self.name) not in NOT_SHOPPED

    @property
    def base_quantity(self) -> Decimal | None:
        """The amount in the Ingredient's own unit, or None if that can't be done honestly."""
        if self.ingredient is None or self.quantity is None or self.prepared:
            return None
        if self.unit is not None and self.unit not in UNITS:
            return None  # "3 cloves", "a pinch": real units, but no fixed size
        amount = convert(
            self.quantity, self.unit, self.ingredient.default_unit, self.ingredient.grams_per_ml
        )
        return None if amount is None else amount.normalize() + 0  # 40.000 → 40


def _number(text: str) -> Decimal:
    whole, _, fraction = text.replace(",", ".").partition(" ")
    if "/" in whole:
        whole, fraction = "0", whole
    value = Decimal(whole)
    if fraction:
        f = Fraction(fraction)
        value += Decimal(f.numerator) / Decimal(f.denominator)
    return value.quantize(Decimal("0.001")).normalize() + 0


def parse_line(text: str, index: IngredientIndex) -> ParsedLine:
    raw = text.strip()
    work = raw
    for symbol, fraction in _FRACTIONS.items():  # "1½" → "1 1/2"
        work = re.sub(rf"(\d){symbol}", rf"\1 {fraction}", work).replace(symbol, fraction)

    notes = [n.strip() for n in re.findall(r"\(([^)]*)\)", work)]
    work = re.sub(r"\([^)]*\)", " ", work)
    head, _, after_comma = work.partition(",")
    if after_comma.strip():
        notes.insert(0, after_comma.strip())
    optional = any(n.lower() == "optional" for n in notes)
    notes = [n for n in notes if n and n.lower() != "optional"]

    quantity, unit = None, None
    head = head.strip()
    amount = _AMOUNT.match(head)
    if amount is not None:
        try:
            quantity = _number(amount["upper"] or amount["qty"])  # a range: buy for the top
            if amount["times"]:
                quantity *= int(amount["times"])
        except (InvalidOperation, ValueError, ZeroDivisionError):
            quantity = None
        if quantity is not None:
            head = head[amount.end() :].strip()
            # "500g" leaves "g beef mince"; "500 g" leaves the same.
            first, _, rest = head.partition(" ")
            if first.lower().rstrip(".") in UNIT_WORDS and rest.strip():
                unit, head = UNIT_WORDS[first.lower().rstrip(".")], rest.strip()
            words = head.split(" ")
            while len(words) > 1 and words[0].lower() in CONTAINERS:
                words = words[1:]
            # "3 garlic cloves": the measure comes after the name. Only take it off if
            # what's left is an Ingredient ("2 bay leaves" must stay bay leaves), and
            # take it off even if the whole thing is an alias: 3 cloves isn't 3 bulbs.
            trailing = TRAILING_MEASURES.get(words[-1].lower())
            if unit is None and trailing and len(words) > 1:
                if index.lookup(" ".join(words[:-1])) is not None:
                    unit, words = trailing, words[:-1]
            head = " ".join(words)

    head = head.strip()
    ingredient, prepared = index.lookup(head), False
    if ingredient is None:  # "cooked rice" → rice, with an amount we can't use
        words = core_name(head).split(" ")
        if len(words) > 1 and words[0] in PREPARED:
            ingredient = index.lookup(" ".join(words[1:]))
            prepared = ingredient is not None
    if ingredient is None:
        second = _second_look(head, index, can_take_unit=quantity is not None and unit is None)
        if second is not None:
            head, ingredient, extra_note, trailing_unit = second
            unit = trailing_unit or unit
            if extra_note:
                notes.insert(0, extra_note)

    return ParsedLine(
        raw_text=raw,
        name=head,
        quantity=quantity,
        unit=unit,
        note="; ".join(notes) or None,
        optional=optional,
        ingredient=ingredient,
        method=ParseMethod.RULE,
        prepared=prepared,
    )


def _clean_word(word: str) -> str:
    return word.lower().strip(".;:")


def _second_look(
    head: str, index: IngredientIndex, *, can_take_unit: bool
) -> tuple[str, KnownIngredient | None, str | None, str | None] | None:
    """Only for a line the first look couldn't match. Recipe websites write lines our
    rules never saw ("2 garlic cloves crushed", "1 cup frozen spinach or kale"), so try
    simpler readings of the name, still only exact names and aliases: no guessing.

    Returns (name, Ingredient or None for something nobody shops for, note, unit from a
    trailing measure), or None if nothing matched.
    """
    words = head.split()
    leading: list[str] = []  # "finely grated parmesan": the preparation goes to the note
    while words and (
        _clean_word(words[0]) in PREP_WORDS
        or _clean_word(words[0]) in LOOSE_WORDS
        or _clean_word(words[0]) in DESCRIPTORS
    ):
        word = words.pop(0)
        if _clean_word(word) in PREP_WORDS:
            leading.append(word)
    trailing: list[str] = []  # "onion finely chopped", "parmesan to serve"
    for i, word in enumerate(words[1:], start=1):
        if _clean_word(word) in PREP_WORDS or _clean_word(word) == "to":
            words, trailing = words[:i], words[i:]
            break
    note = "; ".join(part for part in (" ".join(leading), " ".join(trailing)) if part) or None

    name = " ".join(words).replace("-", " ")  # "extra-virgin" → "extra virgin"
    candidates = [name]
    if " or " in name:  # "spinach or kale"; "chicken or vegetable stock" → chicken stock
        first, second = name.split(" or ", 1)
        rest = second.split()
        if len(first.split()) == 1 and len(rest) > 1:
            candidates += [f"{first} {' '.join(rest[1:])}", second, first]
        else:
            candidates += [first, second]

    for candidate in candidates:
        parts = candidate.split()
        measure = TRAILING_MEASURES.get(_clean_word(parts[-1])) if len(parts) > 1 else None
        if measure is not None:  # "garlic cloves" → garlic, in cloves (not bulbs)
            found = index.lookup(" ".join(parts[:-1]))
            if found is not None:
                return " ".join(parts[:-1]), found, note, measure if can_take_unit else None
        found = index.lookup(candidate)
        if found is not None:
            return candidate, found, note, None
        if core_name(candidate) in NOT_SHOPPED:
            return candidate, None, note, None
    return None


# --- LLM fallback ---------------------------------------------------------------------


class LineReading(BaseModel):
    """What the model says one line means. Checked against our lists before use."""

    line: int  # position in the list we sent
    quantity: float | None
    unit: str | None
    ingredient: str | None  # must be one of our Ingredient names, or None
    note: str | None


class LineParser(Protocol):
    """Anything that can read lines the rules couldn't. The real one calls Claude."""

    async def read_lines(
        self, lines: Sequence[str], ingredient_names: Sequence[str], units: Sequence[str]
    ) -> list[LineReading]: ...


def _apply_reading(line: ParsedLine, reading: LineReading, index: IngredientIndex) -> ParsedLine:
    ingredient = index.by_name(reading.ingredient) if reading.ingredient else None
    if ingredient is None:
        return line  # the model didn't name one of ours: keep it flagged for review
    unit = reading.unit if reading.unit in STORED_UNITS else None
    quantity = None
    if reading.quantity is not None and reading.quantity > 0:
        quantity = Decimal(str(reading.quantity)).quantize(Decimal("0.001")).normalize() + 0
    return replace(
        line,
        quantity=quantity,
        unit=unit,
        note=reading.note or line.note,
        ingredient=ingredient,
        method=ParseMethod.LLM,
    )


async def normalise_lines(
    lines: Sequence[str], index: IngredientIndex, llm: LineParser | None = None
) -> list[ParsedLine]:
    """Rules for every line; then, if given an LLM, one call for the lines still unmatched."""
    parsed = [parse_line(text, index) for text in lines]
    todo = [i for i, line in enumerate(parsed) if line.needs_review]
    if llm is None or not todo:
        return parsed
    readings = await llm.read_lines([parsed[i].raw_text for i in todo], index.names, STORED_UNITS)
    for reading in readings:
        if 0 <= reading.line < len(todo):
            i = todo[reading.line]
            parsed[i] = _apply_reading(parsed[i], reading, index)
    return parsed


async def index_from_db(session: AsyncSession) -> IngredientIndex:
    """Today's starter Ingredients and aliases, from the database. Seed Recipes may only
    use starters (ADR 0012), so Household Ingredients are never in this index."""
    ingredients = (
        (await session.execute(select(Ingredient).where(Ingredient.household_id.is_(None))))
        .scalars()
        .all()
    )
    aliases: dict[uuid.UUID, list[str]] = {}
    for alias, ingredient_id in await session.execute(
        select(IngredientAlias.alias, IngredientAlias.ingredient_id)
    ):
        aliases.setdefault(ingredient_id, []).append(alias)
    return IngredientIndex(
        (KnownIngredient(i.name, i.default_unit, i.grams_per_ml), aliases.get(i.id, []))
        for i in ingredients
    )
