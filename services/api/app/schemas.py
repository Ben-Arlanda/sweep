"""Request and response shapes. They also become the OpenAPI schema for the client."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    computed_field,
    model_validator,
)

from app.models import AddedBy, Role

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


class ListNameIn(BaseModel):
    name: ListName


class AddItemIn(BaseModel):
    text: ItemText
    quantity: Quantity | None = None
    unit: Unit | None = None


class EditItemIn(BaseModel):
    """Only the fields present are changed. Send `null` to clear quantity or unit."""

    text: ItemText | None = None
    quantity: Quantity | None = None
    unit: Unit | None = None

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
