"""Reading a Kitchen Photo into rows for the review screen (slice 3e, ADR 0023).

One model call names the food it sees in photos of items taken out of one Place. Plain
code then trusts the answer only as far as it can check it:

- names are cleaned to one line; the model's count is kept only for Ingredients the
  Kitchen counts (eggs, onions), never turned into grams, and never for a Staple
- names are matched by our own matcher, which never creates an Ingredient here: a
  name Sweep doesn't know stays Not linked (ticked; applying it makes a Household
  Ingredient)
- each row says what the Kitchen has now, so the Member sees "4 in Kitchen, photo shows 6"

Nothing is written or stored. The approved rows go to `kitchen.apply_photo`.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors
from app.data.places import Place
from app.llm_costs import Usage
from app.models import HouseholdStaple, Ingredient, KitchenItem
from app.services import ingredients, kitchen
from app.services.recipe_import import MAX_PHOTOS, Photo
from app.text import clean_line

MAX_ITEMS, MAX_NAME, MAX_COUNT = 60, 80, 99


class SeenItem(BaseModel):
    name: str  # the plain name a shopping list would use, no brand or size
    count: int | None  # only when it can be counted


class KitchenPhotoReading(BaseModel):
    """The shape the model must answer in (a structured output)."""

    found_food: bool
    items: list[SeenItem]


class KitchenPhotoReader(Protocol):
    async def read_kitchen_photos(
        self, photos: Sequence[Photo], place: Place
    ) -> tuple[KitchenPhotoReading | None, Usage]: ...


@dataclass(frozen=True)
class PhotoRow:
    name: str
    ingredient: Ingredient | None  # None: Not linked
    quantity: Decimal | None  # in the Ingredient's own unit; None: "have some"
    tracked: KitchenItem | None  # what the Kitchen has now, if Tracked
    staple: HouseholdStaple | None  # or if it's a Staple

    # Every row starts ticked, Not linked too: the eval found no invented items in 12 runs
    # (ADR 0023), so a name Sweep doesn't know is kept, and a person unticks a misread.
    ticked: bool = True


async def from_photos(
    session: AsyncSession,
    household_id: uuid.UUID,
    reader: KitchenPhotoReader,
    photos: Sequence[Photo],
    place: Place,
) -> tuple[list[PhotoRow], Usage]:
    if not 1 <= len(photos) <= MAX_PHOTOS:
        raise errors.InvalidInput(f"Add 1 to {MAX_PHOTOS} photos.")
    reading, usage = await reader.read_kitchen_photos(photos, place)
    if reading is None:
        raise errors.Unavailable(
            "Sweep couldn't read those photos just now. Try again, or add them by hand."
        )
    rows: list[PhotoRow] = []
    by_ingredient: dict[uuid.UUID, int] = {}  # Ingredient id → its row's index
    for item in reading.items[:MAX_ITEMS] if reading.found_food else []:
        name = clean_line(item.name, MAX_NAME)
        if not name:
            continue
        ingredient = await ingredients.resolve(session, household_id, name, create=False)
        if ingredient is None:
            rows.append(PhotoRow(name, None, None, None, None))
            continue
        staple = await kitchen.staple_of(session, household_id, ingredient.id)
        quantity = _count(item.count) if ingredient.default_unit == "count" and not staple else None
        if ingredient.id in by_ingredient:  # two names, one Ingredient: both are what we have
            i = by_ingredient[ingredient.id]
            known = rows[i].quantity
            both = known + quantity if known is not None and quantity is not None else None
            rows[i] = replace(rows[i], quantity=both)
            continue
        tracked = await kitchen.tracked_of(session, household_id, ingredient.id)
        by_ingredient[ingredient.id] = len(rows)
        rows.append(PhotoRow(name, ingredient, quantity, tracked, staple))
    if not rows:
        raise errors.InvalidInput(
            "We couldn't see any food. Try a clearer photo with the labels facing up, "
            "or add them by hand."
        )
    return rows, usage


def _count(count: int | None) -> Decimal | None:
    return Decimal(count) if count is not None and 1 <= count <= MAX_COUNT else None
