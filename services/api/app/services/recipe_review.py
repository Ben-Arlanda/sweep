"""The AI reviewer for Seed Recipes: LLM-as-judge (slice 4c, ADR 0002).

The automatic checks (`recipe_checks`) catch mistakes with a clear rule. This catches the
ones that need judgement, the way a cook reading the recipe would: too much salt for four
people, rice with too little water, a cake at 250°C, steps in the wrong order.

It only *flags*. A person reads every flagged recipe and decides; nothing is changed or
rejected automatically. And because a judge can be wrong too, it's measured before it's
trusted: `evals/recipe_review.py` scores it against recipes a person has labelled, some
with mistakes planted on purpose.

Calling the reviewer costs money, so nothing here runs it. `python -m evals.recipe_review
--llm` does, on purpose.
"""

from collections.abc import Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.data.recipes import SeedRecipe

IssueKind = Literal[
    "food_safety",  # undercooked, unsafe holding, raw where it shouldn't be
    "quantity",  # an amount that's clearly wrong for the servings
    "method",  # missing, impossible or out-of-order steps
    "timing",  # times or temperatures that won't work, or a total that's wrong
    "clarity",  # a step a home cook couldn't follow
    "mismatch",  # title or summary doesn't match what the recipe makes
]


class Issue(BaseModel):
    kind: IssueKind
    detail: str = Field(description="What's wrong and where, in one sentence.")


class Review(BaseModel):
    """What the reviewer says about one recipe."""

    issues: list[Issue] = Field(
        description="Problems a careful home cook would notice. Empty if there are none."
    )

    @property
    def flagged(self) -> bool:
        return bool(self.issues)


class RecipeReviewer(Protocol):
    async def review(self, recipe: SeedRecipe) -> Review | None:
        """None if the reviewer couldn't give an answer (the recipe then needs a person)."""
        ...


def as_text(recipe: SeedRecipe) -> str:
    """The recipe the way the reviewer sees it: like a recipe card."""
    lines = "\n".join(f"- {line}" for line in recipe.ingredients)
    steps = "\n".join(f"{i}. {step}" for i, step in enumerate(recipe.method, 1))
    return (
        f"{recipe.title} ({recipe.cuisine}, serves {recipe.servings}, "
        f"{recipe.minutes} minutes in total)\n{recipe.summary}\n\n"
        f"Ingredients:\n{lines}\n\nMethod:\n{steps}"
    )


async def review_recipes(
    recipes: Sequence[SeedRecipe], reviewer: RecipeReviewer
) -> dict[str, Review | None]:
    """Review each recipe, one at a time (simple, and gentle on rate limits)."""
    return {r.slug: await reviewer.review(r) for r in recipes}
