"""Turning what a Member typed into an Ingredient, without guessing.

Matching is deliberately strict: exact name, then alias, then simple plural/singular
forms. No fuzzy matching. A wrong link would quietly put the wrong thing in the Cabinet;
no link just means the item doesn't reach the Cabinet, which the app shows. Smarter
matching (embeddings, an LLM fallback) belongs to slice 4's normalisation, with evals.
"""

import re
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ingredient, IngredientAlias

SEARCH_LIMIT = 20


def normalise(text: str) -> str:
    """Lower-case, punctuation to spaces, single spaces: "Chicken  Thighs!" → "chicken thighs"."""
    return " ".join(re.sub(r"[^\w\s-]", " ", text.lower()).split())


def _variants(name: str) -> list[str]:
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


async def match(session: AsyncSession, text: str) -> Ingredient | None:
    name = normalise(text)
    if not name:
        return None
    for candidate in _variants(name):
        found = (
            await session.execute(
                select(Ingredient)
                .outerjoin(IngredientAlias, IngredientAlias.ingredient_id == Ingredient.id)
                .where(or_(Ingredient.name == candidate, IngredientAlias.alias == candidate))
                .limit(1)
            )
        ).scalar_one_or_none()
        if found is not None:
            return found
    return None


async def search(session: AsyncSession, query: str) -> list[Ingredient]:
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
        .where(or_(Ingredient.id.in_(names), Ingredient.id.in_(aliases)))
        .order_by(
            or_(Ingredient.name == q, Ingredient.id.in_(exact_alias)).desc(),
            Ingredient.name.like(f"{q}%").desc(),
            Ingredient.name,
        )
        .limit(SEARCH_LIMIT)
    )
    return list(rows.scalars())


async def get(session: AsyncSession, ingredient_id: uuid.UUID) -> Ingredient | None:
    return await session.get(Ingredient, ingredient_id)
