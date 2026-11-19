"""Deciding a Proposal: `POST /proposals/{id}/decision`.

No Idempotency-Key here. The commit runs inside the graph in its own transaction, so a
key row couldn't be saved atomically with it. The Proposal id does that job instead
(ADR 0005): once approved, a repeated Approve gets the stored outcome, nothing redone.
"""

import uuid
from datetime import date
from typing import Annotated, Any, cast

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from app import errors
from app.deps import MemberDep, SessionDep
from app.embeddings import Embedder
from app.models import Conversation, PlanMode, Proposal, ProposalStatus, utcnow
from app.routes.meal_plan import ideas_out
from app.schemas import DecisionIn, DinnerIdeaOut, ProposalOut
from app.services import diet, dinner_ideas, proposals, recipes
from app.services.conversations import Agent

ALTERNATIVES = 5

router = APIRouter(prefix="/proposals", tags=["agent"])


def shown_status(proposal: Proposal) -> ProposalStatus:
    """Pending but past its expiry reads as expired (it's saved as such when acted on)."""
    if proposal.status == ProposalStatus.PENDING and proposal.expires_at <= utcnow():
        return ProposalStatus.EXPIRED
    return proposal.status


def proposal_fields(proposal: Proposal) -> dict[str, Any]:
    return {
        **proposal.payload,
        "id": proposal.id,
        "status": shown_status(proposal),
        "outcome": proposal.outcome,
    }


def proposal_out(proposal: Proposal) -> ProposalOut:
    return ProposalOut.model_validate(proposal_fields(proposal))


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
    if body.action == "swap":
        assert body.date is not None and body.recipe_id is not None
        await _check_swap(session, ctx.household.id, proposal, body.date, body.recipe_id)

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
    if body.action == "swap":
        decision |= {"date": str(body.date), "recipe_id": str(body.recipe_id)}
    await agent.decide(conversation, proposal.id, decision)

    if body.action == "swap":  # answer with the new Proposal that replaced it
        new = await session.scalar(
            select(Proposal).where(
                Proposal.conversation_id == conversation.id,
                Proposal.status == ProposalStatus.PENDING,
            )
        )
        if new is not None:
            return proposal_out(new)
    await session.refresh(proposal)
    return proposal_out(proposal)


def _day_in(proposal: Proposal, day: date) -> None:
    if day.isoformat() not in {m["date"] for m in proposal.payload["meals"]}:
        raise errors.InvalidInput("That day isn't in this plan")


async def _check_swap(
    session: SessionDep, household_id: uuid.UUID, proposal: Proposal, day: date, rid: uuid.UUID
) -> None:
    """Before the graph resumes: a day of this plan, a recipe the Household can see that
    passes its Dietary Rules. Refused here, the Proposal stays pending and unchanged."""
    _day_in(proposal, day)
    recipe = await recipes.get_recipe(session, household_id, rid)
    check = diet.check_recipe(recipe, await diet.get_rules(session, household_id))
    if not check.ok:
        raise errors.Conflict(
            f"{recipe.title} breaks your Dietary Rules: {', '.join(check.breaks)}"
        )


@router.get("/{proposal_id}/alternatives")
async def alternatives(
    proposal_id: uuid.UUID,
    day: Annotated[date, Query(alias="date")],
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
) -> list[DinnerIdeaOut]:
    """What a day of a pending Proposal could be swapped for (ADR 0025): the same code
    as Dinner Ideas, leaving out the plan's recipes. In New recipes mode, candidates
    come by taste (the Household's liked cuisines) and Favourites get no boost."""
    proposal = await proposals.get_mine(session, ctx, proposal_id)
    if proposal.status != ProposalStatus.PENDING:
        raise errors.Conflict(f"This plan was already {proposal.status.value}")
    _day_in(proposal, day)
    conversation = await session.get_one(Conversation, proposal.conversation_id)
    new = conversation.plan_mode == PlanMode.NEW
    among = None
    embedder = cast(Embedder | None, request.app.state.embedder)
    if new and embedder is not None:
        prefs = await diet.get_preferences(session, ctx.household.id)
        among = await dinner_ideas.by_taste(session, ctx.household.id, embedder, prefs.cuisines)
    found = await dinner_ideas.ideas(
        session,
        ctx,
        exclude=[uuid.UUID(m["recipe_id"]) for m in proposal.payload["meals"]],
        boost_favourites=not new,
        among=among,
        limit=ALTERNATIVES,
    )
    return ideas_out(found)
