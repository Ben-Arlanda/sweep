"""Database tables. Names follow CONTEXT.md (Household, Member, Owner)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.embeddings import DIMENSIONS


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class ChangeSource(StrEnum):
    """What last changed a Cabinet quantity. Feeds the calculated status (ADR 0003)."""

    PURCHASE = "purchase"  # ticked off a Shopping List
    MANUAL = "manual"  # a Member set it
    COOKED = "cooked"  # deducted by Mark as Cooked (slice 6)


class AddedBy(StrEnum):
    MEMBER = "member"
    AGENT = "agent"  # only through an approved Proposal (ADR 0005), from slice 6


def str_enum(enum: type[StrEnum], name: str) -> Enum:
    """A VARCHAR + CHECK constraint storing the enum's values. Easier to migrate than a PG enum."""
    return Enum(
        enum,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda members: [m.value for m in members],
    )


class Household(Base):
    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    # Goes up on every Cabinet change; carried by change notices, like a list's version.
    cabinet_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Member(Base):
    """A signed-in person inside a Household. No Household means no Member row.

    A person is identified by (auth_issuer, auth_subject): `sub` is only unique within
    one issuer, so the pair is what's unique. The unique constraint on that pair is also
    what enforces "one Household per Member" at the database level.
    """

    __tablename__ = "members"
    __table_args__ = (UniqueConstraint("auth_issuer", "auth_subject"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    auth_issuer: Mapped[str] = mapped_column(String(255))
    auth_subject: Mapped[str] = mapped_column(String(255))
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[Role] = mapped_column(str_enum(Role, "member_role"))
    display_name: Mapped[str] = mapped_column(String(80))
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class HouseholdInvite(Base):
    """A single-use code that lets one person join a Household. Expires after 7 days."""

    __tablename__ = "household_invites"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("members.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))


class ShoppingList(Base):
    """One of a Household's Shopping Lists.

    `version` goes up by one on every change to the list or its items. Change notices
    carry it, so a device can tell whether its copy is already up to date.
    """

    __tablename__ = "shopping_lists"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(60))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class ShoppingListItem(Base):
    """A line on a Shopping List. Free text for now; linked to an Ingredient in slice 3."""

    __tablename__ = "shopping_list_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    list_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shopping_lists.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    unit: Mapped[str | None] = mapped_column(String(20))
    added_by: Mapped[AddedBy] = mapped_column(
        str_enum(AddedBy, "item_added_by"), default=AddedBy.MEMBER
    )
    # SET NULL: an item stays on the list after the Member who added it leaves.
    added_by_member_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("members.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("members.id", ondelete="SET NULL")
    )
    # Which Ingredient this line is, if we could tell. Only linked items reach the Cabinet.
    ingredient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ingredients.id", ondelete="SET NULL")
    )
    # Loaded with the item every time (a JOIN), so reading it never needs an extra await.
    ingredient: Mapped["Ingredient | None"] = relationship(lazy="joined")
    # What ticking this item added to the Cabinet, so un-ticking can take it back out.
    cabinet_applied: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    cabinet_added_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))


class IdempotencyKey(Base):
    """A mutation we've already applied, so a retry gets the same answer instead of a repeat.

    Keys are scoped to the Member: two people's devices can't collide, and one Member
    can't replay (and so read) another Member's response by guessing their key.
    """

    __tablename__ = "idempotency_keys"
    __table_args__ = (PrimaryKeyConstraint("member_id", "key"),)

    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(255))
    # SHA-256 of method + path + body. Same key, different request = a client bug.
    fingerprint: Mapped[bytes] = mapped_column(LargeBinary(32))
    status_code: Mapped[int] = mapped_column(SmallInteger)
    response: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class Ingredient(Base):
    """A canonical food item, shared by every Household (reference data, see app/seed.py)."""

    __tablename__ = "ingredients"
    __table_args__ = (
        CheckConstraint("default_unit IN ('g', 'ml', 'count')", name="default_unit_known"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    category: Mapped[str] = mapped_column(String(30))
    # The Cabinet stores this Ingredient's quantities in this unit only.
    default_unit: Mapped[str] = mapped_column(String(10))
    # Density, for turning millilitres into grams and back. Unknown for most things.
    grams_per_ml: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    is_default_staple: Mapped[bool] = mapped_column(Boolean, default=False)


class IngredientAlias(Base):
    """Another name for an Ingredient: "all-purpose flour" → plain flour. Stored normalised."""

    __tablename__ = "ingredient_aliases"

    alias: Mapped[str] = mapped_column(String(80), primary_key=True)
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), index=True
    )


class HouseholdStaple(Base):
    """An Ingredient this Household treats as a Staple: assumed present, no quantity.

    New Households get a row for each default Staple. `ran_out_at` set = "we've run out".
    """

    __tablename__ = "household_staples"
    __table_args__ = (PrimaryKeyConstraint("household_id", "ingredient_id"),)

    household_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE")
    )
    ingredient: Mapped[Ingredient] = relationship(lazy="joined")
    ran_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CabinetItem(Base):
    """A Tracked Ingredient the Household has. `quantity` is in the Ingredient's own unit;
    None means "we have some, amount not recorded".

    Confirmed / Estimated / Unknown is not stored: it's calculated when read from
    `last_change_source` and `last_confirmed_at` (ADR 0003), so it can't go stale.
    """

    __tablename__ = "cabinet_items"
    __table_args__ = (
        UniqueConstraint("household_id", "ingredient_id"),
        CheckConstraint("quantity >= 0", name="quantity_not_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE")
    )
    ingredient: Mapped[Ingredient] = relationship(lazy="joined")
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    last_change_source: Mapped[ChangeSource] = mapped_column(
        str_enum(ChangeSource, "cabinet_change_source")
    )
    last_confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class RecipeKind(StrEnum):
    SEED = "seed"  # written for Sweep, shared by every Household
    IMPORTED = "imported"  # saved from a URL by one Household (slice 4b)


class ParseMethod(StrEnum):
    RULE = "rule"
    LLM = "llm"


class Recipe(Base):
    """A recipe in the Recipe Knowledge Base.

    Seed Recipes have no Household (everyone sees them); Imported Recipes belong to one.
    The CHECK keeps those two facts in step, so a query can't accidentally share an
    Imported Recipe by forgetting a filter.
    """

    __tablename__ = "recipes"
    __table_args__ = (
        CheckConstraint("(kind = 'seed') = (household_id IS NULL)", name="seed_has_no_household"),
        CheckConstraint("servings > 0", name="servings_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    kind: Mapped[RecipeKind] = mapped_column(str_enum(RecipeKind, "recipe_kind"))
    household_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    # Stable name for Seed Recipes, so reloading the seed updates rows instead of adding.
    slug: Mapped[str | None] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(String(500))
    cuisine: Mapped[str | None] = mapped_column(String(40))
    servings: Mapped[int] = mapped_column(SmallInteger)
    total_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    # Steps, for recipes we're allowed to show in full. Imported Recipes link out instead.
    method: Mapped[list[str] | None] = mapped_column(JSONB)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    licence: Mapped[str] = mapped_column(String(100))
    attribution: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        order_by="RecipeIngredient.position",
        cascade="all, delete-orphan",
        lazy="selectin",  # one extra query for all ingredients of all loaded recipes
    )


class RecipeIngredient(Base):
    """One ingredient line of a recipe: what was written, and what we understood."""

    __tablename__ = "recipe_ingredients"
    __table_args__ = (UniqueConstraint("recipe_id", "position"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(SmallInteger)
    raw_text: Mapped[str] = mapped_column(String(300))
    # SET NULL: deleting an Ingredient leaves the line, just unlinked.
    ingredient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ingredients.id", ondelete="SET NULL"), index=True
    )
    ingredient: Mapped[Ingredient | None] = relationship(lazy="joined")
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    unit: Mapped[str | None] = mapped_column(String(20))  # as written: "tbsp", "clove"
    # The same amount in the Ingredient's own unit (g / ml / count), when that's honest.
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    note: Mapped[str | None] = mapped_column(String(300))
    optional: Mapped[bool] = mapped_column(Boolean, default=False)
    parse_method: Mapped[ParseMethod] = mapped_column(str_enum(ParseMethod, "parse_method"))
    # Set when nothing could match the line to an Ingredient (and it isn't just water).
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)


class RecipeEmbedding(Base):
    """A recipe's search vector, per embedding model.

    `content_hash` is a fingerprint of the text that was embedded. If the recipe's text
    changes, the hash no longer matches and the vector is rebuilt.
    """

    __tablename__ = "recipe_embeddings"
    __table_args__ = (
        PrimaryKeyConstraint("recipe_id", "model"),
        # HNSW: an index that finds the nearest vectors without comparing every row.
        Index(
            "ix_recipe_embeddings_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    recipe_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))
    model: Mapped[str] = mapped_column(String(60))
    content_hash: Mapped[bytes] = mapped_column(LargeBinary(32))
    embedding: Mapped[list[float]] = mapped_column(Vector(DIMENSIONS))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
