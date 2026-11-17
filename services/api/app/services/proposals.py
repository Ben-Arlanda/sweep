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
from app.agent.state import Draft, DraftAdaptation, DraftMeal, DraftSwap
from app.agent.validate import validate_draft
from app.models import Actor, AddedBy, PlannedMeal, Proposal, ProposalStatus, utcnow
from app.services import (
    adaptations,
    audit,
    diet,
    ingredients,
    kitchen,
    meal_plan,
    recipes,
    shopping_lists,
)
from app.services.households import MemberContext
from app.units import top_up

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


def _draft_meal(meal: dict[str, Any]) -> DraftMeal:
    """A Proposal's meal back as a Draft meal, Swaps included (ADR 0021)."""
    out = DraftMeal(recipe_id=meal["recipe_id"], servings=meal["servings"])
    adaptation = meal.get("adaptation")
    if adaptation is not None:
        out["adaptation"] = DraftAdaptation(
            label=adaptation["label"],
            swaps=[
                DraftSwap(position=s["position"], raw_text=s["raw_text"])
                for s in adaptation["swaps"]
            ],
        )
    return out


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _message(saved: int, added: int, topped_up: int, skipped: int) -> str:
    """The confirmation the Member sees. Written by code: no LLM call (slice 6 decision)."""
    parts = []
    if saved:
        parts.append(f"saved {_plural(saved, 'meal')}")
    if added:
        parts.append(f"added {_plural(added, 'item')} to the list")
    if topped_up:
        parts.append(f"topped up {topped_up} already there")
    if parts:
        joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
        text = joined[0].upper() + joined[1:] + "."
    else:
        text = "Nothing was saved."
    if skipped:
        text += f" Skipped {skipped}: see below."
    return text


def _cant_top_up(name: str, have: Decimal | None, extra: Decimal | None, unit: str | None) -> str:
    if extra is None:
        return f"{name} is already on the list"
    more = shopping_lists.amount_text(extra, unit)
    if have is None:
        return f"{name} is already on the list with no amount: make sure it covers {more} more"
    return f"{name} is already on the list in a different unit: add {more} more yourself"


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
    - with no `keep_additions`, an unexplained addition (no meal uses it, the Member
      didn't ask for it) is left off: only a Member ticking it on purpose adds it
      (slice 10). Proposals saved before reasons existed have none and are all kept.
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
    skipped: list[str] = []
    kept_additions = []
    for i, item in enumerate(payload["list_additions"]):
        if keep_additions is not None:
            if i in keep_additions:
                kept_additions.append(i)
        elif item.get("reason") == "unexplained":
            skipped.append(f"{item['name']}: not for any meal, so it wasn't added")
        else:
            kept_additions.append(i)
    additions = [payload["list_additions"][i] for i in kept_additions]

    # Meals: re-check against today's recipes and Dietary Rules, Swaps included.
    found = await recipes.get_many(session, hid, [m["recipe_id"] for m in meals])
    rules = await diet.get_rules(session, hid)
    draft = Draft(meals={m["date"]: _draft_meal(m) for m in meals}, list_additions=[])
    adapted, refused = await adaptations.for_draft(session, hid, draft["meals"])
    checked = validate_draft(draft, found, rules, today, adapted=adapted, refused=refused)
    problems = {p.date: p for p in checked if p.date is not None}
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
                "swap": f"{day:%a}: {title} can't be made now: {refused.get(meal['date'])}",
            }.get(problem.kind, problem.message)
            skipped.append(reason)
            continue
        current = existing.get(day)
        if current is not None and current.cooked_at is not None:
            skipped.append(
                f"{day:%a}: {current.recipe.title} was already cooked, so {title} wasn't added"
            )
            continue
        recipe_id = uuid.UUID(meal["recipe_id"])
        if meal["date"] in adapted:  # approving makes the Adaptation (or reuses a kept one)
            planned = draft["meals"][meal["date"]]
            assert "adaptation" in planned
            kept = await adaptations.create(
                session, hid, recipe_id, adaptations.swaps_in(planned),
                planned["adaptation"]["label"],
            )  # fmt: skip
            recipe_id = kept.id
        if current is not None:
            current.recipe_id = recipe_id
            current.servings = meal["servings"]
            current.proposal_id = proposal.id
        else:
            session.add(
                PlannedMeal(
                    household_id=hid,
                    date=day,
                    recipe_id=recipe_id,
                    servings=meal["servings"],
                    proposal_id=proposal.id,
                )
            )
        saved += 1
    if saved:
        await meal_plan.bump(session, hid)

    # List additions: onto the one list, untagged, marked as the agent's.
    view = await shopping_lists.get_household_list(session, ctx)
    items = list(view.items)
    added = 0
    topped_up: list[str] = []
    for addition in additions:
        name = addition["name"]
        ingredient_id = addition.get("ingredient_id")
        if ingredient_id is None:
            match = await ingredients.resolve(session, hid, name, create=False)
            ingredient_id = str(match.id) if match else None
        iid = uuid.UUID(ingredient_id) if ingredient_id else None
        quantity = addition.get("quantity")
        extra = Decimal(str(quantity)) if quantity is not None else None
        unit = addition.get("unit")

        # An addition is the extra to buy (ADR 0016). Already on the list, unticked: top
        # that line up if the amounts combine honestly; otherwise skip and say what to check.
        listed = shopping_lists.unticked_match(items, iid, name)
        if listed is not None:
            ingredient = listed.ingredient
            total = (
                top_up(
                    listed.quantity,
                    listed.unit,
                    extra,
                    unit,
                    ingredient.default_unit,
                    ingredient.grams_per_ml,
                )
                if ingredient is not None
                else None
            )
            if total is None:
                skipped.append(_cant_top_up(name, listed.quantity, extra, unit))
                continue
            before = shopping_lists.amount_text(listed.quantity, listed.unit)
            await shopping_lists.edit_item(
                session, ctx, view.shopping_list.id, listed.id, quantity=total
            )
            after = shopping_lists.amount_text(total, listed.unit)
            topped_up.append(f"{name}: {before} → {after}")
            continue

        item = await shopping_lists.add_item(
            session,
            ctx,
            view.shopping_list.id,
            name,
            extra,
            unit,
            ingredient_id=iid,
            added_by=AddedBy.AGENT,
        )
        items.append(item)
        added += 1

    outcome: dict[str, Any] = {
        "message": _message(saved, added, len(topped_up), len(skipped)),
        "saved_meals": saved,
        "added_items": added,
        "skipped": skipped,
        "topped_up": topped_up,
        # What the Member left ticked (before any skips), so the chat can show it later.
        "kept_meals": [m["date"] for m in meals],
        "kept_additions": kept_additions,
    }
    proposal.status = ProposalStatus.APPROVED
    proposal.decided_at = utcnow()
    proposal.outcome = outcome
    await audit.record(
        session, hid, "proposal.approved", ENTITY, proposal.id,
        member_id=ctx.member.id, detail=outcome,
    )  # fmt: skip
    return outcome
