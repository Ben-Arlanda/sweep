"""Slice 5d, step 1: which days a plan covers, what kind of plan, and Mon–Sun weeks.

The "Plan my week" sheet starts a Conversation with a mode and the days picked. The
Household's usual weekdays are remembered with its Preferences.
"""

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine

from app.agent.prompt import SYSTEM, today_in_sydney
from tests.conftest import ClientFor, FakeIssuer, Loader
from tests.fake_model import ScriptedModel, tool
from tests.fake_model import text as say_text
from tests.helpers import context_json, create_household, idem
from tests.test_agent import of, rid_in_db, say
from tests.test_recipes import CURRY, PASTA

pytestmark = pytest.mark.anyio

TODAY = today_in_sydney()
PREFS = "/households/current/preferences"


def day(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


async def start(
    client: httpx.AsyncClient, issuer: FakeIssuer, body: Mapping[str, object] | None
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
    bodies: list[Mapping[str, object] | None] = [None, {}]
    for body in bodies:
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


WEEKDAYS = "/households/current/plan-weekdays"


async def put_weekdays(
    client: httpx.AsyncClient, issuer: FakeIssuer, weekdays: list[int]
) -> httpx.Response:
    """Its own route, so the sheet saves only the days: sending the whole Preferences
    could overwrite a change another Member just made to the cuisines."""
    return await client.put(
        WEEKDAYS, json={"weekdays": weekdays}, headers=issuer.headers("ana") | idem()
    )


async def test_usual_days_start_as_weeknights_and_are_remembered(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    got = (await client.get(PREFS, headers=fake_issuer.headers("ana"))).json()
    assert got["plan_weekdays"] == [1, 2, 3, 4, 5]  # ISO weekdays: Monday is 1

    response = await put_weekdays(client, fake_issuer, [7, 1, 3])
    assert response.status_code == 200, response.text
    assert response.json() == {"weekdays": [1, 3, 7]}
    got = (await client.get(PREFS, headers=fake_issuer.headers("ana"))).json()
    assert got["plan_weekdays"] == [1, 3, 7]


async def test_the_days_and_the_other_preferences_dont_overwrite_each_other(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    prefs = {"household_size": 3, "cuisines": ["thai"]}
    await client.put(PREFS, json=prefs, headers=fake_issuer.headers("ana") | idem())
    await put_weekdays(client, fake_issuer, [6, 7])
    await client.put(PREFS, json=prefs, headers=fake_issuer.headers("ana") | idem())
    got = (await client.get(PREFS, headers=fake_issuer.headers("ana"))).json()
    assert got == {"household_size": 3, "cuisines": ["thai"], "plan_weekdays": [6, 7]}


async def test_usual_days_are_validated(client: httpx.AsyncClient, fake_issuer: FakeIssuer) -> None:
    await create_household(client, fake_issuer, "ana")
    for bad in ([], [0], [8], [1, 1]):
        response = await put_weekdays(client, fake_issuer, bad)
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


# --- step 2: the agent sees the mode and days; validate holds it to the days ---------


async def started(
    client: httpx.AsyncClient, issuer: FakeIssuer, body: Mapping[str, object] | None
) -> str:
    response = await start(client, issuer, body)
    assert response.status_code == 201, response.text
    cid: str = response.json()["id"]
    return cid


def context_of(model: ScriptedModel, call: int = 0) -> dict[str, Any]:
    return context_json(model.calls[call][-1]["content"][0]["text"])


@pytest.mark.parametrize(
    ("mode", "expected"),
    [("kitchen", "cook from my Kitchen"), ("new", "new recipes to shop for")],
)
async def test_every_turn_says_the_mode_and_the_days(
    client_for: ClientFor, fake_issuer: FakeIssuer, mode: str, expected: str
) -> None:
    model = ScriptedModel([[say_text("Sure.")], [say_text("Sure.")]])
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await started(client, fake_issuer, {"mode": mode, "days": [day(2), day(1)]})
        await say(client, fake_issuer, cid, "plan it")
        await say(client, fake_issuer, cid, "make them quick")  # not just the first turn

    for call in (0, 1):
        context = context_of(model, call)
        assert context["plan_mode"].startswith(expected)
        # With the weekday, so the model doesn't have to work it out.
        named = [f"{TODAY + timedelta(days=n):%a} {day(n)}" for n in (1, 2)]
        assert context["plan_these_days_only"] == named


async def test_a_free_chat_has_no_mode_or_days_in_its_context(
    client_for: ClientFor, fake_issuer: FakeIssuer
) -> None:
    model = ScriptedModel([[say_text("Sure.")]])
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await started(client, fake_issuer, None)
        await say(client, fake_issuer, cid, "hi")
    assert "plan_mode" not in context_of(model)
    assert "plan_these_days_only" not in context_of(model)


def test_the_fixed_prompt_explains_both_modes_and_the_days() -> None:
    # The prompt names the context's keys, so renaming one must update the prompt.
    assert 'plan_mode is "new recipes to shop for' in SYSTEM
    assert "search_recipes" in SYSTEM
    assert "plan_these_days_only" in SYSTEM


async def test_validate_sends_back_a_meal_on_a_day_that_was_not_picked(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY, PASTA])
    curry, pasta = await rid_in_db(db, "chicken-curry"), await rid_in_db(db, "tomato-pasta")
    model = ScriptedModel(
        [
            [
                tool("set_planned_meal", date=day(1), recipe_id=curry, servings=4),
                tool("set_planned_meal", date=day(2), recipe_id=pasta, servings=4),
            ],
            [tool("propose_plan", summary="Two dinners.")],
            # Sent back: day(2) wasn't picked. The agent takes it off and proposes again.
            [tool("remove_planned_meal", date=day(2))],
            [tool("propose_plan", summary="One dinner.")],
        ]
    )
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await started(client, fake_issuer, {"mode": "kitchen", "days": [day(1)]})
        events = await say(client, fake_issuer, cid, "plan it")

    [replan] = of(events, "replan")
    assert replan["problems"] == [f"{day(2)}: not one of the days picked for this plan ({day(1)})"]
    [proposal] = of(events, "proposal")
    assert [m["date"] for m in proposal["proposal"]["meals"]] == [day(1)]


async def test_a_plan_that_keeps_using_other_days_shows_them_as_left_out(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    """The model can't get round it: after the replans run out, the meal is dropped."""
    await load([CURRY, PASTA])
    curry, pasta = await rid_in_db(db, "chicken-curry"), await rid_in_db(db, "tomato-pasta")
    stubborn = [tool("propose_plan", summary="Two dinners.")]
    model = ScriptedModel(
        [
            [
                tool("set_planned_meal", date=day(1), recipe_id=curry, servings=4),
                tool("set_planned_meal", date=day(2), recipe_id=pasta, servings=4),
            ],
            stubborn,
            stubborn,
            stubborn,
        ]
    )
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await started(client, fake_issuer, {"mode": "kitchen", "days": [day(1)]})
        events = await say(client, fake_issuer, cid, "plan it")

    [proposal] = of(events, "proposal")
    assert [m["date"] for m in proposal["proposal"]["meals"]] == [day(1)]
    assert proposal["proposal"]["dropped"] == [
        f"{day(2)}: not one of the days picked for this plan ({day(1)})"
    ]
