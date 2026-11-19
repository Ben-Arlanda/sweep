"""Recipe Adaptations: a Household's copy of a recipe with some lines swapped (ADR 0021).

An Adaptation is stored as a whole recipe (every line, the swapped ones replaced), not
as "parent + Swaps" put together on each read. That way everything that reads lines
(Dietary Rules, Shopping List, Kitchen Match, Mark as Cooked) needs no changes. The
cost: editing the parent later doesn't change its Adaptations.

Before approval an Adaptation exists only in the Draft Plan, as parent + Swaps.
`preview` builds it in memory and runs the Swap checks; the agent's tool, validate and
the commit all go through it, so the checks can't be skipped. There is no route that
creates one: only an approved Proposal does.
"""

import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors
from app.agent.state import DraftMeal
from app.models import Recipe, RecipeIngredient, RecipeKind
from app.schemas import ImportedLineIn
from app.services import diet, imported_recipes, swap_checks
from app.services.recipes import visible_to

TITLE_JOIN = " · "  # "Mum's ragu · with brown lentils"
MAX_TITLE = 200  # Recipe.title's column


def label_for(lines: Sequence[RecipeIngredient]) -> str:
    """The name after the title, written by code from the swapped-in Ingredients (which
    the checks have linked): "with brown lentils", "with tofu and mushrooms". Never the
    model's words: a live run let a planted "nut-free" claim into a label for cashews
    (inject-lying-summary, 2026-11-17), and a label becomes a saved recipe's title."""
    names = list(
        dict.fromkeys(line.ingredient.name for line in lines if line.replaces and line.ingredient)
    )
    if len(names) <= 1:
        return f"with {''.join(names) or 'swaps'}"
    return f"with {', '.join(names[:-1])} and {names[-1]}"


@dataclass(frozen=True)
class SwapIn:
    """Swap the parent's line at `position` for `raw_text`, a recipe line as written."""

    position: int
    raw_text: str


async def parent(session: AsyncSession, household_id: uuid.UUID, recipe_id: uuid.UUID) -> Recipe:
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


async def preview(
    session: AsyncSession,
    household_id: uuid.UUID,
    parent_id: uuid.UUID,
    swaps: Sequence[SwapIn],
) -> Recipe:
    """The Adaptation, built in memory and not added to the session, after the Swap
    checks pass (else `SwapsRefused`). Replacement lines are read and matched like an
    Imported Recipe's (the Household's view of the Ingredients)."""
    original = await parent(session, household_id, parent_id)
    by_position = {line.position: line for line in original.ingredients}
    wanted = {swap.position: swap for swap in swaps}
    if not swaps or len(wanted) != len(swaps) or not wanted.keys() <= by_position.keys():
        raise errors.InvalidInput("Each Swap must replace a different line of the recipe.")
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

    rules = await diet.get_rules(session, household_id)
    pairs = [(by_position[p], new_lines[p]) for p in sorted(new_lines)]
    problems = swap_checks.check(pairs, lines, rules)
    if problems:
        raise errors.SwapsRefused(problems)

    title = f"{original.title}{TITLE_JOIN}{label_for(lines)}"
    if len(title) > MAX_TITLE:
        title = f"{original.title[: MAX_TITLE - 20]}{TITLE_JOIN}adapted"
    return Recipe(
        kind=RecipeKind.ADAPTATION,
        household_id=household_id,
        parent_recipe_id=original.id,
        title=title,
        summary=original.summary,
        cuisine=original.cuisine,
        course=original.course,
        servings=original.servings,
        total_minutes=original.total_minutes,
        method=list(original.method) if original.method is not None else None,
        # Both views as written, like the method.
        prep_minutes=original.prep_minutes,
        cook_minutes=original.cook_minutes,
        difficulty=original.difficulty,
        stages=original.stages,
        tips=original.tips,
        variations=original.variations,
        storage=original.storage,
        source_url=original.source_url,
        licence=original.licence,
        attribution=original.attribution,
        ingredients=lines,
    )


def swaps_of(recipe: Recipe) -> list[tuple[str, str]]:
    """(the line replaced, the new line) for each Swap, in recipe order."""
    return [(line.replaces, line.raw_text) for line in recipe.ingredients if line.replaces]


async def create(
    session: AsyncSession,
    household_id: uuid.UUID,
    parent_id: uuid.UUID,
    swaps: Sequence[SwapIn],
) -> Recipe:
    """Store an Adaptation, or reuse a kept one with exactly the same Swaps (proposing
    "with lentils" twice shouldn't leave two copies under the recipe)."""
    adaptation = await preview(session, household_id, parent_id, swaps)
    for kept in await for_parent(session, household_id, parent_id):
        if swaps_of(kept) == swaps_of(adaptation):
            return kept
    session.add(adaptation)
    await session.flush()
    return adaptation


def swaps_in(meal: DraftMeal) -> list[SwapIn]:
    adaptation = meal.get("adaptation")
    swaps = adaptation["swaps"] if adaptation else []
    return [SwapIn(s["position"], s["raw_text"]) for s in swaps]


async def for_draft(
    session: AsyncSession, household_id: uuid.UUID, meals: Mapping[str, DraftMeal]
) -> tuple[dict[str, Recipe], dict[str, str]]:
    """For the meals that carry an Adaptation: the adapted recipe by day, or why its
    Swaps are refused by day. Rebuilt every time (validate, commit), against the
    current recipes and Rules, because a Proposal can wait a day."""
    adapted: dict[str, Recipe] = {}
    refused: dict[str, str] = {}
    for day, meal in meals.items():
        adaptation = meal.get("adaptation")
        if adaptation is None:
            continue
        try:
            adapted[day] = await preview(
                session,
                household_id,
                uuid.UUID(meal["recipe_id"]),
                swaps_in(meal),
            )
        except errors.SwapsRefused as error:
            refused[day] = "; ".join(error.problems)
        except (errors.NotFound, errors.InvalidInput, ValueError) as error:
            refused[day] = getattr(error, "message", "the recipe can't be adapted")
    return adapted, refused


async def for_parent(
    session: AsyncSession, household_id: uuid.UUID, parent_id: uuid.UUID
) -> list[Recipe]:
    """This Household's Adaptations of one recipe, oldest first. Empty for a recipe it
    can't see, so the answer gives nothing away about other Households."""
    return (await kept_for(session, household_id, [parent_id])).get(parent_id, [])


async def kept_for(
    session: AsyncSession, household_id: uuid.UUID, parent_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[Recipe]]:
    """Kept Adaptations of several recipes in one query, by parent, oldest first."""
    if not parent_ids:
        return {}
    found = await session.execute(
        select(Recipe)
        .where(
            Recipe.kind == RecipeKind.ADAPTATION,
            Recipe.household_id == household_id,
            Recipe.parent_recipe_id.in_(parent_ids),
        )
        .order_by(Recipe.created_at, Recipe.id)
    )
    out: dict[uuid.UUID, list[Recipe]] = defaultdict(list)
    for recipe in found.scalars():
        assert recipe.parent_recipe_id is not None
        out[recipe.parent_recipe_id].append(recipe)
    return dict(out)


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
