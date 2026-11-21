"""Dietary Rules: hard constraints, checked by code and never left to the agent.

Two places use them (CONTEXT.md, plan §7):
- search: recipes that break a Rule are filtered out in SQL, so the agent never sees them
- validate: every Planned Meal is checked again here before a Proposal is shown

Starters are checked against their recorded contents (data/diet.py). A Household
Ingredient is judged by the words in its name (data/diet_words.py, ADR 0032): held back
when it likely breaks a Rule ("andouille sausage"), "check the label" when it depends on
the brand ("satay sauce"), otherwise it passes. An excluded food also catches names that
contain it ("no mushrooms": shiitake mushrooms).
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors
from app.data.diet import CHECK_LABEL, CONTAINS, DIET_EXCLUDES, Contains, Diet
from app.data.diet_words import judge, names_food
from app.models import (
    HouseholdDietaryRules,
    HouseholdExcludedIngredient,
    HouseholdPreferences,
    Ingredient,
    Recipe,
    RecipeIngredient,
)
from app.services import ingredients


@dataclass(frozen=True)
class DietaryRules:
    diets: frozenset[Diet] = frozenset()
    excluded_ingredient_ids: frozenset[uuid.UUID] = frozenset()
    excluded_names: frozenset[str] = frozenset()  # their names, to catch "shiitake mushrooms"

    @property
    def active(self) -> bool:
        return bool(self.diets or self.excluded_ingredient_ids or self.excluded_names)


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
    return check_lines(recipe.ingredients, rules)


def check_lines(lines: Iterable[RecipeIngredient], rules: DietaryRules) -> RuleCheck:
    """check_recipe for lines that aren't a stored recipe yet (an Adaptation's)."""
    check = RuleCheck()
    if not rules.active:
        return check
    for line in lines:
        ingredient = line.ingredient
        if ingredient is None:
            if line.needs_review:  # unlinked but not flagged = water, which is fine
                check.breaks.append(f"{line.raw_text} (couldn't check)")
            continue
        if is_excluded(ingredient, rules):
            check.breaks.append(f"{ingredient.name} (excluded)")
            continue
        likely, label = contents(ingredient)
        broken = _diets_broken(likely, rules.diets)
        check.breaks.extend(f"{ingredient.name} ({_label(d)})" for d in broken)
        maybe = _diets_broken(label, rules.diets)
        check.check_label.extend(f"{ingredient.name} ({_label(d)})" for d in maybe)
    return check


def contents(ingredient: Ingredient) -> tuple[frozenset[Contains], frozenset[Contains]]:
    """(what it contains, what depends on the brand): recorded for starters, read from
    the name for Household Ingredients (only Imported Recipes link to those)."""
    if ingredient.is_household_ingredient:
        return judge(ingredient.name)
    return CONTAINS.get(ingredient.name, frozenset()), CHECK_LABEL.get(ingredient.name, frozenset())


def is_excluded(ingredient: Ingredient, rules: DietaryRules) -> bool:
    return ingredient.id in rules.excluded_ingredient_ids or any(
        names_food(ingredient.name, food) for food in rules.excluded_names
    )


async def banned_ingredient_ids(
    session: AsyncSession, household_id: uuid.UUID, rules: DietaryRules
) -> set[uuid.UUID]:
    """Every Ingredient this Household's recipes must not use under these Rules (for the
    SQL filter): the same answer check_lines gives, worked out over the whole list."""
    if not rules.active:
        return set()
    visible = await session.execute(select(Ingredient).where(ingredients.visible_to(household_id)))
    return {
        i.id
        for i in visible.scalars()
        if is_excluded(i, rules) or _diets_broken(contents(i)[0], rules.diets)
    }


# --- Storage ------------------------------------------------------------------------


async def get_rules(session: AsyncSession, household_id: uuid.UUID) -> DietaryRules:
    row = await session.get(HouseholdDietaryRules, household_id)
    excluded = await session.execute(
        select(HouseholdExcludedIngredient.ingredient_id).where(
            HouseholdExcludedIngredient.household_id == household_id
        )
    )
    diets = frozenset(Diet(d) for d in row.diets) if row else frozenset()
    ids = frozenset(excluded.scalars())
    names = await session.execute(select(Ingredient.name).where(Ingredient.id.in_(ids)))
    return DietaryRules(diets, ids, frozenset(names.scalars()))


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
