"""Kitchen Match (ADR 0013): how well a recipe fits what's in the Kitchen.

Plans start from what the Household has, so ranking recipes is the app's job, done in
plain code where it can be tested; the agent chooses among the results and explains.

Each needed line (not optional) of a recipe is one of:

    have     a Staple marked "have", or a Tracked item that's Confirmed or Estimated
    maybe    a Tracked item whose status is Unknown (might not be there any more)
    missing  anything else that has an Ingredient

A line with no Ingredient ("water", something unrecognised) is ignored, unless its text
names one of the Household's own Ingredients as a whole word ("2 finger limes"): Seed
Recipes can't link to Household Ingredients (ADR 0012), so this is how they still count.
Amounts aren't compared here; check_kitchen_coverage works out how much to buy.

Ranking is "fewest things to buy": missing, then maybe, then Favourites (ADR 0025: they
win ties, never beat a recipe needing less), then the most Tracked items used (so a
recipe that uses what you bought beats a pantry-only one), then title.
"""

import re
import uuid
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ingredient, Recipe, RecipeIngredient, utcnow
from app.services import kitchen
from app.services.households import MemberContext
from app.services.ingredients import normalise, variants
from app.services.recipes import RecipeFilters, eligible


@dataclass(frozen=True)
class KitchenSnapshot:
    have: frozenset[uuid.UUID]  # Staples marked "have" + trusted Tracked items
    maybe: frozenset[uuid.UUID]  # Tracked items with Unknown status
    tracked: frozenset[uuid.UUID]  # every Tracked item (to count what a recipe uses up)
    own_names: Mapping[str, uuid.UUID]  # the Household's own Ingredients, by name


@dataclass(frozen=True)
class Line:
    ingredient_id: uuid.UUID | None
    name: str | None  # the Ingredient's name, when linked
    raw_text: str
    optional: bool = False


@dataclass(frozen=True)
class Match:
    have: tuple[str, ...]
    maybe: tuple[str, ...]
    missing: tuple[str, ...]
    tracked_used: int  # Tracked items (not Staples) this recipe uses: have or maybe


def match(lines: Iterable[Line], snapshot: KitchenSnapshot) -> Match:
    """Sort a recipe's needed lines into have / maybe / missing. Pure: no database."""
    own = _own_patterns(snapshot.own_names)
    seen: set[uuid.UUID] = set()
    have: list[str] = []
    maybe: list[str] = []
    missing: list[str] = []
    for line in lines:
        if line.optional:
            continue
        found = _identify(line, own)
        if found is None or found[0] in seen:
            continue
        ingredient_id, name = found
        seen.add(ingredient_id)
        if ingredient_id in snapshot.have:
            have.append(name)
        elif ingredient_id in snapshot.maybe:
            maybe.append(name)
        else:
            missing.append(name)
    used = sum(1 for i in seen if i in snapshot.tracked)
    return Match(tuple(have), tuple(maybe), tuple(missing), used)


def uses(lines: Iterable[Line], snapshot: KitchenSnapshot) -> list[str]:
    """The Tracked items a recipe uses that are trusted to be there, in recipe order
    ("uses your chicken thigh and rice" on Home). Staples are left out: every recipe
    uses oil and salt, so naming them says nothing. Unknown items are left out too:
    they might not be there any more. Pure: no database."""
    own = _own_patterns(snapshot.own_names)
    used: dict[uuid.UUID, str] = {}
    for line in lines:
        found = None if line.optional else _identify(line, own)
        if found is None:
            continue
        ingredient_id, name = found
        if ingredient_id in snapshot.tracked and ingredient_id in snapshot.have:
            used.setdefault(ingredient_id, name)
    return list(used.values())


def rank_key(title: str, m: Match, favourite: bool = False) -> tuple[int, int, bool, int, str]:
    """Sort key: fewest missing, then fewest unsure, then Favourites, then uses the most,
    then A to Z."""
    return (len(m.missing), len(m.maybe), not favourite, -m.tracked_used, title)


def _identify(
    line: Line, own: list[tuple[re.Pattern[str], str, uuid.UUID]]
) -> tuple[uuid.UUID, str] | None:
    if line.ingredient_id is not None:
        return line.ingredient_id, line.name or ""
    text = normalise(line.raw_text)
    for pattern, name, ingredient_id in own:
        if pattern.search(text):
            return ingredient_id, name
    return None


def _own_patterns(names: Mapping[str, uuid.UUID]) -> list[tuple[re.Pattern[str], str, uuid.UUID]]:
    """Whole-word patterns for each name and its simple plurals, longest name first, so
    "finger lime" wins over "lime" and "sublime" never matches "lime"."""
    return [
        (re.compile(r"\b(?:" + "|".join(map(re.escape, variants(name))) + r")\b"), name, i)
        for name, i in sorted(names.items(), key=lambda kv: -len(kv[0]))
    ]


def mentions(recipe: Recipe, name: str) -> bool:
    """Does any line of this recipe name `name` as a whole word (or simple plural)?"""
    [(pattern, _, _)] = _own_patterns({name: uuid.UUID(int=0)})
    return any(pattern.search(normalise(row.raw_text)) for row in recipe.ingredients)


# --- Loading from the database -------------------------------------------------------


async def snapshot(session: AsyncSession, ctx: MemberContext) -> KitchenSnapshot:
    view = await kitchen.get_kitchen(session, ctx)
    now = utcnow()
    trusted = {
        i.ingredient_id for i in view.tracked if kitchen.status_of(i, now) != kitchen.Status.UNKNOWN
    }
    unsure = {i.ingredient_id for i in view.tracked} - trusted
    staples = {s.ingredient_id for s in view.staples if s.ran_out_at is None}
    own = await session.execute(
        select(Ingredient.name, Ingredient.id).where(Ingredient.household_id == ctx.household.id)
    )
    return KitchenSnapshot(
        have=frozenset(trusted | staples),
        maybe=frozenset(unsure),
        tracked=frozenset(trusted | unsure),
        own_names={name: ingredient_id for name, ingredient_id in own},
    )


def lines_of(recipe: Recipe) -> list[Line]:
    return [_line(r) for r in recipe.ingredients]


def _line(row: RecipeIngredient) -> Line:
    return Line(
        ingredient_id=row.ingredient_id,
        name=row.ingredient.name if row.ingredient else None,
        raw_text=row.raw_text,
        optional=row.optional,
    )


async def rank(
    session: AsyncSession,
    household_id: uuid.UUID,
    snap: KitchenSnapshot,
    filters: RecipeFilters,
    *,
    among: Sequence[uuid.UUID] | None = None,
    exclude: Sequence[uuid.UUID] = (),
    favourites: Collection[uuid.UUID] = frozenset(),
    limit: int,
) -> list[tuple[Recipe, Match]]:
    """The best Kitchen Matches among the recipes this Household may see and eat.

    `among` limits it to some recipes (the top results of a search by meaning: that's
    the hybrid case, where meaning finds candidates and the Kitchen orders them).
    `favourites` win ties: pass favourites.boosted (none in New recipes mode).
    """
    found = await eligible(session, household_id, filters, among=among, exclude=exclude)
    scored = [(r, match(lines_of(r), snap)) for r in found]
    scored.sort(key=lambda pair: rank_key(pair[0].title, pair[1], pair[0].id in favourites))
    return scored[:limit]
