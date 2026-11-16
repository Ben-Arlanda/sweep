"""The Household's daily token budget (plan §7): the cost ceiling for every model call.

The planning agent and the import doors (slice 4d) share one budget per Household per
day, kept in `agent_usage`. Every input token counts, cached or not: it's a safety
limit, so it errs on the side of counting too much.
"""

import uuid
from datetime import date

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm_costs import Usage
from app.models import AgentUsage


async def tokens_used_today(session: AsyncSession, household_id: uuid.UUID, day: date) -> int:
    row = await session.get(AgentUsage, (household_id, day))
    return row.input_tokens + row.output_tokens if row else 0


async def add_usage(
    session: AsyncSession, household_id: uuid.UUID, day: date, usage: Usage
) -> None:
    """Add one call's tokens. An upsert, so two calls at once both count."""
    await session.execute(
        insert(AgentUsage)
        .values(
            household_id=household_id,
            day=day,
            input_tokens=usage.all_input,
            output_tokens=usage.output_tokens,
        )
        .on_conflict_do_update(
            index_elements=["household_id", "day"],
            set_={
                "input_tokens": AgentUsage.input_tokens + usage.all_input,
                "output_tokens": AgentUsage.output_tokens + usage.output_tokens,
            },
        )
    )
