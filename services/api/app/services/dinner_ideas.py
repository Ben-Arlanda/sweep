"""Dinner Ideas (ADR 0025): the best Kitchen Matches for a dinner, chosen by code, not the
agent. "Just tonight" shows them; swapping a day of a plan offers them as alternatives.

Same ranking as the agent's recipes_from_kitchen (kitchen_match.rank), so the screen and
the agent agree: fewest things to buy, Favourites first among equals, mains only, and
the Dietary Rules applied in SQL by filters_for.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings import Embedder, EmbeddingUnavailable
from app.models import Course, Recipe
from app.services import favourites, kitchen_match, recipes
from app.services.households import MemberContext
from app.services.kitchen_match import Match

MAX_IDEAS = 12


@dataclass(frozen=True)
class Idea:
    recipe: Recipe
    match: Match
    kitchen_uses: list[str]  # Tracked items it uses that are there ("uses your chicken")
    favourite: bool


async def ideas(
    session: AsyncSession,
    ctx: MemberContext,
    *,
    max_minutes: int | None = None,
    nothing_to_buy: bool = False,
    exclude: Sequence[uuid.UUID] = (),
    boost_favourites: bool = True,
    among: Sequence[uuid.UUID] | None = None,
    limit: int = 3,
) -> list[Idea]:
    hid = ctx.household.id
    filters = await recipes.filters_for(session, hid, max_minutes, course=Course.MAIN)
    snap = await kitchen_match.snapshot(session, ctx)
    boosted = await favourites.boosted(session, hid) if boost_favourites else set()
    ranked = await kitchen_match.rank(
        session,
        hid,
        snap,
        filters,
        among=among,
        exclude=exclude,
        favourites=boosted,
        # Filtering "nothing to buy" afterwards needs every candidate, not just the top.
        limit=10_000 if nothing_to_buy else limit,
    )
    if nothing_to_buy:
        ranked = [(r, m) for r, m in ranked if not m.missing][:limit]
    hearted = await favourites.ids(session, hid)
    return [
        Idea(r, m, kitchen_match.uses(kitchen_match.lines_of(r), snap), r.id in hearted)
        for r, m in ranked
    ]


TASTE_CANDIDATES = 60


async def by_taste(
    session: AsyncSession, household_id: uuid.UUID, embedder: Embedder, cuisines: Sequence[str]
) -> list[uuid.UUID] | None:
    """New recipes mode: candidates by meaning from the Household's liked cuisines, which
    the Kitchen then orders (the hybrid search recipes_from_kitchen uses). None when
    they like nothing in particular, or search is down: every main is a candidate."""
    if not cuisines:
        return None
    filters = await recipes.filters_for(session, household_id, course=Course.MAIN)
    try:
        found = await recipes.search(
            session, household_id, embedder, " ".join(cuisines), filters, TASTE_CANDIDATES
        )
    except EmbeddingUnavailable:
        return None
    return [r.id for r, _ in found]
