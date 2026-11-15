"""Slice 5d, step 1: which days a plan covers, what kind of plan, and Mon–Sun weeks.

The "Plan my week" sheet starts a Conversation with a mode and the days picked. The
Household's usual weekdays are remembered with its Preferences.
"""

from datetime import timedelta

import httpx
import pytest

from app.agent.prompt import today_in_sydney
from tests.conftest import FakeIssuer
from tests.helpers import create_household, idem

pytestmark = pytest.mark.anyio

TODAY = today_in_sydney()
PREFS = "/households/current/preferences"


def day(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


async def start(
    client: httpx.AsyncClient, issuer: FakeIssuer, body: dict[str, object] | None
) -> httpx.Response:
    return await client.post("/conversations", json=body, headers=issuer.headers("ana"))


# --- a Conversation remembers its mode and days ------------------------------------


async def test_a_plan_starts_with_a_mode_and_days(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    response = await start(client, fake_issuer, {"mode": "new", "days": [day(2), day(1)]})
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["plan_mode"] == "new"
    assert created["plan_days"] == [day(1), day(2)]  # sorted

    got = await client.get(f"/conversations/{created['id']}", headers=fake_issuer.headers("ana"))
    assert got.json()["plan_mode"] == "new"
    assert got.json()["plan_days"] == [day(1), day(2)]


async def test_a_plain_chat_has_no_mode_or_days(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    for body in (None, {}):
        created = (await start(client, fake_issuer, body)).json()
        assert created["plan_mode"] is None
        assert created["plan_days"] is None


async def test_days_must_be_ones_a_plan_can_cover(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    bad = [
        {"mode": "kitchen", "days": [day(-1)]},  # already gone
        {"mode": "kitchen", "days": [day(14)]},  # past the 14 days a plan covers
        {"mode": "kitchen", "days": [day(1), day(1)]},  # twice
        {"mode": "kitchen", "days": []},  # nothing to plan
        {"mode": "something", "days": [day(1)]},
    ]
    for body in bad:
        response = await start(client, fake_issuer, body)
        assert response.status_code == 422, (body, response.text)
    assert (
        await start(client, fake_issuer, {"mode": "kitchen", "days": [day(0), day(13)]})
    ).status_code == 201


# --- the Household's usual days ------------------------------------------------------


async def put_prefs(
    client: httpx.AsyncClient, issuer: FakeIssuer, body: dict[str, object]
) -> httpx.Response:
    return await client.put(PREFS, json=body, headers=issuer.headers("ana") | idem())


async def test_usual_days_start_as_weeknights_and_are_remembered(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    got = (await client.get(PREFS, headers=fake_issuer.headers("ana"))).json()
    assert got["plan_weekdays"] == [1, 2, 3, 4, 5]  # ISO weekdays: Monday is 1

    assert (await put_prefs(client, fake_issuer, {"plan_weekdays": [7, 1, 3]})).status_code == 200
    got = (await client.get(PREFS, headers=fake_issuer.headers("ana"))).json()
    assert got["plan_weekdays"] == [1, 3, 7]


async def test_saving_other_preferences_keeps_the_usual_days(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    """The Dietary Rules screen doesn't know about days. Saving it mustn't reset them."""
    await create_household(client, fake_issuer, "ana")
    await put_prefs(client, fake_issuer, {"plan_weekdays": [6, 7]})
    await put_prefs(client, fake_issuer, {"household_size": 3, "cuisines": ["thai"]})
    got = (await client.get(PREFS, headers=fake_issuer.headers("ana"))).json()
    assert got["plan_weekdays"] == [6, 7]
    assert got["household_size"] == 3


async def test_usual_days_are_validated(client: httpx.AsyncClient, fake_issuer: FakeIssuer) -> None:
    await create_household(client, fake_issuer, "ana")
    for bad in ([], [0], [8], [1, 1]):
        response = await put_prefs(client, fake_issuer, {"plan_weekdays": bad})
        assert response.status_code == 422, (bad, response.text)


# --- the Meal Plan reads Mon–Sun weeks -----------------------------------------------


async def test_the_meal_plan_starts_on_this_weeks_monday_and_says_what_today_is(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    body = (await client.get("/meal-plan", headers=fake_issuer.headers("ana"))).json()
    monday = TODAY - timedelta(days=TODAY.weekday())
    assert body["start"] == monday.isoformat()
    assert body["end"] == (monday + timedelta(days=6)).isoformat()
    assert body["today"] == TODAY.isoformat()
