"""Dietary Rules: hard constraints, checked by code and never left to the agent.

Two places use them (CONTEXT.md, plan §7):
- search: recipes that break a Rule are filtered out in SQL, so the agent never sees them
- validate: every Planned Meal is checked again here before a Proposal is shown

Fails closed: when any Rule is set, a line we can't check counts as breaking it. That's
a line we couldn't match ("1 jar mystery sauce"), or one linked to a Household
Ingredient: a Member made "satay sauce", and Sweep has no idea what's in it.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors
from app.data.diet import CHECK_LABEL, CONTAINS, DIET_EXCLUDES, Contains, Diet
from app.models import (
    HouseholdDietaryRules,
    HouseholdExcludedIngredient,
    HouseholdPreferences,
    Ingredient,
    Recipe,
)
from app.services import ingredients


@dataclass(frozen=True)
class DietaryRules:
    diets: frozenset[Diet] = frozenset()
    excluded_ingredient_ids: frozenset[uuid.UUID] = frozenset()

    @property
    def active(self) -> bool:
        return bool(self.diets or self.excluded_ingredient_ids)


@dataclass(frozen=True)
class RuleCheck:
    breaks: list[str] = field(default_factory=list)  # "soy sauce (gluten free)"
    check_label: list[str] = field(default_factory=list)  # "stock cubes (gluten free)"

    @property
    def ok(self) -> bool:
        return not self.breaks


def _label(diet: Diet) -> str:
    return diet.value.replace("_", " ")


def _diets_broken(flags: frozenset[Contains], diets: Iterable[Diet]) -> list[Diet]:
    return [d for d in sorted(diets) if flags & DIET_EXCLUDES[d]]


def check_recipe(recipe: Recipe, rules: DietaryRules) -> RuleCheck:
    """Which lines break the Rules, and which need a label check. Pure: no database."""
    check = RuleCheck()
    if not rules.active:
        return check
    for line in recipe.ingredients:
        ingredient = line.ingredient
        if ingredient is None:
            if line.needs_review:  # unlinked but not flagged = water, which is fine
                check.breaks.append(f"{line.raw_text} (couldn't check)")
            continue
        if ingredient.id in rules.excluded_ingredient_ids:
            check.breaks.append(f"{ingredient.name} (excluded)")
            continue
        if ingredient.is_household_ingredient:  # only Imported Recipes link to these
            check.breaks.append(f"{ingredient.name} (couldn't check)")
            continue
        broken = _diets_broken(CONTAINS.get(ingredient.name, frozenset()), rules.diets)
        check.breaks.extend(f"{ingredient.name} ({_label(d)})" for d in broken)
        maybe = _diets_broken(CHECK_LABEL.get(ingredient.name, frozenset()), rules.diets)
        check.check_label.extend(f"{ingredient.name} ({_label(d)})" for d in maybe)
    return check


def banned_names(diets: Iterable[Diet]) -> set[str]:
    """Ingredient names that break at least one of these diets."""
    excluded: set[Contains] = set().union(*(DIET_EXCLUDES[d] for d in diets))
    return {name for name, flags in CONTAINS.items() if flags & excluded}


async def banned_ingredient_ids(session: AsyncSession, rules: DietaryRules) -> set[uuid.UUID]:
    """Every Ingredient a recipe must not use under these Rules (for the SQL filter)."""
    ids = set(rules.excluded_ingredient_ids)
    names = banned_names(rules.diets)
    if names:
        found = await session.execute(
            select(Ingredient.id).where(Ingredient.name.in_(names), ingredients.STARTERS)
        )
        ids.update(found.scalars())
    return ids


# --- Storage ------------------------------------------------------------------------


async def get_rules(session: AsyncSession, household_id: uuid.UUID) -> DietaryRules:
    row = await session.get(HouseholdDietaryRules, household_id)
    excluded = await session.execute(
        select(HouseholdExcludedIngredient.ingredient_id).where(
            HouseholdExcludedIngredient.household_id == household_id
        )
    )
    diets = frozenset(Diet(d) for d in row.diets) if row else frozenset()
    return DietaryRules(diets, frozenset(excluded.scalars()))


async def set_rules(
    session: AsyncSession, household_id: uuid.UUID, rules: DietaryRules
) -> DietaryRules:
    """Replace the Household's Rules (PUT: send the whole set)."""
    if rules.excluded_ingredient_ids:
        found = await session.execute(
            select(Ingredient.id).where(
                Ingredient.id.in_(rules.excluded_ingredient_ids),
                ingredients.visible_to(household_id),
            )
        )
        if set(found.scalars()) != rules.excluded_ingredient_ids:
            raise errors.NotFound("Ingredient not found")

    row = await session.get(HouseholdDietaryRules, household_id)
    if row is None:
        row = HouseholdDietaryRules(household_id=household_id)
        session.add(row)
    row.diets = sorted(d.value for d in rules.diets)

    current = await session.execute(
        select(HouseholdExcludedIngredient).where(
            HouseholdExcludedIngredient.household_id == household_id
        )
    )
    for old in current.scalars():
        await session.delete(old)
    await session.flush()
    session.add_all(
        HouseholdExcludedIngredient(household_id=household_id, ingredient_id=i)
        for i in rules.excluded_ingredient_ids
    )
    await session.flush()
    return rules


async def excluded_ingredients(
    session: AsyncSession, household_id: uuid.UUID, rules: DietaryRules
) -> list[Ingredient]:
    if not rules.excluded_ingredient_ids:
        return []
    found = await session.execute(
        select(Ingredient)
        .where(
            Ingredient.id.in_(rules.excluded_ingredient_ids), ingredients.visible_to(household_id)
        )
        .order_by(Ingredient.name)
    )
    return list(found.scalars())


async def get_preferences(session: AsyncSession, household_id: uuid.UUID) -> HouseholdPreferences:
    row = await session.get(HouseholdPreferences, household_id)
    return row or HouseholdPreferences(
        household_id=household_id, cuisines=[], plan_weekdays=[1, 2, 3, 4, 5]
    )


async def set_preferences(
    session: AsyncSession,
    household_id: uuid.UUID,
    household_size: int | None,
    cuisines: Iterable[str],
) -> HouseholdPreferences:
    """Replaces size and cuisines. The usual weekdays have their own setter."""
    row = await session.get(HouseholdPreferences, household_id)
    if row is None:
        row = HouseholdPreferences(household_id=household_id, plan_weekdays=[1, 2, 3, 4, 5])
        session.add(row)
    row.household_size = household_size
    row.cuisines = sorted({c.lower() for c in cuisines})
    await session.flush()
    return row


async def set_plan_weekdays(
    session: AsyncSession, household_id: uuid.UUID, weekdays: Iterable[int]
) -> list[int]:
    row = await session.get(HouseholdPreferences, household_id)
    if row is None:
        row = HouseholdPreferences(household_id=household_id, cuisines=[])
        session.add(row)
    row.plan_weekdays = sorted(set(weekdays))
    await session.flush()
    return row.plan_weekdays
