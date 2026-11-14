"""Database tables. Names follow CONTEXT.md (Household, Member, Owner)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


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
