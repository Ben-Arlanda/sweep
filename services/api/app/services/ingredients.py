"""Turning what a Member typed into an Ingredient, without guessing.

Visibility (ADR 0012): a Household sees the starter Ingredients plus its own Household
Ingredients, never another Household's. Every query here takes the caller's Household
and applies `visible_to`; code elsewhere that reads `ingredients` must do the same.

Matching is deliberately strict: exact name, then alias, then simple plural/singular
forms. No fuzzy matching. A wrong match would quietly put the wrong thing in the
Kitchen; an unknown name instead becomes a Household Ingredient, and the Member fixes a
near-miss ("chocolate" should be dark chocolate) with a link.
"""

import re
import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HouseholdIngredientLink, Ingredient, IngredientAlias

SEARCH_LIMIT = 20
NAME_MAX = 80  # ingredients.name is VARCHAR(80)

# The shared starter set. Names are unique per owner, so a lookup by name must say whose.
STARTERS: ColumnElement[bool] = Ingredient.household_id.is_(None)


def visible_to(household_id: uuid.UUID) -> ColumnElement[bool]:
    """The rows this Household may see: starters and its own."""
    return or_(STARTERS, Ingredient.household_id == household_id)


def normalise(text: str) -> str:
    """Lower-case, punctuation to spaces, single spaces: "Chicken  Thighs!" → "chicken thighs"."""
    return " ".join(re.sub(r"[^\w\s-]", " ", text.lower()).split())


def variants(name: str) -> list[str]:
    """The name, then simple singular/plural forms of its last word."""
    words = name.split(" ")
    last = words[-1]
    forms = [last]
    if last.endswith("ies"):
        forms.append(last[:-3] + "y")
    if last.endswith("es"):
        forms.append(last[:-2])
    if last.endswith("s"):
        forms.append(last[:-1])
    else:
        forms += [last + "s", last + "es"]
    return [" ".join([*words[:-1], form]) for form in forms]


async def resolve(
    session: AsyncSession, household_id: uuid.UUID, text: str, *, create: bool
) -> Ingredient | None:
    """The one matcher (ADR 0012), used by the list, the Kitchen, the agent and recipe lines.

    Lookup order, each step trying the name and its simple plural/singular forms:
      1. this Household's links ("chocolate" → dark chocolate): the Member said so
      2. starter names and aliases
      3. this Household's own Ingredients
      4. with `create`, a new Household Ingredient, so nothing a Member types is refused

    Callers acting on a Member's words pass create=True. The agent passes False: a model's
    guess must never add Ingredients.
    """
    name = normalise(text)
    if not name:
        return None
    forms = variants(name)
    linked = (
        await session.execute(
            select(Ingredient)
            .join(HouseholdIngredientLink, HouseholdIngredientLink.ingredient_id == Ingredient.id)
            .where(
                HouseholdIngredientLink.household_id == household_id,
                HouseholdIngredientLink.name.in_(forms),
                visible_to(household_id),  # a link can only point at what we may see
            )
            .order_by((HouseholdIngredientLink.name == name).desc())  # exact spelling first
            .limit(1)
        )
    ).scalar_one_or_none()
    if linked is not None:
        return linked
    for owner in (STARTERS, Ingredient.household_id == household_id):
        found = await _by_name(session, owner, forms)
        if found is not None:
            return found
    if not create or len(name) > NAME_MAX:
        return None  # 80+ characters is a note, not a thing; it stays unlinked
    return await _create(session, household_id, name)


async def _by_name(
    session: AsyncSession, owner: ColumnElement[bool], forms: list[str]
) -> Ingredient | None:
    """Try each form in order ("tomatoes" before "tomatoe"), names and aliases alike."""
    for candidate in forms:
        found = (
            await session.execute(
                select(Ingredient)
                .outerjoin(IngredientAlias, IngredientAlias.ingredient_id == Ingredient.id)
                .where(or_(Ingredient.name == candidate, IngredientAlias.alias == candidate), owner)
                .limit(1)
            )
        ).scalar_one_or_none()
        if found is not None:
            return found
    return None


async def _create(session: AsyncSession, household_id: uuid.UUID, name: str) -> Ingredient:
    """A Household Ingredient: category "other" (so the Cupboard), counted, no density.

    ON CONFLICT DO NOTHING, then read: two Members adding "kale" at the same moment both
    end up with the same row instead of one of them getting an error.
    """
    await session.execute(
        insert(Ingredient)
        .values(
            id=uuid.uuid4(),
            household_id=household_id,
            name=name,
            category="other",
            default_unit="count",
            is_default_staple=False,
        )
        .on_conflict_do_nothing(constraint="uq_ingredients_household_id_name")
    )
    return (
        await session.execute(
            select(Ingredient).where(
                Ingredient.household_id == household_id, Ingredient.name == name
            )
        )
    ).scalar_one()


async def set_link(
    session: AsyncSession, household_id: uuid.UUID, text: str, ingredient: Ingredient | None
) -> None:
    """Remember what this Household means by `text` (None forgets it). Called when a Member
    relinks a list item; the matcher then sends future items with that name the same way.

    The caller has already checked the Ingredient is visible to this Household.
    """
    name = normalise(text)
    if not name or len(name) > NAME_MAX:
        return
    if ingredient is None or ingredient.name == name:
        # Unlinked, or linked to what the name already means: no link needed.
        await session.execute(
            delete(HouseholdIngredientLink).where(
                HouseholdIngredientLink.household_id == household_id,
                HouseholdIngredientLink.name == name,
            )
        )
        return
    await session.execute(
        insert(HouseholdIngredientLink)
        .values(household_id=household_id, name=name, ingredient_id=ingredient.id)
        .on_conflict_do_update(
            index_elements=["household_id", "name"], set_={"ingredient_id": ingredient.id}
        )
    )


async def search(session: AsyncSession, household_id: uuid.UUID, query: str) -> list[Ingredient]:
    """Ingredients whose name or an alias contains the query.

    Ranked: exact name or alias first ("flour" → plain flour), then names starting with
    the query, then the rest alphabetically.
    """
    q = normalise(query)
    if not q:
        return []
    pattern = f"%{q.replace('%', '').replace('_', '')}%"
    names = select(Ingredient.id).where(Ingredient.name.like(pattern))
    aliases = select(IngredientAlias.ingredient_id).where(IngredientAlias.alias.like(pattern))
    exact_alias = select(IngredientAlias.ingredient_id).where(IngredientAlias.alias == q)
    rows = await session.execute(
        select(Ingredient)
        .where(or_(Ingredient.id.in_(names), Ingredient.id.in_(aliases)), visible_to(household_id))
        .order_by(
            or_(Ingredient.name == q, Ingredient.id.in_(exact_alias)).desc(),
            Ingredient.name.like(f"{q}%").desc(),
            Ingredient.name,
        )
        .limit(SEARCH_LIMIT)
    )
    return list(rows.scalars())


async def get(
    session: AsyncSession, household_id: uuid.UUID, ingredient_id: uuid.UUID
) -> Ingredient | None:
    """None for an unknown id *and* for another Household's: callers answer 404 either way,
    so the response never confirms an id exists somewhere else."""
    return (
        await session.execute(
            select(Ingredient).where(Ingredient.id == ingredient_id, visible_to(household_id))
        )
    ).scalar_one_or_none()


async def names(session: AsyncSession, ids: Sequence[str | None]) -> dict[str, str]:
    """Ingredient id → name for the ids given (None and unknown ids are left out)."""
    wanted = {uuid.UUID(i) for i in ids if i is not None}
    if not wanted:
        return {}
    found = await session.execute(
        select(Ingredient.id, Ingredient.name).where(Ingredient.id.in_(wanted))
    )
    return {str(iid): name for iid, name in found.all()}
