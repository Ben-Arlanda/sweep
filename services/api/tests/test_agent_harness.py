"""The eval harness (slice 8), run with the scripted model so it's free and repeatable.

These prove the harness records what the agent really did. Live runs then only add
the real model; everything they report comes through the code tested here.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from app.agent.prompt import today_in_sydney
from app.data.diet import Diet
from app.embeddings import EmbeddingUnavailable, HashingEmbedder, Purpose
from app.models import PlanMode
from app.services import proposals
from evals.agent_harness import (
    Approve,
    CachedEmbedder,
    FlakyEmbedder,
    MealFacts,
    Reject,
    Say,
    Setup,
    build_household,
    collect_proposals,
    copy_recipe_embeddings,
    list_days,
    open_database,
    run_scenario,
    words,
)
from tests.conftest import Loader
from tests.fake_model import Messages, ScriptedModel, last_result, tool
from tests.test_dietary_rules import SALAD
from tests.test_recipes import CURRY, PASTA, STIR_FRY

pytestmark = pytest.mark.anyio

TOMORROW = (today_in_sydney() + timedelta(days=1)).isoformat()


class CountingEmbedder(HashingEmbedder):
    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, texts: list[str], purpose: Purpose) -> list[list[float]]:
        self.calls += 1
        return await super().embed(texts, purpose)


async def test_the_embedding_cache_answers_repeats_from_disk(tmp_path: Path) -> None:
    inner = CountingEmbedder()
    cache = CachedEmbedder(inner, tmp_path / "embeddings.json")
    first = await cache.embed(["quick vegan dinner"], "query")
    assert await cache.embed(["quick vegan dinner"], "query") == first
    assert inner.calls == 1

    # A new run (new process) reads the same file: no call at all.
    again = CachedEmbedder(inner, tmp_path / "embeddings.json")
    assert await again.embed(["quick vegan dinner"], "query") == first
    assert inner.calls == 1
    # Purpose is part of the key: a recipe text isn't a search text.
    await again.embed(["quick vegan dinner"], "document")
    assert inner.calls == 2


async def test_the_flaky_embedder_fails_first_then_works() -> None:
    flaky = FlakyEmbedder(HashingEmbedder(), failures=1)
    with pytest.raises(EmbeddingUnavailable):
        await flaky.embed(["curry"], "query")
    assert len(await flaky.embed(["curry"], "query")) == 1


def plan_salad_tomorrow() -> ScriptedModel:
    def salad(messages: Messages) -> str:
        [found] = [r for r in last_result(messages) if r["title"] == "Chickpea salad"]
        rid: str = found["recipe_id"]
        return rid

    return ScriptedModel(
        [
            [tool("search_recipes", query="vegetarian salad")],
            lambda m: [tool("set_planned_meal", date=TOMORROW, recipe_id=salad(m), servings=2)],
            [tool("propose_plan", summary="A chickpea salad tomorrow.")],
        ]
    )


SETUP = Setup(
    diets=frozenset({Diet.VEGETARIAN}),
    kitchen={"chickpeas": Decimal(400), "cucumber": None},
    mode=PlanMode.NEW,
    days=(1, 2),
)


async def test_a_run_records_what_the_agent_did(database_url: str, load: Loader) -> None:
    await load([CURRY, PASTA, STIR_FRY, SALAD])
    async with open_database(database_url) as db:
        record = await run_scenario(
            db, plan_salad_tomorrow(), HashingEmbedder(), "salad", SETUP, [Say("Plan {0}")]
        )

    assert record.crashed is None
    assert record.model == "scripted"
    [turn] = record.turns
    assert turn.said == "Plan " + f"{today_in_sydney() + timedelta(days=1):%A}"
    assert record.today == today_in_sydney().isoformat()
    assert record.tool_calls == ("search_recipes", "set_planned_meal", "propose_plan")
    assert record.replans == 0 and turn.error is None
    assert record.chosen_days is not None and len(record.chosen_days) == 2
    assert len(record.usages) == 3  # one per model call

    final = record.final
    assert final is not None and final.status == "pending"
    [meal] = final.meals
    assert meal.title == "Chickpea salad" and meal.date == TOMORROW
    assert meal.exists and meal.rule_breaks == ()
    # Facts come from the Kitchen: chickpeas and cucumber are there, tomatoes aren't.
    assert set(meal.kitchen_uses) == {"chickpeas", "cucumber"}
    assert meal.to_buy is not None and meal.to_buy >= 1


async def test_approve_and_reject_reach_the_proposal(database_url: str, load: Loader) -> None:
    await load([CURRY, PASTA, STIR_FRY, SALAD])
    async with open_database(database_url) as db:
        approved = await run_scenario(
            db, plan_salad_tomorrow(), HashingEmbedder(), "a", SETUP, [Say("Plan"), Approve()]
        )
        rejected = await run_scenario(
            db, plan_salad_tomorrow(), HashingEmbedder(), "r", SETUP, [Say("Plan"), Reject()]
        )
    assert approved.final is not None and approved.final.status == "approved"
    assert rejected.final is not None and rejected.final.status == "rejected"


async def facts_for_a_proposal_of(database_url: str, recipe_id: str) -> MealFacts:
    """Save a Proposal directly (no agent) and collect its facts, as the harness would."""
    async with open_database(database_url) as db, db.sessionmaker() as session:
        _, ctx, cid = await build_household(session, SETUP, today_in_sydney())
        meal = {"date": TOMORROW, "recipe_id": recipe_id, "title": "?", "servings": 2}
        payload = {"summary": "", "meals": [meal], "list_additions": [], "dropped": []}
        await proposals.create(session, cid, ctx.household.id, ctx.member.id, payload)
        [facts] = await collect_proposals(session, ctx, cid)
    [found] = facts.meals
    return found


async def test_a_rule_break_is_found_even_if_validate_missed_it(
    database_url: str, load: Loader, db: Engine
) -> None:
    # The harness re-checks Dietary Rules itself, so a bug in validate can't hide one.
    await load([CURRY, SALAD])
    with db.connect() as conn:
        curry = str(
            conn.execute(text("SELECT id FROM recipes WHERE slug = 'chicken-curry'")).scalar_one()
        )
    meal = await facts_for_a_proposal_of(database_url, curry)
    assert meal.exists and meal.rule_breaks == ("chicken thigh (vegetarian)",)
    assert meal.course == "main"  # for the only_courses check


async def test_a_made_up_recipe_id_is_recorded_as_missing(database_url: str, load: Loader) -> None:
    await load([SALAD])
    meal = await facts_for_a_proposal_of(database_url, str(uuid.UUID(int=0)))
    assert not meal.exists and meal.to_buy is None


async def test_a_scenario_naming_an_unknown_ingredient_fails_loudly(
    database_url: str, db: Engine
) -> None:
    async with open_database(database_url) as eval_db:
        async with eval_db.sessionmaker() as session:
            with pytest.raises(ValueError, match="dragonfruit jam"):
                await build_household(
                    session, Setup(kitchen={"dragonfruit jam": None}), today_in_sydney()
                )


async def test_recipe_vectors_are_copied_by_slug(database_url: str, load: Loader) -> None:
    await load([CURRY, PASTA, STIR_FRY, SALAD])
    async with open_database(database_url) as db:
        copied = await copy_recipe_embeddings(database_url, db, HashingEmbedder.model)
    assert copied == 4


def test_messages_name_the_days_the_way_the_app_does() -> None:
    days = [date(2026, 11, 29), date(2026, 11, 30), date(2026, 12, 1)]
    assert list_days(days) == "Sun 29, Mon 30 Nov and Tue 1 Dec"
    assert list_days(days[:1]) == "Sun 29 Nov"
    step = Say("Plan new recipes to shop for, for {days}. Swap {1}.")
    assert words(step, days) == (
        "Plan new recipes to shop for, for Sun 29, Mon 30 Nov and Tue 1 Dec. Swap Monday."
    )
