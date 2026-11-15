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

from app.data.diet import Diet
from app.data.places import Place
from app.models import AddedBy, ChangeSource, RecipeKind, Role

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

ShopName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
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
    is_household_ingredient: bool  # created by this Household (ADR 0012), not a starter


class ShopIn(BaseModel):
    name: ShopName


class ShopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class AddItemIn(BaseModel):
    # Optional: devices choose it so they can refer to the item before the server replies.
    id: uuid.UUID | None = None
    text: ItemText
    quantity: Quantity | None = None
    unit: Unit | None = None
    # Usually left out: the server reads the amount off the text and finds the Ingredient.
    ingredient_id: uuid.UUID | None = None
    shop_id: uuid.UUID | None = None  # None = any shop


class EditItemIn(BaseModel):
    """Only the fields present are changed. Send `null` to clear quantity, unit, the
    Ingredient link or the Shop."""

    text: ItemText | None = None
    quantity: Quantity | None = None
    unit: Unit | None = None
    ingredient_id: uuid.UUID | None = None
    shop_id: uuid.UUID | None = None

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
    shop_id: uuid.UUID | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def checked(self) -> bool:
        return self.checked_at is not None


class ShoppingListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    version: int


class ShoppingListDetailOut(ShoppingListOut):
    items: list[ItemOut]
    shops: list[ShopOut]  # the Household's Shops, A to Z


# --- Kitchen -----------------------------------------------------------------------


class SetQuantityIn(BaseModel):
    """`null` means "we have some; amount not recorded"."""

    quantity: Quantity | None


class SetStapleIn(BaseModel):
    have: bool


class KitchenItemOut(BaseModel):
    ingredient: IngredientOut
    quantity: Quantity | None
    unit: str  # always the Ingredient's own unit: g, ml or count
    status: Literal["confirmed", "estimated", "unknown"]
    last_change_source: ChangeSource
    last_confirmed_at: datetime
    place: Place


class StapleOut(BaseModel):
    ingredient: IngredientOut
    have: bool
    place: Place


class PlaceIn(BaseModel):
    place: Place | None  # None = back to the default for its category


class PlaceOut(BaseModel):
    place: Place


class KitchenOut(BaseModel):
    version: int
    tracked: list[KitchenItemOut]
    staples: list[StapleOut]


# --- Recipes -----------------------------------------------------------------------

# An amount we report (never accept), sent as a string so no precision is lost.
Amount = Annotated[Decimal, PlainSerializer(lambda d: f"{d.normalize():f}", return_type=str)]


class RecipeSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: RecipeKind
    title: str
    summary: str
    cuisine: str | None
    servings: int
    total_minutes: int | None
    # How close to the search (1 = identical meaning). Only set for a search.
    score: float | None = None


class RecipeIngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    raw_text: str
    ingredient: IngredientOut | None
    quantity: Amount | None
    unit: str | None
    base_quantity: Amount | None  # in the Ingredient's own unit (g / ml / count)
    note: str | None
    optional: bool
    needs_review: bool


class RecipeOut(RecipeSummaryOut):
    ingredients: list[RecipeIngredientOut]
    method: list[str] | None
    source_url: str | None
    licence: str
    attribution: str


# --- Dietary Rules and Preferences ----------------------------------------------------

Cuisine = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class DietaryRulesIn(BaseModel):
    """The whole set (PUT replaces it). Unknown diets are rejected, not ignored."""

    diets: list[Diet] = Field(default=[], max_length=len(Diet))
    excluded_ingredient_ids: list[uuid.UUID] = Field(default=[], max_length=100)


class DietaryRulesOut(BaseModel):
    diets: list[Diet]
    excluded_ingredients: list[IngredientOut]


class PreferencesIn(BaseModel):
    household_size: int | None = Field(default=None, ge=1, le=20)
    cuisines: list[Cuisine] = Field(default=[], max_length=20)


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    household_size: int | None
    cuisines: list[str]


# --- Conversations with the agent --------------------------------------------------


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class ChatLine(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class DraftMealOut(BaseModel):
    recipe_id: str
    servings: int
    title: str | None = None  # missing on Drafts saved before 5b


class DraftAdditionOut(BaseModel):
    name: str
    quantity: float | None
    unit: str | None
    ingredient_id: str | None


class DraftOut(BaseModel):
    """The Draft Plan as it grows during a turn. Not Household data yet."""

    meals: dict[str, DraftMealOut]  # ISO date → meal
    list_additions: list[DraftAdditionOut]


class ProposalMealOut(BaseModel):
    date: str
    recipe_id: str
    title: str
    servings: int


class ProposalOut(BaseModel):
    """What the Member is asked to approve (slice 6). Meals that broke a Dietary Rule are
    already left out and named in `dropped`; `check_label` lists ingredients to check."""

    summary: str
    meals: list[ProposalMealOut]
    list_additions: list[DraftAdditionOut]
    check_label: list[str]
    dropped: list[str]


class ConversationDetailOut(ConversationOut):
    messages: list[ChatLine]
    draft: DraftOut | None
    proposal: ProposalOut | None


# What POST /conversations/{id}/messages streams. Each SSE message is `event: <type>`
# plus `data: <one of these as JSON>`. Listed in the OpenAPI schema so the app gets
# generated types for them, and checked in the tests against every event the agent sends.


class TextEvent(BaseModel):
    type: Literal["text"]
    text: str  # a piece of the reply, to append to what came before


class ToolEvent(BaseModel):
    type: Literal["tool"]
    name: str  # the tool the agent is using right now


class DraftEvent(BaseModel):
    type: Literal["draft"]
    draft: DraftOut


class ReplanEvent(BaseModel):
    type: Literal["replan"]
    problems: list[str]  # why validate sent the plan back


class ProposalEvent(BaseModel):
    type: Literal["proposal"]
    proposal: ProposalOut


class DoneEvent(BaseModel):
    type: Literal["done"]


class ErrorEvent(BaseModel):
    type: Literal["error"]
    message: str  # safe to show the Member


TurnEvent = Annotated[
    TextEvent | ToolEvent | DraftEvent | ReplanEvent | ProposalEvent | DoneEvent | ErrorEvent,
    Field(discriminator="type"),
]


class SendMessageIn(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
