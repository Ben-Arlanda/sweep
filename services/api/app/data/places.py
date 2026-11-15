"""Where things live in the Kitchen: Fridge, Freezer or Cupboard (ADR 0011).

Reference data in code, like `diet.py`: every Ingredient gets a default Place from its
category, and a Household can move any item. Produce mostly goes in the fridge, except a
short list Australian kitchens keep out of it (on the bench or in the cupboard).
"""

from enum import StrEnum


class Place(StrEnum):
    FRIDGE = "fridge"
    FREEZER = "freezer"
    CUPBOARD = "cupboard"  # includes the bench and the fruit bowl


BY_CATEGORY: dict[str, Place] = {
    "meat": Place.FRIDGE,
    "seafood": Place.FRIDGE,
    "dairy": Place.FRIDGE,
    "chilled": Place.FRIDGE,
    "produce": Place.FRIDGE,
    "frozen": Place.FREEZER,
    "pantry": Place.CUPBOARD,
    "spices": Place.CUPBOARD,
    "bakery": Place.CUPBOARD,
    "drinks": Place.CUPBOARD,
}

# Produce that's better (or usually kept) out of the fridge.
PRODUCE_OUT_OF_FRIDGE = frozenset(
    {
        "onion",
        "red onion",
        "shallots",
        "garlic",
        "potatoes",
        "sweet potato",
        "pumpkin",
        "tomatoes",
        "cherry tomatoes",
        "bananas",
        "avocado",
        "pineapple",
        "mangoes",
        "passionfruit",
    }
)


def default_place(name: str, category: str) -> Place:
    if category == "produce" and name in PRODUCE_OUT_OF_FRIDGE:
        return Place.CUPBOARD
    # An unknown category (a newly added Ingredient) lands in the cupboard, not nowhere.
    return BY_CATEGORY.get(category, Place.CUPBOARD)
