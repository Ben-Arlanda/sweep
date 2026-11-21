"""Dinner Ideas (ADR 0025): the best Kitchen Matches for a dinner, chosen by code, not the
agent. "Just tonight" shows them; swapping a day of a plan offers them as alternatives.

Same ranking as the agent's recipes_from_kitchen (kitchen_match.rank), so the screen and
the agent agree: fewest things to buy, Favourites first among equals, mains only, and
the Dietary Rules applied in SQL by filters_for.
"""

import random
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.diet import Diet
from app.embeddings import Embedder, EmbeddingUnavailable
from app.models import Course, Recipe
from app.services import diet, favourites, kitchen_match, recipes
from app.services.households import MemberContext
from app.services.kitchen_match import Match

MAX_IDEAS = 12
SPECIFIC_CANDIDATES = 10  # "pasta" should mean pastas, then the Kitchen orders them


class Mood(StrEnum):
    """What the Member is in the mood for on the Dinner ideas setup (slice 6f)."""

    KITCHEN = "kitchen"  # fewest things to buy (Just tonight's ranking)
    SURPRISE = "surprise"  # good matches, shuffled once a day
    SPECIFIC = "specific"  # their words first, then the Kitchen


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
    vegetarian: bool = False,
    limit: int = 3,
) -> list[Idea]:
    hid = ctx.household.id
    filters = await _filters(session, hid, max_minutes, vegetarian)
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


async def _filters(
    session: AsyncSession, hid: uuid.UUID, max_minutes: int | None, vegetarian: bool
) -> recipes.RecipeFilters:
    """Mains within the Rules; `vegetarian` adds the diet for this search only, judged
    the same way as a Rule (a new food by its words)."""
    filters = await recipes.filters_for(session, hid, max_minutes, course=Course.MAIN)
    if not vegetarian:
        return filters
    meat = await diet.banned_ingredient_ids(
        session, hid, diet.DietaryRules(frozenset({Diet.VEGETARIAN}))
    )
    return replace(
        filters, exclude_ingredient_ids=sorted(set(filters.exclude_ingredient_ids) | meat)
    )


def shuffled_for_day[T](items: Sequence[T], household_id: uuid.UUID, day: date) -> list[T]:
    """The same order all day for this Household, a new one tomorrow."""
    out = list(items)
    random.Random(f"{household_id}:{day.isoformat()}").shuffle(out)
    return out


async def for_mood(
    session: AsyncSession,
    ctx: MemberContext,
    embedder: Embedder | None,
    mood: Mood,
    *,
    today: date,
    q: str = "",
    max_minutes: int | None = None,
    nothing_to_buy: bool = False,
    vegetarian: bool = False,
    exclude: Sequence[uuid.UUID] = (),
    limit: int = 3,
) -> list[Idea]:
    """Dinner Ideas for a mood. All code: search picks candidates, the Kitchen orders."""
    hid = ctx.household.id
    among: list[uuid.UUID] | None = None
    if mood == Mood.SPECIFIC:
        filters = await _filters(session, hid, max_minutes, vegetarian)
        found = await recipes.search_or_keywords(
            session, hid, embedder, q, filters, SPECIFIC_CANDIDATES
        )
        among = [r.id for r, _ in found]
    elif mood == Mood.SURPRISE and embedder is not None:
        cuisines = (await diet.get_preferences(session, hid)).cuisines
        among = await by_taste(session, hid, embedder, cuisines)
    found_ideas = await ideas(
        session,
        ctx,
        max_minutes=max_minutes,
        nothing_to_buy=nothing_to_buy,
        exclude=exclude,
        among=among,
        vegetarian=vegetarian,
        limit=MAX_IDEAS if mood == Mood.SURPRISE else limit,
    )
    if mood == Mood.SURPRISE:
        return shuffled_for_day(found_ideas, hid, today)[:limit]
    return found_ideas
