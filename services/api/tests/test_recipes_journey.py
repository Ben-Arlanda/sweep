"""Slice 6f, the Recipes journey: Dinner ideas moods, Serves, and All recipes sort + count.

Moods stay code (ADR 0025): Use my Kitchen ranks by what you have, Surprise me shuffles
the good matches once a day, Something specific searches first and ranks by Kitchen.
"""

import uuid
from datetime import date, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine

from app.services.dinner_ideas import shuffled_for_day
from tests.conftest import ClientFor, FakeIssuer, Loader
from tests.fake_model import ScriptedModel
from tests.helpers import create_household, idem
from tests.test_dietary_rules import SALAD
from tests.test_favourites import recipe_id
from tests.test_imported_recipes import nonna, save
from tests.test_kitchen_first import ingredient_ids, stock
from tests.test_recipes import CURRY, PASTA, PAVLOVA, STIR_FRY
from tests.test_search_fallback import DownEmbedder

pytestmark = pytest.mark.anyio

MAINS = [CURRY, PASTA, STIR_FRY, SALAD]


async def get(client: httpx.AsyncClient, issuer: FakeIssuer, path: str, **params: Any) -> Any:
    response = await client.get(path, params=params, headers=issuer.headers("ana"))
    assert response.status_code == 200, response.text
    return response.json()


def titles(found: list[dict[str, Any]]) -> list[str]:
    return [r["title"] for r in found]


# --- Dinner ideas moods -------------------------------------------------------------


async def test_something_specific_finds_it_first_then_ranks_by_kitchen(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load(MAINS)
    # Keywords (Voyage down) make the candidates exact: only chickpea dishes.
    async with client_for(ScriptedModel(), DownEmbedder()) as client:
        await create_household(client, fake_issuer, "ana")
        found = await get(client, fake_issuer, "/dinner-ideas", mood="specific", q="chickpeas")
    assert set(titles(found)) == {"Chicken and chickpea curry", "Chickpea salad"}


async def test_something_specific_needs_words(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    response = await client.get(
        "/dinner-ideas", params={"mood": "specific"}, headers=fake_issuer.headers("ana")
    )
    assert response.status_code == 422


async def test_surprise_me_shuffles_good_matches_but_is_steady_within_a_day(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load(MAINS)
    await create_household(client, fake_issuer, "ana")
    kitchen = titles(await get(client, fake_issuer, "/dinner-ideas", limit=4))
    first = titles(await get(client, fake_issuer, "/dinner-ideas", mood="surprise", limit=4))
    again = titles(await get(client, fake_issuer, "/dinner-ideas", mood="surprise", limit=4))
    assert sorted(first) == sorted(kitchen)  # the same good matches…
    assert first == again  # …in an order that holds for the day


async def test_vegetarian_just_this_once_fails_closed(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load(MAINS)
    await create_household(client, fake_issuer, "ana")
    found = await get(client, fake_issuer, "/dinner-ideas", vegetarian="true", limit=6)
    assert set(titles(found)) == {"Quick tomato pasta", "Chickpea salad"}
    # Not saved as a Rule: the next search is back to everything.
    assert len(await get(client, fake_issuer, "/dinner-ideas", limit=6)) == 4


# --- Serves -------------------------------------------------------------------------


async def test_planning_a_day_can_set_the_servings(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY])
    await create_household(client, fake_issuer, "ana")
    today = (await get(client, fake_issuer, "/meal-plan"))["today"]
    response = await client.put(
        f"/meal-plan/days/{today}",
        json={"recipe_id": await recipe_id(db, "chicken-curry"), "servings": 2},
        headers=fake_issuer.headers("ana") | idem(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["servings"] == 2


# --- All recipes: sort and count ----------------------------------------------------


async def test_sort_a_to_z_newest_and_recommended(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY, PASTA, STIR_FRY, PAVLOVA])
    await create_household(client, fake_issuer, "ana")
    assert (await save(client, fake_issuer, nonna())).status_code == 201
    await stock(client, fake_issuer, (await ingredient_ids(db, "chicken-curry"))[:3])

    a_to_z = titles(await get(client, fake_issuer, "/recipes"))
    assert a_to_z == sorted(a_to_z)
    newest = titles(await get(client, fake_issuer, "/recipes", sort="newest"))
    assert newest[0] == "Nonna's lasagne"  # saved after the Seed Recipes
    recommended = titles(await get(client, fake_issuer, "/recipes", sort="recommended"))
    assert recommended[0] == "Chicken and chickpea curry"  # the most in the Kitchen
    paged = await get(client, fake_issuer, "/recipes", sort="recommended", limit=2, offset=1)
    assert titles(paged) == recommended[1:3]


async def test_count_matches_the_filters(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([CURRY, PASTA, STIR_FRY, PAVLOVA])
    await create_household(client, fake_issuer, "ana")
    assert await get(client, fake_issuer, "/recipes/count") == {"count": 4}
    assert await get(client, fake_issuer, "/recipes/count", course="dessert") == {"count": 1}
    assert await get(client, fake_issuer, "/recipes/count", max_minutes=20) == {
        "count": len(await get(client, fake_issuer, "/recipes", max_minutes=20))
    }


def test_surprise_order_holds_for_a_day_and_changes_across_days() -> None:
    hid = uuid.uuid4()
    items = list(range(8))
    day = date(2026, 11, 18)
    assert shuffled_for_day(items, hid, day) == shuffled_for_day(items, hid, day)
    orders = {tuple(shuffled_for_day(items, hid, day + timedelta(days=n))) for n in range(7)}
    assert len(orders) > 1
    assert sorted(shuffled_for_day(items, hid, day)) == items  # the same ideas, reordered
