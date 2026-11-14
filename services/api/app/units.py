"""Units and amounts: deterministic, boring, and refuses to guess (ADR 0003).

Every Ingredient has one base unit: grams, millilitres or a count. The Cabinet stores
quantities in that base unit only, so adding "1.5 kg" to "500 g" is plain addition.

Converting between weight and volume needs the Ingredient's density (`grams_per_ml`).
Without it, or for units we don't know ("a bunch"), we return None ("amount unknown")
rather than inventing a number. A Cabinet that is confidently wrong is worse than one
that admits it doesn't know.
"""

import re
from decimal import Decimal
from typing import Literal

BaseUnit = Literal["g", "ml", "count"]

# Lower-cased unit word → (base unit, multiplier into that base unit)
UNITS: dict[str, tuple[BaseUnit, Decimal]] = {
    "g": ("g", Decimal(1)),
    "gram": ("g", Decimal(1)),
    "grams": ("g", Decimal(1)),
    "kg": ("g", Decimal(1000)),
    "kilo": ("g", Decimal(1000)),
    "kilos": ("g", Decimal(1000)),
    "ml": ("ml", Decimal(1)),
    "l": ("ml", Decimal(1000)),
    "litre": ("ml", Decimal(1000)),
    "litres": ("ml", Decimal(1000)),
    "liter": ("ml", Decimal(1000)),
    "liters": ("ml", Decimal(1000)),
    "each": ("count", Decimal(1)),
    "x": ("count", Decimal(1)),
    "pc": ("count", Decimal(1)),
    "pcs": ("count", Decimal(1)),
}

# "500g pasta", "2 kg chicken", "1.5L milk", "6 eggs". The unit may touch the number.
_LEADING_AMOUNT = re.compile(r"^\s*(\d+(?:[.,]\d+)?)(\s*)([a-zA-Z]+)?(.*)$")


def convert(
    quantity: Decimal, unit: str | None, base_unit: str, grams_per_ml: Decimal | None
) -> Decimal | None:
    """`quantity unit` expressed in `base_unit`, or None if that can't be done honestly."""
    source = UNITS.get(unit.lower()) if unit else ("count", Decimal(1))
    if source is None:
        return None
    source_base, factor = source
    amount = quantity * factor
    if source_base == base_unit:
        return amount
    if grams_per_ml is not None and {source_base, base_unit} == {"g", "ml"}:
        return amount * grams_per_ml if source_base == "ml" else amount / grams_per_ml
    return None


def parse_item_text(text: str) -> tuple[str, Decimal | None, str | None]:
    """Split "2 kg chicken thighs" into ("chicken thighs", 2, "kg").

    Only takes a leading number, plus a unit if the next word is one we know. Anything
    else stays in the name ("2 lemons" → 2 of "lemons"). If nothing would be left as
    the name, nothing is parsed.
    """
    match = _LEADING_AMOUNT.match(text)
    if match is None:
        return text, None, None
    number, gap, word, rest = match.groups()
    if word is not None and word.lower() in UNITS:
        name, unit = rest, word.lower()
    elif word is not None and not gap:
        return text, None, None  # "7up": a number glued to a word that isn't a unit
    else:
        name, unit = (word or "") + rest, None
    name = name.strip()
    if not name:
        return text, None, None
    return name, Decimal(number.replace(",", ".")), unit
