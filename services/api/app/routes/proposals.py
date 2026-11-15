"""Deciding a Proposal: `POST /proposals/{id}/decision`.

No Idempotency-Key here. The commit runs inside the graph in its own transaction, so a
key row couldn't be saved atomically with it. The Proposal id does that job instead
(ADR 0005): once approved, a repeated Approve gets the stored outcome, nothing redone.
"""

import uuid
from typing import Any, cast

from fastapi import APIRouter, Request

from app import errors
from app.deps import MemberDep, SessionDep
from app.models import Conversation, Proposal, ProposalStatus, utcnow
from app.schemas import DecisionIn, ProposalOut
from app.services import proposals
from app.services.conversations import Agent

router = APIRouter(prefix="/proposals", tags=["agent"])


def proposal_out(proposal: Proposal) -> ProposalOut:
    return ProposalOut.model_validate(
        {
            **proposal.payload,
            "id": proposal.id,
            "status": proposal.status,
            "outcome": proposal.outcome,
        }
    )


@router.post("/{proposal_id}/decision")
async def decide(
    proposal_id: uuid.UUID,
    body: DecisionIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
) -> ProposalOut:
    proposal = await proposals.get_mine(session, ctx, proposal_id)
    if proposal.status == ProposalStatus.APPROVED and body.action == "approve":
        return proposal_out(proposal)  # a retry: same answer, nothing repeated
    if proposal.status != ProposalStatus.PENDING:
        raise errors.Conflict(f"This plan was already {proposal.status.value}")
    if await proposals.expire_if_due(session, proposal, utcnow()):
        await session.commit()
        raise errors.Conflict("This plan has expired. Ask for a new one.")
    proposals.check_keep(proposal.payload, body.keep_meals, body.keep_additions)

    agent = cast(Agent | None, request.app.state.agent)
    if agent is None:
        raise errors.Unavailable("The assistant isn't configured on this server")
    conversation = await session.get_one(Conversation, proposal.conversation_id)
    await session.commit()  # end this read before the graph's own transactions start

    decision: dict[str, Any] = {"action": body.action}
    if body.action == "approve":
        decision["keep_meals"] = (
            [d.isoformat() for d in body.keep_meals] if body.keep_meals is not None else None
        )
        decision["keep_additions"] = body.keep_additions
    await agent.decide(conversation, proposal.id, decision)

    await session.refresh(proposal)
    return proposal_out(proposal)
