"""The Recipe Image eval's scoring (slice 4f). No model calls."""

from evals.recipe_images import load_cases, score


def test_the_bar_is_no_false_pass_and_most_matches_pass() -> None:
    assert score([("pass", True)] * 8 + [("pass", False)] * 2 + [("fail", False)] * 5)["met"]
    assert not score([("pass", True)] * 10 + [("fail", True)])["met"]  # one misleading photo
    assert not score([("pass", True)] * 7 + [("pass", False)] * 3)["met"]  # 70% < 80%


def test_cases_are_labelled_with_a_reason_and_a_real_recipe() -> None:
    from app.data.recipes import load_seed_recipes

    slugs = {r.slug for r in load_seed_recipes()}
    cases = load_cases()
    assert len(cases) >= 30
    assert {c["expect"] for c in cases} == {"pass", "fail"}
    assert all(c["slug"] in slugs and c["why"] for c in cases)
    assert len({c["name"] for c in cases}) == len(cases)
