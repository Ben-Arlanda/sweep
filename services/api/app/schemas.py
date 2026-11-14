"""Request and response shapes. They also become the OpenAPI schema for the client."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    computed_field,
    model_validator,
)

from app.models import AddedBy, ChangeSource, Role

HouseholdName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class CreateHouseholdIn(BaseModel):
    name: HouseholdName
    display_name: DisplayName


class AcceptInviteIn(BaseModel):
    display_name: DisplayName


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    role: Role
    joined_at: datetime


class HouseholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime


class HouseholdDetailOut(HouseholdOut):
    members: list[MemberOut]


class MeOut(BaseModel):
    member: MemberOut
    household: HouseholdOut


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    expires_at: datetime


class ErrorOut(BaseModel):
    code: str
    detail: str


# --- Shopping Lists ----------------------------------------------------------------

ListName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
ItemText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Unit = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
# Sent and returned as a string ("1.5"), so no float rounding on either side.
# Postgres hands back 1.500 for NUMERIC(10, 3); trim the trailing zeros.
Quantity = Annotated[
    Decimal,
    Field(gt=0, max_digits=10, decimal_places=3),
    PlainSerializer(lambda d: f"{d.normalize():f}", return_type=str),
]


class IngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    default_unit: str


class ListNameIn(BaseModel):
    name: ListName


class AddItemIn(BaseModel):
    # Optional: devices choose it so they can refer to the item before the server replies.
    id: uuid.UUID | None = None
    text: ItemText
    quantity: Quantity | None = None
    unit: Unit | None = None
    # Usually left out: the server reads the amount off the text and finds the Ingredient.
    ingredient_id: uuid.UUID | None = None


class EditItemIn(BaseModel):
    """Only the fields present are changed. Send `null` to clear quantity, unit or the
    Ingredient link."""

    text: ItemText | None = None
    quantity: Quantity | None = None
    unit: Unit | None = None
    ingredient_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def text_cannot_be_cleared(self) -> Self:
        if "text" in self.model_fields_set and self.text is None:
            raise ValueError("text can't be empty")
        return self


class SetCheckedIn(BaseModel):
    checked: bool


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    quantity: Quantity | None
    unit: str | None
    added_by: AddedBy
    added_by_member_id: uuid.UUID | None
    created_at: datetime
    checked_at: datetime | None
    checked_by: uuid.UUID | None
    ingredient: IngredientOut | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def checked(self) -> bool:
        return self.checked_at is not None


class ShoppingListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    version: int


class ShoppingListSummaryOut(ShoppingListOut):
    unchecked_count: int


class ShoppingListDetailOut(ShoppingListOut):
    items: list[ItemOut]


# --- Cabinet -----------------------------------------------------------------------


class SetQuantityIn(BaseModel):
    """`null` means "we have some; amount not recorded"."""

    quantity: Quantity | None


class SetStapleIn(BaseModel):
    have: bool


class CabinetItemOut(BaseModel):
    ingredient: IngredientOut
    quantity: Quantity | None
    unit: str  # always the Ingredient's own unit: g, ml or count
    status: Literal["confirmed", "estimated", "unknown"]
    last_change_source: ChangeSource
    last_confirmed_at: datetime


class StapleOut(BaseModel):
    ingredient: IngredientOut
    have: bool


class CabinetOut(BaseModel):
    version: int
    tracked: list[CabinetItemOut]
    staples: list[StapleOut]
