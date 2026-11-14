"""Database tables. Names follow CONTEXT.md (Household, Member, Owner)."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


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
    role: Mapped[Role] = mapped_column(
        Enum(
            Role,
            name="member_role",
            native_enum=False,  # a VARCHAR + CHECK constraint; easier to migrate than a PG enum
            create_constraint=True,
            length=20,
            values_callable=lambda roles: [r.value for r in roles],
        )
    )
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
