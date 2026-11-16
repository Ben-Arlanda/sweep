"""Request and response shapes. They also become the OpenAPI schema for the client."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    computed_field,
    field_validator,
    model_validator,
)

from app.data.diet import Diet
from app.data.places import Place
from app.models import (
    AddedBy,
    ChangeSource,
    Course,
    ParseMethod,
    PlanMode,
    ProposalStatus,
    RecipeKind,
    Role,
)
from app.services.ingredients import normalise
from app.text import ONE_LINE


# Trimming runs before ONE_LINE, so a pasted trailing newline is simply removed.
def _name(max_length: int) -> StringConstraints:
    return StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length)


HouseholdName = Annotated[str, _name(100), ONE_LINE]
DisplayName = Annotated[str, _name(80), ONE_LINE]


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

ShopName = Annotated[str, _name(40), ONE_LINE]
ItemText = Annotated[str, _name(200), ONE_LINE]
Unit = Annotated[str, _name(20), ONE_LINE]
# Sent and returned as a string ("1.5"), so no float rounding on either side.
# Postgres hands back 1.500 for NUMERIC(10, 3); trim the trailing zeros.
Quantity = Annotated[
    Decimal,
    Field(gt=0, max_digits=10, decimal_places=3),
    PlainSerializer(lambda d: f"{d.normalize():f}", return_type=str),
]


IngredientName = Annotated[str, _name(80), ONE_LINE]


class IngredientIn(BaseModel):
    name: IngredientName

    @field_validator("name")
    @classmethod
    def has_letters_or_digits(cls, name: str) -> str:
        if not normalise(name):  # "!!!" would match nothing and can't be a name
            raise ValueError("needs a letter or number")
        return name


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
    course: Course
    servings: int
    total_minutes: int | None
    # How close to the search (1 = identical meaning). Only set for a search.
    score: float | None = None


class ImportedRecipeOut(RecipeSummaryOut):
    """One of "Your recipes". `rule_breaks` empty = plannable; otherwise why the Dietary
    Rules hide it from search and plans: "satay sauce (couldn't check)"."""

    rule_breaks: list[str]


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
    parse_method: ParseMethod  # "llm" = the review screen's "Check" mark


class RecipeOut(RecipeSummaryOut):
    ingredients: list[RecipeIngredientOut]
    method: list[str] | None
    source_url: str | None
    licence: str
    attribution: str


# --- Dietary Rules and Preferences ----------------------------------------------------

Cuisine = Annotated[str, _name(40), ONE_LINE]


class DietaryRulesIn(BaseModel):
    """The whole set (PUT replaces it). Unknown diets are rejected, not ignored."""

    diets: list[Diet] = Field(default=[], max_length=len(Diet))
    excluded_ingredient_ids: list[uuid.UUID] = Field(default=[], max_length=100)


class DietaryRulesOut(BaseModel):
    diets: list[Diet]
    excluded_ingredients: list[IngredientOut]


Weekday = Annotated[int, Field(ge=1, le=7)]  # ISO: Monday 1 … Sunday 7


class PreferencesIn(BaseModel):
    household_size: int | None = Field(default=None, ge=1, le=20)
    cuisines: list[Cuisine] = Field(default=[], max_length=20)


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    household_size: int | None
    cuisines: list[str]
    plan_weekdays: list[int]


class PlanWeekdaysIn(BaseModel):
    """The days the Household usually plans. Its own route, so saving them can't
    overwrite another Member's change to the rest of the Preferences."""

    weekdays: list[Weekday] = Field(min_length=1, max_length=7)

    @field_validator("weekdays")
    @classmethod
    def _no_repeats(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("each weekday once")
        return v


class PlanWeekdaysOut(BaseModel):
    weekdays: list[int]


# --- Meal Plan ----------------------------------------------------------------------


class PlannedMealOut(BaseModel):
    id: uuid.UUID
    date: date
    recipe_id: uuid.UUID
    title: str
    servings: int
    cooked_at: datetime | None
    cooked_by: uuid.UUID | None
    # Before Cooked: Tracked items in the Kitchen it uses. After: what Cooked took out.
    kitchen_uses: list[str]


class MealPlanOut(BaseModel):
    """A week of Planned Meals, from `start`. `version` matches the change notices."""

    start: date
    end: date
    today: date  # the app's today (Sydney), so the phone doesn't trust its own clock
    version: int
    meals: list[PlannedMealOut]


# --- Conversations with the agent --------------------------------------------------


class ConversationIn(BaseModel):
    """How a plan starts. Both left out for a free chat; the "Plan my week" sheet sends
    the kind of plan and the days picked (ADR 0015)."""

    mode: PlanMode | None = None
    days: list[date] | None = Field(default=None, min_length=1, max_length=14)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    plan_mode: PlanMode | None
    plan_days: list[date] | None


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
    # On a Proposal: how much of it is already on the Shopping List ("200 g"), since an
    # addition is the extra on top (ADR 0016). None when it isn't there.
    on_list: str | None = None
    # On a Proposal (slice 10): "meal" (for_meals uses it), "asked" (the Member named it)
    # or "unexplained" (shown unticked: "Not for any meal"). None on a Draft, and on
    # Proposals saved before reasons existed.
    reason: Literal["meal", "asked", "unexplained"] | None = None
    for_meals: list[str] = []


class DraftOut(BaseModel):
    """The Draft Plan as it grows during a turn. Not Household data yet."""

    meals: dict[str, DraftMealOut]  # ISO date → meal
    list_additions: list[DraftAdditionOut]


class ProposalMealOut(BaseModel):
    date: str
    recipe_id: str
    title: str
    servings: int
    # The dinner already planned that day, which approving would replace.
    replaces: str | None = None


class ProposalOutcomeOut(BaseModel):
    """What approving did. `message` is written by code, not the LLM."""

    message: str
    saved_meals: int
    added_items: int
    skipped: list[str]  # each one says what and why, e.g. "Rice is already on the list"
    # Additions already on the list, raised by the extra (ADR 0016): "rice: 500 g → 800 g".
    topped_up: list[str] = []
    # What the Member left ticked. None on outcomes saved before this was recorded.
    kept_meals: list[str] | None = None
    kept_additions: list[int] | None = None


class ProposalOut(BaseModel):
    """What the Member is asked to approve. Meals that broke a Dietary Rule are already
    left out and named in `dropped`; `check_label` lists ingredients to check."""

    id: uuid.UUID | None = None  # missing on Proposals shown before slice 6a
    status: ProposalStatus = ProposalStatus.PENDING
    summary: str
    meals: list[ProposalMealOut]
    list_additions: list[DraftAdditionOut]
    check_label: list[str]
    dropped: list[str]
    outcome: ProposalOutcomeOut | None = None


class DecisionIn(BaseModel):
    """Approve (optionally with some meals or additions unticked) or reject.

    `keep_meals` / `keep_additions` list what stays ticked: dates of proposed meals, and
    positions in `list_additions`. Leave one out to keep all of that kind."""

    action: Literal["approve", "reject"]
    keep_meals: list[date] | None = Field(default=None, max_length=14)
    keep_additions: list[int] | None = Field(default=None, max_length=60)


class ChatProposalOut(ProposalOut):
    # How many `messages` lines come before it, so the chat can show it in place.
    # None for Proposals made before slice 6a step 5 (shown at the end).
    after_line: int | None


class ConversationDetailOut(ConversationOut):
    messages: list[ChatLine]
    draft: DraftOut | None
    proposal: ProposalOut | None  # the one waiting for an answer, if any
    proposals: list[ChatProposalOut]  # every Proposal in this chat, oldest first


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


# --- Imported Recipes (slice 4d) --------------------------------------------------------

RecipeLine = Annotated[str, _name(300), ONE_LINE]  # an ingredient line, as written


class LinesIn(BaseModel):
    """Ingredient lines to read for the review screen. Nothing is stored."""

    lines: list[RecipeLine] = Field(min_length=1, max_length=60)


class ImportedLineIn(BaseModel):
    raw_text: RecipeLine
    # Set when a Member chose the Ingredient in the Link sheet; otherwise Sweep matches it.
    ingredient_id: uuid.UUID | None = None


class ImportedRecipeIn(BaseModel):
    """What the review screen saves (POST) or replaces (PUT). Its Save rules: a title,
    servings, a Course and one line. The marks ("Check", "Not linked") never block."""

    title: Annotated[str, _name(200), ONE_LINE]
    servings: int = Field(gt=0, le=50)
    total_minutes: int | None = Field(default=None, gt=0, le=1440)
    course: Course
    cuisine: Cuisine | None = None
    lines: list[ImportedLineIn] = Field(min_length=1, max_length=60)
    method: list[Annotated[str, _name(2000)]] | None = Field(default=None, max_length=40)


class PasteIn(BaseModel):
    """Pasted recipe text. Line breaks are kept: they're how recipes are laid out."""

    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20_000)]


class DraftLineOut(RecipeIngredientOut):
    # True: the line isn't in the pasted text word for word, so the review screen marks
    # it "Check". The model may have reworded it, or made it up.
    check: bool


class ImportDraftOut(BaseModel):
    """What a door read, for the review screen. Nothing is stored until Save."""

    title: str
    servings: int | None  # None: the Member fills it in (Save needs it)
    total_minutes: int | None
    course: Course  # Sweep's guess, pre-selected and labelled as one
    cuisine: str | None
    lines: list[DraftLineOut]
    method: list[str] | None
    more_recipes: bool  # "This has more than one recipe: we've taken the first."
