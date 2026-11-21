"""The gap report (ADR 0032): foods recipes keep adding that Sweep doesn't know yet.

    uv run python -m app.gap_report

Household Ingredients that recipe lines use, by name, when at least 3 Households have
one. Names and counts only: nothing says which Households. Each shows how the diet words
judge it, so a wrong verdict gets fixed when the food becomes a starter or an alias (the
merge then repoints every Household's lines, Kitchen rows and list items).
"""

import asyncio
import sys
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.data.diet import DIET_EXCLUDES, Diet
from app.data.diet_words import judge
from app.db import make_engine, make_sessionmaker
from app.models import Ingredient, RecipeIngredient

MIN_HOUSEHOLDS = 3  # fewer could point at one Household, and isn't a pattern yet


@dataclass(frozen=True)
class Gap:
    name: str
    households: int
    held_back: list[str]  # diets its words say it likely breaks
    check_label: list[str]


def _label(diet: Diet) -> str:
    return diet.value.replace("_", " ")


async def gaps(session: AsyncSession) -> list[Gap]:
    """Most Households first, then A to Z."""
    households = func.count(Ingredient.household_id.distinct())
    rows = await session.execute(
        select(Ingredient.name, households)
        .join(RecipeIngredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .where(Ingredient.household_id.is_not(None))
        .group_by(Ingredient.name)
        .having(households >= MIN_HOUSEHOLDS)
        .order_by(households.desc(), Ingredient.name)
    )
    out = []
    for name, count in rows.all():
        likely, label = judge(name)
        out.append(
            Gap(
                name=name,
                households=count,
                held_back=[_label(d) for d in Diet if likely & DIET_EXCLUDES[d]],
                check_label=[_label(d) for d in Diet if label & DIET_EXCLUDES[d]],
            )
        )
    return out


def line(gap: Gap) -> str:
    parts = [f"{gap.name}: {gap.households} Households"]
    if gap.held_back:
        parts.append("held back: " + ", ".join(gap.held_back))
    if gap.check_label:
        parts.append("check the label: " + ", ".join(gap.check_label))
    if not gap.held_back and not gap.check_label:
        parts.append("passes every diet")
    return " · ".join(parts)


async def main() -> int:
    engine = make_engine(settings.database_url)
    async with make_sessionmaker(engine)() as session:
        found = await gaps(session)
    await engine.dispose()
    for gap in found:
        print(line(gap))
    print(f"{len(found)} foods in at least {MIN_HOUSEHOLDS} Households' recipes")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
