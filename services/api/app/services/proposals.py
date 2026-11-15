"""Proposals: saving what the agent proposed, and turning an Approval into Household data.

Everything here is plain code (ADR 0005). The agent can only *propose*; `commit` is the
one place agent-planned meals and list additions become real, and it re-checks them
against today's data first, because a Proposal can wait up to a day.

Every status change is guarded by `status = 'pending'`, so running a step twice (a
retry, a crash and resume) can't decide a Proposal twice.
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors
from app.agent.state import Draft, DraftMeal
from app.agent.validate import validate_draft
from app.models import Actor, AddedBy, PlannedMeal, Proposal, ProposalStatus, utcnow
from app.services import audit, diet, ingredients, kitchen, meal_plan, recipes, shopping_lists
from app.services.households import MemberContext

EXPIRES_AFTER = timedelta(hours=24)
ENTITY = "proposal"


async def create(
    session: AsyncSession,
    conversation_id: uuid.UUID,
    household_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: dict[str, Any],
) -> Proposal:
    """Save a Proposal the Member is about to see. Anything still pending in this
    Conversation is superseded: only the newest one can be approved."""
    await close_pending(session, conversation_id, ProposalStatus.SUPERSEDED, member_id)
    now = utcnow()
    proposal = Proposal(
        conversation_id=conversation_id,
        household_id=household_id,
        created_by=member_id,
        payload=payload,
        created_at=now,
        expires_at=now + EXPIRES_AFTER,
    )
    session.add(proposal)
    await session.flush()
    await audit.record(
        session, household_id, "proposal.created", ENTITY, proposal.id,
        member_id=member_id, actor=Actor.AGENT,
    )  # fmt: skip
    return proposal


async def close_pending(
    session: AsyncSession,
    conversation_id: uuid.UUID,
    status: ProposalStatus,
    member_id: uuid.UUID,
    proposal_id: uuid.UUID | None = None,
) -> None:
    """Move pending Proposals (one, or all in the Conversation) to `status`. One that's
    past its expiry becomes expired instead, whatever was asked."""
    now = utcnow()
    query = select(Proposal).where(
        Proposal.conversation_id == conversation_id,
        Proposal.status == ProposalStatus.PENDING,
    )
    if proposal_id is not None:
        query = query.where(Proposal.id == proposal_id)
    for proposal in (await session.execute(query.with_for_update())).scalars():
        final = ProposalStatus.EXPIRED if proposal.expires_at <= now else status
        proposal.status = final
        proposal.decided_at = now
        await audit.record(
            session, proposal.household_id, f"proposal.{final.value}", ENTITY, proposal.id,
            member_id=member_id,
        )  # fmt: skip


async def get_mine(session: AsyncSession, ctx: MemberContext, proposal_id: uuid.UUID) -> Proposal:
    """Only the Member who started the Conversation may see or decide its Proposals.
    Anyone else, in this Household or another, gets "not found"."""
    proposal = await session.scalar(
        select(Proposal).where(
            Proposal.id == proposal_id,
            Proposal.household_id == ctx.household.id,
            Proposal.created_by == ctx.member.id,
        )
    )
    if proposal is None:
        raise errors.NotFound("Proposal not found")
    return proposal


async def expire_if_due(session: AsyncSession, proposal: Proposal, now: datetime) -> bool:
    """Expiry is checked when someone acts, not by a background job."""
    if proposal.status != ProposalStatus.PENDING or proposal.expires_at > now:
        return False
    await session.execute(
        update(Proposal)
        .where(Proposal.id == proposal.id, Proposal.status == ProposalStatus.PENDING)
        .values(status=ProposalStatus.EXPIRED, decided_at=now)
    )
    await audit.record(
        session, proposal.household_id, "proposal.expired", ENTITY, proposal.id,
        member_id=proposal.created_by,
    )  # fmt: skip
    return True


def check_keep(
    payload: dict[str, Any], keep_meals: list[date] | None, keep_additions: list[int] | None
) -> None:
    """The Member can only untick what was proposed, not add to it."""
    proposed = {m["date"] for m in payload["meals"]}
    if keep_meals is not None and not {d.isoformat() for d in keep_meals} <= proposed:
        raise errors.InvalidInput("keep_meals has a day that isn't in this Proposal")
    count = len(payload["list_additions"])
    if keep_additions is not None and not all(0 <= i < count for i in keep_additions):
        raise errors.InvalidInput("keep_additions has an item that isn't in this Proposal")


async def latest_decision(session: AsyncSession, conversation_id: uuid.UUID) -> str | None:
    """For the agent's next turn: how the Member answered the newest Proposal."""
    newest = await session.scalar(
        select(Proposal)
        .where(Proposal.conversation_id == conversation_id)
        .order_by(Proposal.created_at.desc())
        .limit(1)
    )
    if newest is None:
        return None
    if newest.status == ProposalStatus.APPROVED and newest.outcome:
        return f"approved. {newest.outcome['message']}"
    if newest.status == ProposalStatus.REJECTED:
        return "rejected."
    return None


# --- commit ----------------------------------------------------------------------------


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _message(saved: int, added: int, skipped: int) -> str:
    """The confirmation the Member sees. Written by code: no LLM call (slice 6 decision)."""
    parts = []
    if saved:
        parts.append(f"Saved {_plural(saved, 'meal')}")
    if added:
        parts.append(("added " if parts else "Added ") + f"{_plural(added, 'item')} to the list")
    text = (" and ".join(parts) + ".") if parts else "Nothing was saved."
    if skipped:
        text += f" Skipped {skipped}: see below."
    return text


async def commit(
    session: AsyncSession,
    ctx: MemberContext,
    proposal_id: uuid.UUID,
    keep_meals: list[str] | None,
    keep_additions: list[int] | None,
    today: date,
) -> dict[str, Any]:
    """Approve: write the kept meals and list additions, in the caller's transaction.

    The product owner's rules (2026-11-15):
    - a meal that no longer passes the checks (Rules changed, recipe gone, day passed)
      is skipped and the rest saved
    - a meal on a day that already has one replaces it, unless that one was Cooked
    - an addition whose Ingredient (or name) is already unticked on the list is skipped
    """
    hid = ctx.household.id
    # Lock order matches the rest of the app: Kitchen (Household row), then the list.
    await kitchen.lock(session, hid)
    proposal = await session.scalar(
        select(Proposal).where(Proposal.id == proposal_id).with_for_update()
    )
    assert proposal is not None
    if proposal.status == ProposalStatus.APPROVED:
        assert proposal.outcome is not None
        return proposal.outcome  # already done: same answer, nothing repeated
    if proposal.status != ProposalStatus.PENDING:
        raise errors.Conflict(f"This plan was already {proposal.status.value}")

    payload = proposal.payload
    meals = [m for m in payload["meals"] if keep_meals is None or m["date"] in keep_meals]
    additions = [
        a
        for i, a in enumerate(payload["list_additions"])
        if keep_additions is None or i in keep_additions
    ]
    skipped: list[str] = []

    # Meals: re-check against today's recipes and Dietary Rules.
    found = await recipes.get_many(session, hid, [m["recipe_id"] for m in meals])
    rules = await diet.get_rules(session, hid)
    draft = Draft(
        meals={
            m["date"]: DraftMeal(recipe_id=m["recipe_id"], servings=m["servings"]) for m in meals
        },
        list_additions=[],
    )
    problems = {p.date: p for p in validate_draft(draft, found, rules, today) if p.date is not None}
    days = [date.fromisoformat(m["date"]) for m in meals]
    existing = (
        {
            pm.date: pm
            for pm in await meal_plan.between(session, hid, min(days), max(days), for_update=True)
        }
        if days
        else {}
    )
    saved = 0
    for meal in meals:
        day = date.fromisoformat(meal["date"])
        title = meal["title"]
        problem = problems.get(meal["date"])
        if problem is not None:
            reason = {
                "unknown_recipe": f"{day:%a}: {title} is no longer in the recipe library",
                "date": f"{day:%a}: {title}, that day has passed",
            }.get(problem.kind, problem.message)
            skipped.append(reason)
            continue
        current = existing.get(day)
        if current is not None and current.cooked_at is not None:
            skipped.append(
                f"{day:%a}: {current.recipe.title} was already cooked, so {title} wasn't added"
            )
            continue
        if current is not None:
            current.recipe_id = uuid.UUID(meal["recipe_id"])
            current.servings = meal["servings"]
            current.proposal_id = proposal.id
        else:
            session.add(
                PlannedMeal(
                    household_id=hid,
                    date=day,
                    recipe_id=uuid.UUID(meal["recipe_id"]),
                    servings=meal["servings"],
                    proposal_id=proposal.id,
                )
            )
        saved += 1
    if saved:
        await meal_plan.bump(session, hid)

    # List additions: onto the one list, untagged, marked as the agent's.
    view = await shopping_lists.get_household_list(session, ctx)
    unticked = [i for i in view.items if i.checked_at is None]
    on_list_ids = {i.ingredient_id for i in unticked if i.ingredient_id is not None}
    on_list_names = {ingredients.normalise(i.text) for i in unticked}
    added = 0
    for addition in additions:
        name = addition["name"]
        ingredient_id = addition.get("ingredient_id")
        if ingredient_id is None:
            match = await ingredients.resolve(session, hid, name, create=False)
            ingredient_id = str(match.id) if match else None
        if (ingredient_id and uuid.UUID(ingredient_id) in on_list_ids) or (
            ingredients.normalise(name) in on_list_names
        ):
            skipped.append(f"{name} is already on the list")
            continue
        quantity = addition.get("quantity")
        item = await shopping_lists.add_item(
            session,
            ctx,
            view.shopping_list.id,
            name,
            Decimal(str(quantity)) if quantity is not None else None,
            addition.get("unit"),
            ingredient_id=uuid.UUID(ingredient_id) if ingredient_id else None,
            added_by=AddedBy.AGENT,
        )
        if item.ingredient_id is not None:
            on_list_ids.add(item.ingredient_id)
        on_list_names.add(ingredients.normalise(name))
        added += 1

    outcome: dict[str, Any] = {
        "message": _message(saved, added, len(skipped)),
        "saved_meals": saved,
        "added_items": added,
        "skipped": skipped,
    }
    proposal.status = ProposalStatus.APPROVED
    proposal.decided_at = utcnow()
    proposal.outcome = outcome
    await audit.record(
        session, hid, "proposal.approved", ENTITY, proposal.id,
        member_id=ctx.member.id, detail=outcome,
    )  # fmt: skip
    return outcome
