"""Imported Recipes in search (slice 4d step 7): embedded when saved, without waiting.

One embedding call per Save with a short time limit. If it fails or is slow, the recipe
is saved anyway (browsing and Kitchen Match don't need a vector), and the next Save, or
the API starting, embeds whatever is still missing.
"""

from collections.abc import AsyncIterator
from typing import Any

import anyio
import httpx
import pytest
from sqlalchemy import Engine, text

from app.config import Settings
from app.embeddings import EmbeddingUnavailable, HashingEmbedder, Purpose
from app.main import create_app
from app.services import recipes
from tests.conftest import FakeIssuer
from tests.fake_model import ScriptedFetcher, ScriptedModel, ScriptedReader
from tests.helpers import create_household, idem
from tests.test_imported_recipes import nonna

pytestmark = pytest.mark.anyio


class FlakyEmbedder(HashingEmbedder):
    """The fake embedder, which can be told to fail or to be slow."""

    def __init__(self) -> None:
        self.mode = "ok"  # "ok", "down" or "slow"
        self.calls = 0

    async def embed(self, texts: list[str], purpose: Purpose) -> list[list[float]]:
        self.calls += 1
        if self.mode == "down":
            raise EmbeddingUnavailable("Voyage request failed (503)")
        if self.mode == "slow":
            await anyio.sleep(30)
        return await super().embed(texts, purpose)


@pytest.fixture
def embedder() -> FlakyEmbedder:
    return FlakyEmbedder()


@pytest.fixture
async def app_client(
    database_url: str, db: Engine, fake_issuer: FakeIssuer, embedder: FlakyEmbedder
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(
        Settings(database_url=database_url),
        token_verifier=fake_issuer.verifier(),
        embedder=embedder,
        agent_model=ScriptedModel(),
        recipe_reader=ScriptedReader(),
        page_fetcher=ScriptedFetcher(),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    await app.state.agent.checkpoints.close()
    await app.state.engine.dispose()


def vectors(db: Engine) -> dict[str, bytes]:
    """Title → content hash, for every embedded Imported Recipe."""
    with db.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT r.title, e.content_hash FROM recipe_embeddings e"
                " JOIN recipes r ON r.id = e.recipe_id WHERE r.kind = 'imported'"
            )
        )
        return {title: bytes(digest) for title, digest in rows}


async def save(client: httpx.AsyncClient, issuer: FakeIssuer, **changes: Any) -> httpx.Response:
    response = await client.post(
        "/recipes/imported", json=nonna(**changes), headers=issuer.headers("ana") | idem()
    )
    assert response.status_code == 201, response.text
    return response


async def test_a_saved_recipe_is_found_by_search(
    app_client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    await create_household(app_client, fake_issuer, "ana")
    await save(app_client, fake_issuer)
    assert list(vectors(db)) == ["Nonna's lasagne"]
    found = await app_client.get(
        "/recipes", params={"q": "nonna lasagne"}, headers=fake_issuer.headers("ana")
    )
    assert "Nonna's lasagne" in [r["title"] for r in found.json()]


async def test_editing_it_embeds_the_new_text(
    app_client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    await create_household(app_client, fake_issuer, "ana")
    recipe = (await save(app_client, fake_issuer)).json()
    before = vectors(db)["Nonna's lasagne"]
    response = await app_client.put(
        f"/recipes/imported/{recipe['id']}",
        json=nonna(title="Nonna's veg lasagne"),
        headers=fake_issuer.headers("ana") | idem(),
    )
    assert response.status_code == 200
    assert vectors(db)["Nonna's veg lasagne"] != before


async def test_embedding_down_still_saves_and_the_next_save_catches_up(
    app_client: httpx.AsyncClient, fake_issuer: FakeIssuer, embedder: FlakyEmbedder, db: Engine
) -> None:
    await create_household(app_client, fake_issuer, "ana")
    embedder.mode = "down"
    await save(app_client, fake_issuer)  # 201 all the same
    assert vectors(db) == {}

    embedder.mode = "ok"
    await save(app_client, fake_issuer, title="Pumpkin soup")
    assert sorted(vectors(db)) == ["Nonna's lasagne", "Pumpkin soup"]


async def test_a_slow_embedding_doesnt_hold_up_the_save(
    app_client: httpx.AsyncClient,
    fake_issuer: FakeIssuer,
    embedder: FlakyEmbedder,
    db: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(recipes, "EMBED_ON_SAVE_SECONDS", 0.2)
    await create_household(app_client, fake_issuer, "ana")
    embedder.mode = "slow"
    with anyio.fail_after(5):  # far less than the 30 s the embedder would take
        await save(app_client, fake_issuer)
    assert vectors(db) == {}


async def test_the_api_starting_catches_up_too(
    app_client: httpx.AsyncClient, fake_issuer: FakeIssuer, embedder: FlakyEmbedder, db: Engine
) -> None:
    await create_household(app_client, fake_issuer, "ana")
    embedder.mode = "down"
    await save(app_client, fake_issuer)
    embedder.mode = "ok"
    transport = app_client._transport  # noqa: SLF001 - the app behind this test client
    app: Any = transport.app  # type: ignore[attr-defined]
    assert await recipes.catch_up_imported(app.state.sessionmaker, embedder) == 1
    assert list(vectors(db)) == ["Nonna's lasagne"]
