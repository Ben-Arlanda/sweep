"""Kitchen Match (ADR 0013): how well a recipe fits what's in the Kitchen, and the ranking
plans start from. The scoring is a pure function, so most of these tests need no database.
"""

import uuid

import pytest

from app.services.kitchen_match import KitchenSnapshot, Line, match, rank_key

PASTA, TOMATOES, GARLIC, BASIL, SALT, LEMON = (uuid.uuid4() for _ in range(6))
FINGER_LIME = uuid.uuid4()


def kitchen(
    have: set[uuid.UUID] = frozenset(),  # type: ignore[assignment]
    maybe: set[uuid.UUID] = frozenset(),  # type: ignore[assignment]
    staples: set[uuid.UUID] = frozenset(),  # type: ignore[assignment]
    own: dict[str, uuid.UUID] | None = None,
) -> KitchenSnapshot:
    """`have` and `maybe` are Tracked items; `staples` are Staples marked "have"."""
    return KitchenSnapshot(
        have=frozenset(have) | frozenset(staples),
        maybe=frozenset(maybe),
        tracked=frozenset(have) | frozenset(maybe),
        own_names=own or {},
    )


def line(
    ingredient: uuid.UUID | None, name: str | None, text: str = "", optional: bool = False
) -> Line:
    return Line(
        ingredient_id=ingredient, name=name, raw_text=text or (name or ""), optional=optional
    )


PASTA_RECIPE = [
    line(PASTA, "pasta"),
    line(TOMATOES, "tomatoes"),
    line(GARLIC, "garlic"),
    line(SALT, "salt"),
    line(BASIL, "basil", optional=True),
    line(None, None, "1 cup water"),
]


def test_each_needed_line_is_have_maybe_or_missing() -> None:
    result = match(PASTA_RECIPE, kitchen(have={PASTA}, maybe={TOMATOES}, staples={SALT}))

    assert result.have == ("pasta", "salt")
    assert result.maybe == ("tomatoes",)
    assert result.missing == ("garlic",)  # basil is optional; water has no Ingredient


def test_a_staple_that_ran_out_is_missing() -> None:
    result = match([line(SALT, "salt")], kitchen())

    assert result.missing == ("salt",)


def test_tracked_items_used_counts_bought_things_not_staples() -> None:
    result = match(PASTA_RECIPE, kitchen(have={PASTA, GARLIC}, maybe={TOMATOES}, staples={SALT}))

    assert result.tracked_used == 3  # pasta, garlic, tomatoes; salt is a Staple


def test_the_same_ingredient_twice_counts_once() -> None:
    lines = [line(GARLIC, "garlic", "2 cloves garlic"), line(GARLIC, "garlic", "1 clove garlic")]

    assert match(lines, kitchen()).missing == ("garlic",)


@pytest.mark.parametrize("text", ["2 finger limes, halved", "Finger lime pearls", "1 finger lime"])
def test_a_household_ingredient_named_in_an_unlinked_line_counts(text: str) -> None:
    own = {"finger lime": FINGER_LIME}

    have = match([line(None, None, text)], kitchen(have={FINGER_LIME}, own=own))
    missing = match([line(None, None, text)], kitchen(own=own))

    assert have.have == ("finger lime",)
    assert missing.missing == ("finger lime",)


def test_household_ingredient_names_match_whole_words_longest_first() -> None:
    own = {"lime": LEMON, "finger lime": FINGER_LIME}

    result = match(
        [line(None, None, "2 finger limes"), line(None, None, "sublime syrup")],
        kitchen(have={FINGER_LIME}, own=own),
    )

    assert result.have == ("finger lime",)  # not "lime", and "sublime" isn't "lime"
    assert result.missing == ()


def test_fewest_things_to_buy_ranks_first_then_unsure_then_what_it_uses() -> None:
    snapshot = kitchen(have={PASTA, GARLIC, TOMATOES}, maybe={BASIL}, staples={SALT})
    candidates = {
        "needs lemon": [line(PASTA, "pasta"), line(LEMON, "lemon")],
        "maybe basil": [line(PASTA, "pasta"), line(BASIL, "basil")],
        "uses three": [line(PASTA, "pasta"), line(GARLIC, "garlic"), line(TOMATOES, "tomatoes")],
        "uses one": [line(PASTA, "pasta"), line(SALT, "salt")],
    }

    ordered = sorted(
        candidates, key=lambda title: rank_key(title, match(candidates[title], snapshot))
    )

    assert ordered == ["uses three", "uses one", "maybe basil", "needs lemon"]


def test_kitchen_first_beats_kitchen_blind_on_the_real_recipes() -> None:
    """The eval (evals/kitchen_first.py) as a guard: on every sample Kitchen, planning
    from the Kitchen needs fewer things bought than picking at random."""
    from app.data.recipes import load_seed_recipes
    from evals.kitchen_first import KITCHENS, evaluate

    for result in evaluate(KITCHENS, load_seed_recipes()):
        assert result.first.to_buy_per_meal < result.blind.to_buy_per_meal / 2, result.kitchen
