"""Recipe Adaptations: a Household's copy of a recipe with some lines swapped (ADR 0021).

An Adaptation is stored as a whole recipe (every line, the swapped ones replaced), not
as "parent + Swaps" put together on each read. That way everything that reads lines
(Dietary Rules, Shopping List, Kitchen Match, Mark as Cooked) needs no changes. The
cost: editing the parent later doesn't change its Adaptations.

There is no route that creates one. Only an approved Proposal does (slice 5e step 3),
after the Swap checks in code have passed.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors
from app.models import Recipe, RecipeIngredient, RecipeKind
from app.schemas import ImportedLineIn
from app.services import imported_recipes
from app.services.recipes import visible_to

TITLE_JOIN = " · "  # "Mum's ragu · with lentils"
MAX_TITLE = 200  # Recipe.title's column


@dataclass(frozen=True)
class SwapIn:
    """Swap the parent's line at `position` for `raw_text`, a recipe line as written."""

    position: int
    raw_text: str


async def _parent(session: AsyncSession, household_id: uuid.UUID, recipe_id: uuid.UUID) -> Recipe:
    """A Seed or Imported Recipe this Household can see. Not an Adaptation: a new one is
    always made from the original, so Swaps never stack up on each other."""
    recipe = (
        await session.execute(
            visible_to(household_id).where(
                Recipe.id == recipe_id, Recipe.kind != RecipeKind.ADAPTATION
            )
        )
    ).scalar_one_or_none()
    if recipe is None:
        raise errors.NotFound("Recipe not found")
    return recipe


def _copy(line: RecipeIngredient) -> RecipeIngredient:
    return RecipeIngredient(
        position=line.position,
        raw_text=line.raw_text,
        ingredient_id=line.ingredient_id,
        ingredient=line.ingredient,
        quantity=line.quantity,
        unit=line.unit,
        base_quantity=line.base_quantity,
        note=line.note,
        optional=line.optional,
        parse_method=line.parse_method,
        needs_review=line.needs_review,
    )


async def create(
    session: AsyncSession,
    household_id: uuid.UUID,
    parent_id: uuid.UUID,
    swaps: Sequence[SwapIn],
    label: str,
) -> Recipe:
    """Store an Adaptation of `parent_id`. Each replacement line is read and matched the
    same way as an Imported Recipe's (the Household's view of the Ingredients)."""
    parent = await _parent(session, household_id, parent_id)
    by_position = {line.position: line for line in parent.ingredients}
    wanted = {swap.position: swap for swap in swaps}
    if not swaps or len(wanted) != len(swaps) or not wanted.keys() <= by_position.keys():
        raise errors.InvalidInput("Each Swap must replace a different line of the recipe.")
    title = f"{parent.title}{TITLE_JOIN}{label}"
    if len(title) > MAX_TITLE:
        raise errors.InvalidInput("That name is too long.")

    replacements = await imported_recipes.read_lines(
        session, household_id, [ImportedLineIn(raw_text=s.raw_text) for s in wanted.values()]
    )
    new_lines = dict(zip(wanted, replacements, strict=True))
    lines = []
    for position, line in sorted(by_position.items()):
        if position in new_lines:
            swapped = new_lines[position]
            swapped.position, swapped.replaces = position, line.raw_text
            lines.append(swapped)
        else:
            lines.append(_copy(line))

    adaptation = Recipe(
        kind=RecipeKind.ADAPTATION,
        household_id=household_id,
        parent_recipe_id=parent.id,
        title=title,
        summary=parent.summary,
        cuisine=parent.cuisine,
        course=parent.course,
        servings=parent.servings,
        total_minutes=parent.total_minutes,
        method=list(parent.method) if parent.method is not None else None,
        source_url=parent.source_url,
        licence=parent.licence,
        attribution=parent.attribution,
        ingredients=lines,
    )
    session.add(adaptation)
    await session.flush()
    return adaptation


async def for_parent(
    session: AsyncSession, household_id: uuid.UUID, parent_id: uuid.UUID
) -> list[Recipe]:
    """This Household's Adaptations of one recipe, oldest first. Empty for a recipe it
    can't see, so the answer gives nothing away about other Households."""
    found = await session.execute(
        select(Recipe)
        .where(
            Recipe.kind == RecipeKind.ADAPTATION,
            Recipe.household_id == household_id,
            Recipe.parent_recipe_id == parent_id,
        )
        .order_by(Recipe.created_at, Recipe.id)
    )
    return list(found.scalars())


async def delete(session: AsyncSession, household_id: uuid.UUID, recipe_id: uuid.UUID) -> None:
    """Any Member may. Planned Meals that used it go with it (ON DELETE CASCADE), as for
    an Imported Recipe. Anything that isn't this Household's Adaptation is a 404."""
    recipe = (
        await session.execute(
            select(Recipe).where(
                Recipe.id == recipe_id,
                Recipe.household_id == household_id,
                Recipe.kind == RecipeKind.ADAPTATION,
            )
        )
    ).scalar_one_or_none()
    if recipe is None:
        raise errors.NotFound("Recipe not found")
    await session.delete(recipe)
    await session.flush()
