"""Dinner Ideas (slice 6e, ADR 0025): "Just tonight" shows tonight's best Kitchen Matches
that pass the Dietary Rules, chosen by code. Picking one plans it directly (no Proposal)."""

from datetime import timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text

from app.agent.prompt import today_in_sydney
from tests.conftest import FakeIssuer, Loader
from tests.helpers import create_household, idem
from tests.test_dietary_rules import SALAD
from tests.test_favourites import ALPHA, ZETA, heart, recipe_id
from tests.test_kitchen_first import ingredient_ids, stock
from tests.test_recipes import CURRY, PASTA, PAVLOVA, STIR_FRY

pytestmark = pytest.mark.anyio


async def ideas(client: httpx.AsyncClient, issuer: FakeIssuer, **params: Any) -> Any:
    response = await client.get("/dinner-ideas", params=params, headers=issuer.headers("ana"))
    assert response.status_code == 200, response.text
    return response.json()


async def plan_day(
    client: httpx.AsyncClient, issuer: FakeIssuer, day: str, rid: str
) -> httpx.Response:
    return await client.put(
        f"/meal-plan/days/{day}",
        json={"recipe_id": rid},
        headers=issuer.headers("ana") | idem(),
    )


async def test_ideas_are_the_best_kitchen_matches_with_what_they_use(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY, PASTA, STIR_FRY, SALAD, PAVLOVA])
    await create_household(client, fake_issuer, "ana")
    chicken, chickpeas = (await ingredient_ids(db, "chicken-curry"))[:2]
    await stock(client, fake_issuer, [chicken, chickpeas])

    found = await ideas(client, fake_issuer)

    assert [i["title"] for i in found] == [  # three by default, mains only
        "Chicken and chickpea curry",
        "Chickpea salad",
        "Beef and broccoli stir-fry",
    ]
    curry = found[0]
    assert curry["missing"] == ["onion"]
    assert set(curry["kitchen_uses"]) == {"chicken thigh", "chickpeas"}
    assert curry["favourite"] is False
    more = await ideas(client, fake_issuer, limit=6)
    assert [i["title"] for i in more][3:] == ["Quick tomato pasta"]


async def test_dietary_rules_always_apply(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([CURRY, PASTA, STIR_FRY, SALAD])
    await create_household(client, fake_issuer, "ana")
    response = await client.put(
        "/households/current/dietary-rules",
        json={"diets": ["vegetarian"], "excluded_ingredient_ids": []},
        headers=fake_issuer.headers("ana") | idem(),
    )
    assert response.status_code == 200, response.text

    found = await ideas(client, fake_issuer)

    assert {i["title"] for i in found} == {"Quick tomato pasta", "Chickpea salad"}


async def test_filters_quick_nothing_to_buy_and_exclude(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY, PASTA, STIR_FRY])
    await create_household(client, fake_issuer, "ana")
    curry = await recipe_id(db, "chicken-curry")
    await stock(client, fake_issuer, (await ingredient_ids(db, "chicken-curry"))[:3])  # oil: Staple

    quick = await ideas(client, fake_issuer, max_minutes=30)
    assert {i["title"] for i in quick} == {"Quick tomato pasta", "Beef and broccoli stir-fry"}
    ready = await ideas(client, fake_issuer, nothing_to_buy="true")
    assert [i["title"] for i in ready] == ["Chicken and chickpea curry"]
    others = await ideas(client, fake_issuer, exclude=[curry])
    assert curry not in {i["id"] for i in others}


async def test_a_favourite_wins_a_tie(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([ALPHA, ZETA])
    await create_household(client, fake_issuer, "ana")
    await heart(client, fake_issuer, await recipe_id(db, "zeta-stew"))

    found = await ideas(client, fake_issuer)

    assert [(i["title"], i["favourite"]) for i in found] == [
        ("Zeta stew", True),
        ("Alpha stew", False),
    ]


async def test_picking_an_idea_plans_it_directly(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY, PASTA])
    await create_household(client, fake_issuer, "ana")
    today = today_in_sydney().isoformat()
    pasta = await recipe_id(db, "tomato-pasta")

    response = await plan_day(client, fake_issuer, today, pasta)

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Quick tomato pasta"
    assert response.json()["servings"] == 4  # the recipe's, with no household size set
    week = (await client.get("/meal-plan", headers=fake_issuer.headers("ana"))).json()
    assert [(m["date"], m["title"]) for m in week["meals"]] == [(today, "Quick tomato pasta")]
    with db.connect() as conn:
        proposals = conn.execute(text("SELECT count(*) FROM proposals")).scalar_one()
        action = conn.execute(text("SELECT action FROM audit_log")).scalar_one()
    assert proposals == 0
    assert action == "meal.planned"


async def test_picking_again_replaces_the_day_unless_it_was_cooked(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY, PASTA])
    await create_household(client, fake_issuer, "ana")
    today = today_in_sydney().isoformat()
    pasta, curry = await recipe_id(db, "tomato-pasta"), await recipe_id(db, "chicken-curry")

    first = (await plan_day(client, fake_issuer, today, pasta)).json()
    second = await plan_day(client, fake_issuer, today, curry)
    assert second.status_code == 200
    assert second.json()["title"] == "Chicken and chickpea curry"

    cooked = await client.post(
        f"/planned-meals/{first['id']}/cooked", headers=fake_issuer.headers("ana") | idem()
    )
    assert cooked.status_code == 200, cooked.text
    refused = await plan_day(client, fake_issuer, today, pasta)
    assert refused.status_code == 409


async def test_planning_refuses_past_days_rule_breakers_and_others_recipes(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY, PASTA])
    await create_household(client, fake_issuer, "ana")
    today = today_in_sydney()
    curry = await recipe_id(db, "chicken-curry")

    past = await plan_day(client, fake_issuer, (today - timedelta(days=1)).isoformat(), curry)
    assert past.status_code == 422

    await client.put(
        "/households/current/dietary-rules",
        json={"diets": ["vegetarian"], "excluded_ingredient_ids": []},
        headers=fake_issuer.headers("ana") | idem(),
    )
    meat = await plan_day(client, fake_issuer, today.isoformat(), curry)
    assert meat.status_code == 409
    assert "Dietary Rules" in meat.json()["detail"]

    await create_household(client, fake_issuer, "zoe")
    lasagne = await client.post(
        "/recipes/imported",
        json={
            "title": "Zoe's lasagne",
            "servings": 4,
            "course": "main",
            "lines": [{"raw_text": "1 onion"}],
        },
        headers=fake_issuer.headers("zoe") | idem(),
    )
    hidden = await plan_day(client, fake_issuer, today.isoformat(), lasagne.json()["id"])
    assert hidden.status_code == 404
