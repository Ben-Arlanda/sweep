"""Household business rules: who belongs where, and who may change membership.

Every function takes the caller (an Identity or a MemberContext) and only ever touches
that caller's Household. Callers never pass a household_id in; it comes from their
Member row. That's what makes "access another Household" impossible rather than
merely forbidden.
"""

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import Identity
from app.errors import (
    AlreadyInHousehold,
    Conflict,
    InviteInvalid,
    NotFound,
    NotInHousehold,
    PermissionDenied,
)
from app.models import Household, HouseholdInvite, Member, Role, utcnow

INVITE_LIFETIME = timedelta(days=7)
# No 0/O or 1/I/L: codes get read aloud and typed on phones.
INVITE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
INVITE_LENGTH = 8


@dataclass(frozen=True)
class MemberContext:
    """The verified caller plus their Household. Passed to every Household-scoped service."""

    member: Member
    household: Household

    @property
    def is_owner(self) -> bool:
        return self.member.role == Role.OWNER


async def find_member(session: AsyncSession, identity: Identity) -> Member | None:
    result = await session.execute(
        select(Member).where(
            Member.auth_issuer == identity.issuer, Member.auth_subject == identity.subject
        )
    )
    return result.scalar_one_or_none()


async def get_member_context(session: AsyncSession, identity: Identity) -> MemberContext:
    result = await session.execute(
        select(Member, Household)
        .join(Household, Member.household_id == Household.id)
        .where(Member.auth_issuer == identity.issuer, Member.auth_subject == identity.subject)
    )
    row = result.one_or_none()
    if row is None:
        raise NotInHousehold("You're not in a Household yet")
    return MemberContext(member=row.Member, household=row.Household)


async def _add_member(
    session: AsyncSession, identity: Identity, household: Household, role: Role, name: str
) -> Member:
    member = Member(
        auth_issuer=identity.issuer,
        auth_subject=identity.subject,
        household_id=household.id,
        role=role,
        display_name=name,
    )
    session.add(member)
    try:
        await session.flush()
    except IntegrityError as error:
        # Two requests raced past the "already a member?" check. The database's unique
        # constraint on (auth_issuer, auth_subject) is the real guard; this is the backstop.
        raise AlreadyInHousehold("You're already in a Household") from error
    return member


async def create_household(
    session: AsyncSession, identity: Identity, name: str, display_name: str
) -> MemberContext:
    if await find_member(session, identity) is not None:
        raise AlreadyInHousehold("You're already in a Household")

    household = Household(name=name)
    session.add(household)
    await session.flush()  # sends the INSERT so the member's foreign key has a row to point at
    member = await _add_member(session, identity, household, Role.OWNER, display_name)
    return MemberContext(member=member, household=household)


async def list_members(session: AsyncSession, ctx: MemberContext) -> list[Member]:
    result = await session.execute(
        select(Member)
        .where(Member.household_id == ctx.household.id)
        .order_by(Member.joined_at, Member.id)
    )
    return list(result.scalars())


async def create_invite(
    session: AsyncSession, ctx: MemberContext, now: datetime | None = None
) -> HouseholdInvite:
    if not ctx.is_owner:
        raise PermissionDenied("Only the Owner can invite people")

    now = now or utcnow()
    invite = HouseholdInvite(
        code="".join(secrets.choice(INVITE_ALPHABET) for _ in range(INVITE_LENGTH)),
        household_id=ctx.household.id,
        created_by=ctx.member.id,
        created_at=now,
        expires_at=now + INVITE_LIFETIME,
    )
    session.add(invite)
    await session.flush()
    return invite


async def accept_invite(
    session: AsyncSession,
    identity: Identity,
    code: str,
    display_name: str,
    now: datetime | None = None,
) -> MemberContext:
    if await find_member(session, identity) is not None:
        raise AlreadyInHousehold("Leave your current Household before joining another")

    now = now or utcnow()
    # FOR UPDATE locks the invite row until we commit, so two people redeeming the same
    # code at the same moment can't both get in: the second waits, then sees used_at set.
    result = await session.execute(
        select(HouseholdInvite)
        .where(HouseholdInvite.code == code.strip().upper())
        .with_for_update()
    )
    invite = result.scalar_one_or_none()
    # One error for unknown, used and expired: the app shows the same message either way.
    if invite is None or invite.used_at is not None or invite.expires_at <= now:
        raise InviteInvalid("This invite code is invalid or has expired")

    household = await session.get_one(Household, invite.household_id)
    member = await _add_member(session, identity, household, Role.MEMBER, display_name)
    invite.used_at = now
    invite.used_by = member.id
    return MemberContext(member=member, household=household)


async def remove_member(session: AsyncSession, ctx: MemberContext, member_id: uuid.UUID) -> None:
    if not ctx.is_owner:
        raise PermissionDenied("Only the Owner can remove Members")
    if member_id == ctx.member.id:
        raise Conflict("Use account deletion to leave your own Household")

    # Scoped to the caller's Household: a Member of another Household is "not found".
    result = await session.execute(
        select(Member).where(Member.id == member_id, Member.household_id == ctx.household.id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise NotFound("No such Member in your Household")
    await session.delete(target)


async def delete_account(session: AsyncSession, ctx: MemberContext) -> None:
    """Remove the caller. The last Member out deletes the Household and everything in it."""
    # Lock the Household row so two Members deleting at the same moment are handled one
    # after the other. Without it, both could see "someone else is still here", and the
    # Household would be left with no Members at all.
    await session.execute(
        select(Household).where(Household.id == ctx.household.id).with_for_update()
    )
    others = [m for m in await list_members(session, ctx) if m.id != ctx.member.id]

    if not others:
        await session.delete(ctx.household)  # ON DELETE CASCADE removes members and invites
        return

    if ctx.is_owner:
        others[0].role = Role.OWNER  # longest-standing remaining Member
    await session.delete(ctx.member)
