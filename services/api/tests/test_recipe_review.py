"""The recipe reviewer's plumbing and its eval scoring, with a stand-in (no API calls)."""

from typing import get_args

import pytest

from app.data.recipes import SeedRecipe
from app.services.recipe_checks import check_recipes
from app.services.recipe_review import Issue, IssueKind, Review, as_text, review_recipes
from evals.recipe_review import load_cases, score


class CannedReviewer:
    """Flags recipes whose slug is in `flag`; can't answer for those in `fail`."""

    def __init__(self, flag: dict[str, IssueKind], fail: set[str] = frozenset()) -> None:  # type: ignore[assignment]
        self.flag, self.fail = flag, fail
        self.seen: list[str] = []

    async def review(self, recipe: SeedRecipe) -> Review | None:
        self.seen.append(recipe.slug)
        if recipe.slug in self.fail:
            return None
        kind = self.flag.get(recipe.slug)
        return Review(issues=[Issue(kind=kind, detail="x")] if kind else [])


CASES = load_cases()


def test_the_dataset_loads_with_valid_labels() -> None:
    assert len(CASES) >= 12
    assert {c.planted for c in CASES if c.planted} <= set(get_args(IssueKind))
    assert len({c.recipe.slug for c in CASES}) == len(CASES)


def test_sound_eval_recipes_pass_the_automatic_checks() -> None:
    # Otherwise a "false alarm" might be the reviewer spotting a real mistake we made.
    sound = [c.recipe for c in CASES if not c.planted]
    assert check_recipes(sound) == []


def test_the_reviewer_sees_the_whole_recipe_card() -> None:
    card = as_text(CASES[0].recipe)
    assert "serves 4, 35 minutes in total" in card
    assert "- 800 g chicken thigh" in card
    assert "1. Season the chicken" in card


@pytest.mark.anyio
async def test_review_recipes_asks_about_each_one_in_order() -> None:
    reviewer = CannedReviewer({})
    recipes = [c.recipe for c in CASES[:3]]
    reviews = await review_recipes(recipes, reviewer)
    assert reviewer.seen == [r.slug for r in recipes]
    assert all(r is not None and not r.flagged for r in reviews.values())


@pytest.mark.anyio
async def test_scoring_counts_catches_kinds_false_alarms_and_no_answers() -> None:
    planted = [c for c in CASES if c.planted]
    sound = [c for c in CASES if not c.planted]
    flags: dict[str, IssueKind] = {
        planted[0].recipe.slug: planted[0].planted,  # type: ignore[dict-item]  # caught, right kind
        planted[1].recipe.slug: "clarity",  # caught, wrong kind
        sound[0].recipe.slug: "quantity",  # a false alarm
    }
    reviewer = CannedReviewer(flags, fail={planted[2].recipe.slug})
    reviews = {c.recipe.slug: await reviewer.review(c.recipe) for c in CASES}
    s = score(CASES, reviews)
    assert (s.caught, s.right_kind, s.false_alarms, s.no_answer) == (2, 1, 1, 1)
    assert (s.planted, s.sound) == (len(planted), len(sound))
