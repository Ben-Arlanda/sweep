"""A recipe's Nutrition per serve, added up from its lines (slice 4h, ADR 0035).

Each Ingredient's values per 100 g come from FSANZ's AUSNUT 2023 (`app/data/nutrition.json`,
built by `scripts.nutrition_data`). An estimate: cooking losses and brands aren't counted.
"""

import json
import re
from collections.abc import Sequence
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

from app.services.ingredient_lines import parse_line
from app.units import UNITS

TABLE_FILE = Path(__file__).parents[1] / "data" / "nutrition.json"
NUTRIENTS = (
    "energy_kj",
    "protein_g",
    "fat_g",
    "saturated_fat_g",
    "carbs_g",
    "sugars_g",
    "fibre_g",
    "sodium_mg",
)
QUIET = {"pinch", "dash", "sprig", "sprigs"}  # too small to matter, too small to mention
MAIN = {"meat", "seafood"}  # missing one of these and the numbers mislead
HEAVY = 0.15  # a missing line over this share of the recipe's weight
FRYING = re.compile(r"deep[- ]?fry|for frying|shallow[- ]?fry", re.IGNORECASE)
FRYING_GRAMS = 180  # about 200 ml: more oil than a recipe eats, so it's for frying
SOAKED_UP = 0.1  # the share of deep-frying oil that ends up in the food (a rough figure)


class Nutrients(BaseModel):
    energy_kj: float
    protein_g: float
    fat_g: float
    saturated_fat_g: float
    carbs_g: float
    sugars_g: float
    fibre_g: float
    sodium_mg: float


class Nutrition(BaseModel):
    available: bool
    per_serve: Nutrients | None  # None when `available` is False
    left_out: list[str]  # lines with amounts we couldn't count


class _Ingredient(Protocol):
    name: str
    category: str
    default_unit: str


class Line(Protocol):
    raw_text: str
    quantity: Decimal | None
    unit: str | None
    base_quantity: Decimal | None
    optional: bool
    needs_review: bool  # False with no Ingredient: water, which counts as nothing

    @property
    def ingredient(self) -> _Ingredient | None: ...


@cache
def load_table() -> dict[str, Any]:
    return json.loads(TABLE_FILE.read_text()) if TABLE_FILE.exists() else {}


def _is_prepared(line: Line) -> bool:
    """ "4 cups cooked rice": the amount is of the cooked thing. The parser decides, as it did."""
    from app.services.recipe_checks import INDEX  # the starters' index; imported late (cycle)

    return parse_line(line.raw_text, INDEX).prepared


def grams_of(line: Line, entry: dict[str, Any]) -> float | None:
    """The line's weight in grams, from its base amount or the Ingredient's own measures."""
    density = entry["grams_per_ml"]
    unit = (line.unit or "each").lower()
    assert line.ingredient is not None and line.quantity is not None
    base = line.ingredient.default_unit
    if line.base_quantity is not None:
        amount = float(line.base_quantity)
        if base == "g":
            return amount
        if base == "ml" and density:
            return amount * float(density)
        if base == "count" and "each" in entry["grams_per"]:
            return amount * float(entry["grams_per"]["each"])
    if unit in entry["grams_per"]:
        return float(line.quantity) * float(entry["grams_per"][unit])
    known = UNITS.get(unit)
    if known and known[0] == "g":
        return float(line.quantity * known[1])
    if known and known[0] == "ml" and density:
        return float(line.quantity * known[1]) * float(density)
    return None


def _rough_grams(line: Line) -> float | None:
    """A missing line's weight, only when its amount says it plainly (taking 1 ml as 1 g)."""
    known = UNITS.get((line.unit or "").lower())
    if line.quantity is None or not known or known[0] == "count":
        return None
    return float(line.quantity * known[1])


def nutrition_per_serve(
    lines: Sequence[Line], servings: int, table: dict[str, Any] | None = None
) -> Nutrition:
    values = table if table is not None else load_table()
    totals = dict.fromkeys(NUTRIENTS, 0.0)
    counted_grams = 0.0
    missing: list[tuple[str, float | None, bool]] = []  # (name, rough grams, a main)
    for line in lines:
        if line.optional or line.quantity is None or (line.unit or "").lower() in QUIET:
            continue
        ing = line.ingredient
        if ing is None and not line.needs_review:
            continue
        entry = values.get(ing.name) if ing else None
        grams = grams_of(line, entry) if entry and not _is_prepared(line) else None
        if entry is None or grams is None:
            name = ing.name if ing else line.raw_text
            missing.append((name, _rough_grams(line), bool(ing and ing.category in MAIN)))
            continue
        if "oil" in ing.name and (grams >= FRYING_GRAMS or FRYING.search(line.raw_text)):  # type: ignore[union-attr]
            grams *= SOAKED_UP
        counted_grams += grams
        for n in NUTRIENTS:
            totals[n] += entry["per_100g"][n] * grams / 100
    left_out = [name for name, _, _ in missing]
    whole = counted_grams + sum(g or 0 for _, g, _ in missing)
    heavy = any(main or (g is not None and g > HEAVY * whole) for _, g, main in missing)
    if heavy or counted_grams == 0:
        return Nutrition(available=False, per_serve=None, left_out=left_out)
    per = Nutrients(**{n: round(v / servings, 1) for n, v in totals.items()})
    return Nutrition(available=True, per_serve=per, left_out=left_out)
