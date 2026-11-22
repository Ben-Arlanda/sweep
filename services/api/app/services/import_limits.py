"""Limits on the doors where Sweep reads what a Member sends: the recipe imports (paste,
photo, file, link; slice 4d) and Kitchen Photos (slice 3e, ADR 0023). One shared count.

- At most MAX_PER_HOUR attempts per Member in any hour (429 + Retry-After).
- The model doors also need budget left today (the Household's, shared with the agent).
  Once it's spent they wait until midnight in Sydney (429 + Retry-After).
- Every model call's tokens are added to that budget as soon as the call returns
  (`MeteredReader`), even when the answer then turns out not to be a recipe.

Counted in Postgres (`recipe_imports`) like the agent's turns, so the limit holds
across every copy of the API. Typing a recipe isn't limited: no model, nothing fetched.
"""

import math
import uuid
from collections.abc import Sequence
from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import errors
from app.agent.prompt import today_in_sydney
from app.data.places import Place
from app.llm_costs import Usage
from app.models import RecipeImport, utcnow
from app.services import token_budget
from app.services.households import MemberContext
from app.services.kitchen_photos import KitchenPhotoReader, KitchenPhotoReading
from app.services.recipe_import import Photo, RecipeReader, RecipeReading

MAX_PER_HOUR = 20
WINDOW = timedelta(hours=1)
SYDNEY = ZoneInfo("Australia/Sydney")

Door = Literal["paste", "photo", "file", "link", "kitchen"]

# What the Member can do instead, per door.
_INSTEAD = {"kitchen": "add them by hand"}
_TOO_MANY = {"kitchen": "photos"}


async def start(
    session: AsyncSession, ctx: MemberContext, door: Door, *, daily_budget: int | None
) -> None:
    """Check the limits and record the attempt, in one committed transaction.
    `daily_budget`: None for a door that uses no model (link)."""
    now = utcnow()
    # Check-then-insert races: two uploads at once would both see 19. A lock per
    # Member, held until commit, makes them take turns at this check.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
        {"k": f"recipe-import:{ctx.member.id}"},
    )
    recent = list(
        (
            await session.scalars(
                select(RecipeImport.started_at)
                .where(
                    RecipeImport.member_id == ctx.member.id,
                    RecipeImport.started_at > now - WINDOW,
                )
                .order_by(RecipeImport.started_at.desc())
                .limit(MAX_PER_HOUR)
            )
        ).all()
    )
    if len(recent) >= MAX_PER_HOUR:
        wait = _seconds_until(recent[-1] + WINDOW, now)  # when the oldest turns an hour
        raise errors.RateLimited(
            f"That's a lot of {_TOO_MANY.get(door, 'recipes')} for one hour. "
            f"Try again in {_minutes(wait)}, or {_INSTEAD.get(door, 'type it in')}.",
            retry_after=wait,
        )
    if daily_budget is not None:
        used = await token_budget.tokens_used_today(session, ctx.household.id, today_in_sydney())
        if used >= daily_budget:
            raise errors.RateLimited(
                "Sweep has done all the reading it can for your household today. "
                f"It resets tomorrow, or you can {_INSTEAD.get(door, 'type the recipe in')}.",
                retry_after=_seconds_until(_next_midnight(now), now),
            )
    session.add(RecipeImport(member_id=ctx.member.id, door=door, started_at=now))
    await session.commit()


class MeteredReader:
    """The recipe reader, with every call's tokens added to the Household's budget the
    moment it returns, in a transaction of its own (the request's may roll back)."""

    def __init__(
        self,
        inner: RecipeReader,
        sessionmaker: async_sessionmaker[AsyncSession],
        household_id: uuid.UUID,
    ) -> None:
        self._inner, self._sessionmaker, self._household_id = inner, sessionmaker, household_id

    async def read(
        self, text: str, cuisines: Sequence[str], layout: str | None = None
    ) -> tuple[RecipeReading | None, Usage]:
        return await self._count(await self._inner.read(text, cuisines, layout))

    async def read_photos(
        self, photos: Sequence[Photo], cuisines: Sequence[str]
    ) -> tuple[RecipeReading | None, Usage]:
        return await self._count(await self._inner.read_photos(photos, cuisines))

    async def read_document(
        self, pdf: bytes, cuisines: Sequence[str]
    ) -> tuple[RecipeReading | None, Usage]:
        return await self._count(await self._inner.read_document(pdf, cuisines))

    async def _count(
        self, answer: tuple[RecipeReading | None, Usage]
    ) -> tuple[RecipeReading | None, Usage]:
        await _add_usage(self._sessionmaker, self._household_id, answer[1])
        return answer


class MeteredKitchenReader:
    """The Kitchen Photo reader, metered the same way."""

    def __init__(
        self,
        inner: KitchenPhotoReader,
        sessionmaker: async_sessionmaker[AsyncSession],
        household_id: uuid.UUID,
    ) -> None:
        self._inner, self._sessionmaker, self._household_id = inner, sessionmaker, household_id

    async def read_kitchen_photos(
        self, photos: Sequence[Photo], place: Place
    ) -> tuple[KitchenPhotoReading | None, Usage]:
        answer = await self._inner.read_kitchen_photos(photos, place)
        await _add_usage(self._sessionmaker, self._household_id, answer[1])
        return answer


async def _add_usage(
    sessionmaker: async_sessionmaker[AsyncSession], household_id: uuid.UUID, usage: Usage
) -> None:
    """In a transaction of its own: the request's may roll back."""
    async with sessionmaker() as session:
        await token_budget.add_usage(session, household_id, today_in_sydney(), usage)
        await session.commit()


def _next_midnight(now: datetime) -> datetime:
    tomorrow = now.astimezone(SYDNEY).date() + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=SYDNEY)


def _seconds_until(when: datetime, now: datetime) -> int:
    return max(1, math.ceil((when - now).total_seconds()))


def _minutes(seconds: int) -> str:
    minutes = math.ceil(seconds / 60)
    return "a minute" if minutes == 1 else f"{minutes} minutes"
