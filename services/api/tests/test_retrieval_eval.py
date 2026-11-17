"""The retrieval eval's scores and the Retrieval Set itself (slice 9). No database."""

from app.data.recipes import load_seed_recipes
from evals.retrieval import (
    KINDS,
    load_queries,
    percentile,
    precision_at,
    recall_at,
    reciprocal_rank,
)

RELEVANT = frozenset({"a", "b"})


def test_recall_counts_how_many_relevant_recipes_made_the_cut() -> None:
    assert recall_at(["a", "x", "b"], RELEVANT, 10) == 1.0
    assert recall_at(["a", "x", "b"], RELEVANT, 2) == 0.5
    assert recall_at([], RELEVANT, 10) == 0.0


def test_precision_is_out_of_k_even_when_fewer_came_back() -> None:
    assert precision_at(["a", "x"], RELEVANT, 10) == 0.1


def test_reciprocal_rank_is_one_over_the_first_relevant_position() -> None:
    assert reciprocal_rank(["x", "x", "b"], RELEVANT) == 1 / 3
    assert reciprocal_rank(["x"] * 10 + ["a"], RELEVANT) == 0.0  # past the top 10


def test_percentile_picks_a_real_value() -> None:
    assert percentile([5.0, 1.0, 3.0], 0.5) == 3.0
    assert percentile([5.0, 1.0, 3.0], 0.95) == 5.0


def test_the_retrieval_set_is_labelled_with_real_seed_recipes() -> None:
    queries = load_queries()
    slugs = {s.slug for s in load_seed_recipes()}
    assert len(queries) >= 50
    assert len({q.id for q in queries}) == len(queries)
    assert {q.kind for q in queries} == set(KINDS)
    assert {q.split for q in queries} == {"dev", "test"}
    for q in queries:
        assert q.relevant, f"{q.id} has no relevant recipes"
        assert q.relevant <= q.judged
        assert q.judged <= slugs, f"{q.id}: {sorted(q.judged - slugs)} aren't Seed Recipes"
