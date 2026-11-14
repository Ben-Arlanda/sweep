"""HTTP routes for Households, invites and account deletion.

Routes stay thin: parse input, call a service, commit, shape the response.
"""

import uuid

from fastapi import APIRouter, Response, status

from app.deps import IdentityDep, MemberDep, SessionDep
from app.schemas import (
    AcceptInviteIn,
    CreateHouseholdIn,
    HouseholdDetailOut,
    HouseholdOut,
    InviteOut,
    MemberOut,
    MeOut,
)
from app.services import households
from app.services.households import MemberContext

router = APIRouter()


def me_out(ctx: MemberContext) -> MeOut:
    return MeOut(
        member=MemberOut.model_validate(ctx.member),
        household=HouseholdOut.model_validate(ctx.household),
    )


@router.post("/households", status_code=status.HTTP_201_CREATED)
async def create_household(
    body: CreateHouseholdIn, session: SessionDep, identity: IdentityDep
) -> MeOut:
    ctx = await households.create_household(session, identity, body.name, body.display_name)
    await session.commit()
    return me_out(ctx)


@router.get("/me")
async def get_me(ctx: MemberDep) -> MeOut:
    return me_out(ctx)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(ctx: MemberDep, session: SessionDep) -> Response:
    await households.delete_account(session, ctx)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/households/current")
async def get_household(ctx: MemberDep, session: SessionDep) -> HouseholdDetailOut:
    members = await households.list_members(session, ctx)
    return HouseholdDetailOut(
        **HouseholdOut.model_validate(ctx.household).model_dump(),
        members=[MemberOut.model_validate(m) for m in members],
    )


@router.post("/households/current/invites", status_code=status.HTTP_201_CREATED)
async def create_invite(ctx: MemberDep, session: SessionDep) -> InviteOut:
    invite = await households.create_invite(session, ctx)
    await session.commit()
    return InviteOut.model_validate(invite)


@router.post("/invites/{code}/accept")
async def accept_invite(
    code: str, body: AcceptInviteIn, session: SessionDep, identity: IdentityDep
) -> MeOut:
    ctx = await households.accept_invite(session, identity, code, body.display_name)
    await session.commit()
    return me_out(ctx)


@router.delete("/households/current/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(member_id: uuid.UUID, ctx: MemberDep, session: SessionDep) -> Response:
    await households.remove_member(session, ctx, member_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
