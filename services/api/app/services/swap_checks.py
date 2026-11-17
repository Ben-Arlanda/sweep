"""The Swap checks: code decides whether a model-written Swap is allowed (ADR 0021).

Pure (no database, no model), so every rule is tested directly, and the same reasons go
back to the agent so it can fix its Swaps and try again. Each reason is written by
code, quoting only the line the model wrote.

A Swap is refused when its replacement:
1. isn't linked to an Ingredient Sweep knows (a Not linked line);
2. is linked to a Household Ingredient: Sweep doesn't know what's in it (fail closed);
3. is the same Ingredient as before ("for two" is a Planned Meal's servings);
4. brings in meat, seafood or egg the replaced line didn't have: the method's cooking
   times weren't written for it (tofu → chicken is refused, thigh → breast is fine).
Then the adapted recipe as a whole must pass the Household's Dietary Rules.
"""

from collections.abc import Iterable, Sequence

from app.data.diet import CONTAINS, Contains
from app.models import Ingredient, RecipeIngredient
from app.services.diet import DietaryRules, check_lines

# Only these need the method to have been written for them. Dairy or gluten swaps
# (cream → yoghurt, pasta → rice) don't change whether something is cooked through.
COOKED_THROUGH = (Contains.MEAT, Contains.SEAFOOD, Contains.EGG)


def _contains(found: Ingredient | None) -> frozenset[Contains]:
    return CONTAINS.get(found.name, frozenset()) if found is not None else frozenset()


def _swap_problem(original: RecipeIngredient, replacement: RecipeIngredient) -> str | None:
    new, raw = replacement.ingredient, replacement.raw_text
    if new is None:
        return f'"{raw}" isn\'t an Ingredient Sweep knows'
    if new.is_household_ingredient:
        return f'"{raw}" uses {new.name}, which Sweep can\'t check'
    old = original.ingredient
    if old is not None and old.name == new.name:
        return f'"{raw}" is still {new.name}: a Swap must change the ingredient'
    added = [c for c in COOKED_THROUGH if c in _contains(new) - _contains(old)]
    if added:
        return f'"{raw}" adds {added[0].value}, which the method wasn\'t written for'
    return None


def check(
    swaps: Sequence[tuple[RecipeIngredient, RecipeIngredient]],
    adapted_lines: Iterable[RecipeIngredient],
    rules: DietaryRules,
) -> list[str]:
    """Every problem with these Swaps, in order; empty = allowed. `swaps` pairs each
    replaced line with its replacement; `adapted_lines` is the whole recipe after."""
    problems = [p for original, new in swaps if (p := _swap_problem(original, new)) is not None]
    rule_check = check_lines(adapted_lines, rules)
    if not rule_check.ok:
        problems.append(
            f"The recipe still breaks the Dietary Rules: {', '.join(rule_check.breaks)}"
        )
    return problems
