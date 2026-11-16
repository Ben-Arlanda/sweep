"""Rate limits on the agent (slice 10).

- One turn at a time per Member, across all their Conversations, so opening five
  chats can't run five turns at once (409).
- At most MAX_PER_HOUR messages per Member in any hour (429 + Retry-After).

Counted in Postgres (`agent_turns`), not in memory, so the limits hold across every
copy of the API (slice 11). The Household's daily token budget stays the cost ceiling;
these stop one Member flooding the agent, by mistake or on purpose.
"""

import math
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import errors
from app.models import AgentTurn, utcnow

MAX_PER_HOUR = 30
WINDOW = timedelta(hours=1)
# A turn with no finished_at counts as running for this long. A server that dies
# mid-turn never finishes its row; without a cut-off the Member would be locked out.
# Longer than the turn timeout (60s), so a slow turn that's still going isn't missed.
RUNNING_FOR_AT_MOST = timedelta(minutes=2)


async def start(
    session: AsyncSession, member_id: uuid.UUID, conversation_id: uuid.UUID
) -> uuid.UUID:
    """Check both limits and record the turn, in one committed transaction."""
    now = utcnow()
    # Check-then-insert races: two messages at once would both see "nothing running".
    # A lock per Member, held until commit, makes them take turns at this check.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
        {"k": f"agent-turn:{member_id}"},
    )
    mine = AgentTurn.member_id == member_id
    running = await session.scalar(
        select(func.count())
        .select_from(AgentTurn)
        .where(
            mine,
            AgentTurn.finished_at.is_(None),
            AgentTurn.started_at > now - RUNNING_FOR_AT_MOST,
        )
    )
    if running:
        raise errors.TurnInProgress(
            "Sweep is still answering your last message, maybe on another device. "
            "Try again when it's done."
        )

    recent = list(
        (
            await session.scalars(
                select(AgentTurn.started_at)
                .where(mine, AgentTurn.started_at > now - WINDOW)
                .order_by(AgentTurn.started_at.desc())
                .limit(MAX_PER_HOUR)
            )
        ).all()
    )
    if len(recent) >= MAX_PER_HOUR:
        # A slot frees when the oldest of the last MAX_PER_HOUR turns turns an hour old.
        wait = _seconds_until(recent[-1] + WINDOW, now)
        raise errors.RateLimited(
            f"That's a lot of messages. Try again in {_minutes(wait)}.", retry_after=wait
        )

    turn = AgentTurn(member_id=member_id, conversation_id=conversation_id, started_at=now)
    session.add(turn)
    await session.commit()
    return turn.id


async def finish(sessionmaker: async_sessionmaker[AsyncSession], turn_id: uuid.UUID) -> None:
    """Called when the reply stream ends, however it ends. Its own session: the
    request's may already be closed by the time a stream finishes."""
    async with sessionmaker() as session:
        await session.execute(
            update(AgentTurn).where(AgentTurn.id == turn_id).values(finished_at=utcnow())
        )
        await session.commit()


def _seconds_until(when: datetime, now: datetime) -> int:
    return max(1, math.ceil((when - now).total_seconds()))


def _minutes(seconds: int) -> str:
    minutes = math.ceil(seconds / 60)
    return "a minute" if minutes == 1 else f"{minutes} minutes"
