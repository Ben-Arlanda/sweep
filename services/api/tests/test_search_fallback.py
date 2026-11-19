"""Search when Voyage is down: by keyword instead (R2, slice 9), not an error.

The free tier allows about 3 embedding calls a minute, and a week plan searches several
times at once, so "unavailable" was common. Keywords rank worse than meaning (ADR 0022)
but find real recipes, which beats planning without search at all.
"""

import uuid
from typing import Any

import pytest

from app.db import make_engine, make_sessionmaker
from app.embeddings import EmbeddingUnavailable, HashingEmbedder, Purpose
from app.services import recipes
from tests.conftest import ClientFor, FakeIssuer, Loader
from tests.fake_model import Messages, ScriptedModel, last_result, tool
from tests.helpers import create_household
from tests.test_agent import say, start
from tests.test_recipes import CURRY, PASTA, PAVLOVA, STIR_FRY

pytestmark = pytest.mark.anyio


class DownEmbedder(HashingEmbedder):
    """Every call fails, like Voyage answering 429."""

    async def embed(self, texts: list[str], purpose: Purpose) -> list[list[float]]:
        raise EmbeddingUnavailable("Voyage request failed (429)")


async def found(database_url: str, embedder: Any, query: str) -> list[str]:
    engine = make_engine(database_url)
    async with make_sessionmaker(engine)() as session:
        rows = await recipes.search_or_keywords(
            session, uuid.uuid4(), embedder, query, recipes.RecipeFilters(), 10
        )
    await engine.dispose()
    return [r.title for r, _score in rows]


async def test_search_down_finds_by_keyword(database_url: str, load: Loader) -> None:
    await load([CURRY, PASTA, PAVLOVA, STIR_FRY])
    assert await found(database_url, DownEmbedder(), "chicken curry") == [
        "Chicken and chickpea curry"
    ]


async def test_no_embedder_finds_by_keyword(database_url: str, load: Loader) -> None:
    await load([CURRY, PASTA, PAVLOVA, STIR_FRY])
    assert await found(database_url, None, "pasta") == ["Quick tomato pasta"]


async def test_search_up_still_searches_by_meaning(database_url: str, load: Loader) -> None:
    await load([CURRY, PASTA, PAVLOVA, STIR_FRY])
    # By meaning, every recipe comes back ranked; keywords would find only the curry.
    assert len(await found(database_url, HashingEmbedder(), "chicken curry")) == 4


async def test_the_recipes_screen_searches_by_keyword_when_voyage_is_down(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([CURRY, PASTA, PAVLOVA, STIR_FRY])
    async with client_for(ScriptedModel(), DownEmbedder()) as client:
        await create_household(client, fake_issuer, "ana")
        got = await client.get(
            "/recipes", params={"q": "pasta"}, headers=fake_issuer.headers("ana")
        )
    assert got.status_code == 200, got.text
    assert [r["title"] for r in got.json()] == ["Quick tomato pasta"]


async def test_the_agent_still_gets_recipes_when_voyage_is_down(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([CURRY, PASTA, PAVLOVA, STIR_FRY])
    seen: list[Any] = []

    def look(messages: Messages) -> list[dict[str, Any]]:
        seen.append(last_result(messages))
        return [tool("recipes_from_kitchen", query="curry")]

    def look_again(messages: Messages) -> list[dict[str, Any]]:
        seen.append(last_result(messages))
        return [{"type": "text", "text": "Found some."}]

    model = ScriptedModel([[tool("search_recipes", query="chicken curry")], look, look_again])
    async with client_for(model, DownEmbedder()) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await start(client, fake_issuer)
        await say(client, fake_issuer, cid, "a curry please")

    searched, from_kitchen = seen
    assert [r["title"] for r in searched] == ["Chicken and chickpea curry"]
    assert "Chicken and chickpea curry" in [r["title"] for r in from_kitchen]
