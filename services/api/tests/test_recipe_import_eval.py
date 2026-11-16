"""The recipe import eval's grading (free): a failed call must never look like a refusal."""

from app.data.ingredients import INGREDIENTS
from app.services.ingredient_lines import IngredientIndex
from evals.recipe_import import grade, passed
from tests.test_recipe_import import reading

INDEX = IngredientIndex.from_seed(INGREDIENTS)
NOT_A_RECIPE = {"name": "not-a-recipe", "door": "paste", "found": False}


def test_a_refusal_passes_a_not_a_recipe_case() -> None:
    result = grade(NOT_A_RECIPE, reading(found_recipe=False), INDEX, "hello")
    assert passed(result) and not result["no_answer"]


def test_no_answer_fails_even_a_not_a_recipe_case() -> None:
    # The reader returns None when the API call fails (no credit, rate limited) or the
    # answer is cut off. That isn't the model refusing, so it can't count as one.
    result = grade(NOT_A_RECIPE, None, INDEX, "hello")
    assert result["no_answer"] and not passed(result)
