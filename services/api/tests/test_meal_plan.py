"""The Meal Plan and Mark as Cooked (slice 6a, step 4).

Cooked is the only thing that takes ingredients out of the Kitchen (ADR 0003). It only
touches Tracked items, never goes below zero, and can be undone.
"""

from datetime import timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text

from tests.conftest import FakeIssuer, Loader
from tests.helpers import create_household, idem
from tests.test_agent import MON, TODAY, TUE
from tests.test_approvals import rows
from tests.test_kitchen import ingredient_id
from tests.test_recipes import CURRY, PASTA

pytestmark = pytest.mark.anyio


def plan(db: Engine, day: str, slug: str, servings: int = 2, who: str = "ana") -> str:
    """Put a Planned Meal straight in the database (approving is tested elsewhere)."""
    with db.begin() as conn:
        found = conn.execute(
            text(
                "INSERT INTO planned_meals (id, household_id, date, recipe_id, servings)"
                " SELECT gen_random_uuid(), m.household_id, :day, r.id, :servings"
                " FROM members m, recipes r WHERE m.auth_subject = :who AND r.slug = :slug"
                " RETURNING id"
            ),
            {"day": day, "slug": slug, "servings": servings, "who": who},
        )
        return str(found.scalar_one())


async def kitchen(client: httpx.AsyncClient, issuer: FakeIssuer) -> dict[str, Any]:
    body = (await client.get("/kitchen", headers=issuer.headers("ana"))).json()
    return {i["ingredient"]["name"]: i for i in body["tracked"]}


async def track(client: httpx.AsyncClient, issuer: FakeIssuer, name: str, qty: str | None) -> None:
    iid = await ingredient_id(client, issuer, "ana", name)
    response = await client.put(
        f"/kitchen/items/{iid}", json={"quantity": qty}, headers=issuer.headers("ana") | idem()
    )
    assert response.status_code == 200, response.text


async def cooked(
    client: httpx.AsyncClient, issuer: FakeIssuer, mid: str, *, undo: bool = False, who: str = "ana"
) -> httpx.Response:
    method = "DELETE" if undo else "POST"
    return await client.request(
        method, f"/planned-meals/{mid}/cooked", headers=issuer.headers(who) | idem()
    )


async def test_the_meal_plan_shows_a_week_of_this_households_meals(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY, PASTA])
    await create_household(client, fake_issuer, "ana")
    await create_household(client, fake_issuer, "eve")
    plan(db, MON, "chicken-curry", 4)
    plan(db, TUE, "tomato-pasta")
    plan(db, (TODAY + timedelta(days=7)).isoformat(), "tomato-pasta")  # next week
    plan(db, MON, "tomato-pasta", who="eve")  # another Household's

    response = await client.get(
        "/meal-plan", params={"start": MON}, headers=fake_issuer.headers("ana")
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["start"] == MON
    assert [(m["date"], m["title"], m["servings"]) for m in body["meals"]] == [
        (MON, "Chicken and chickpea curry", 4),
        (TUE, "Quick tomato pasta", 2),
    ]
    assert body["meals"][0]["cooked_at"] is None


async def test_cooked_takes_scaled_amounts_from_tracked_items_only(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY])
    await create_household(client, fake_issuer, "ana")
    await track(client, fake_issuer, "chicken thigh", "1000")
    await track(client, fake_issuer, "chickpeas", "150")
    await track(client, fake_issuer, "onion", None)  # "we have some"
    mid = plan(db, MON, "chicken-curry", servings=2)  # the recipe serves 4: half of it

    response = await cooked(client, fake_issuer, mid)
    assert response.status_code == 200, response.text
    assert response.json()["cooked_at"] is not None

    after = await kitchen(client, fake_issuer)
    assert after["chicken thigh"]["quantity"] == "750"  # 1000 - 250
    assert after["chicken thigh"]["status"] == "estimated"
    assert "chickpeas" not in after  # needed 200, had 150: never below zero, so gone
    assert after["onion"]["quantity"] is None  # can't subtract from "some"
    assert after["onion"]["status"] == "estimated"
    # vegetable oil is a Staple: Cooked never touches Staples.
    staples = (await client.get("/kitchen", headers=fake_issuer.headers("ana"))).json()["staples"]
    assert {s["ingredient"]["name"]: s["have"] for s in staples}["vegetable oil"] is True


async def test_cooked_twice_deducts_once(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY])
    await create_household(client, fake_issuer, "ana")
    await track(client, fake_issuer, "chicken thigh", "1000")
    mid = plan(db, MON, "chicken-curry", servings=2)

    first = await cooked(client, fake_issuer, mid)
    again = await cooked(client, fake_issuer, mid)  # a new key: a second tap, not a retry
    assert again.status_code == 200 and again.json()["cooked_at"] == first.json()["cooked_at"]
    assert (await kitchen(client, fake_issuer))["chicken thigh"]["quantity"] == "750"


async def test_undoing_cooked_puts_back_what_it_took(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY])
    await create_household(client, fake_issuer, "ana")
    await track(client, fake_issuer, "chicken thigh", "1000")
    await track(client, fake_issuer, "chickpeas", "150")
    await track(client, fake_issuer, "onion", None)
    mid = plan(db, MON, "chicken-curry", servings=2)
    await cooked(client, fake_issuer, mid)

    response = await cooked(client, fake_issuer, mid, undo=True)
    assert response.status_code == 200, response.text
    assert response.json()["cooked_at"] is None

    after = await kitchen(client, fake_issuer)
    assert after["chicken thigh"]["quantity"] == "1000"
    assert after["chickpeas"]["quantity"] == "150"  # brought back
    assert {after[n]["status"] for n in ("chicken thigh", "chickpeas", "onion")} == {"confirmed"}
    actions = [r.action for r in rows(db, "SELECT action FROM audit_log ORDER BY id")]
    assert actions == ["meal.cooked", "meal.uncooked"]


async def test_a_cooked_meal_cant_be_removed_but_a_planned_one_can(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY, PASTA])
    await create_household(client, fake_issuer, "ana")
    eaten, later = plan(db, MON, "chicken-curry"), plan(db, TUE, "tomato-pasta")
    await cooked(client, fake_issuer, eaten)
    headers = fake_issuer.headers("ana") | idem()

    blocked = await client.delete(f"/planned-meals/{eaten}", headers=headers)
    assert blocked.status_code == 409
    removed = await client.delete(
        f"/planned-meals/{later}", headers=fake_issuer.headers("ana") | idem()
    )
    assert removed.status_code == 204
    assert [r.date for r in rows(db, "SELECT date::text FROM planned_meals")] == [MON]


async def test_another_households_meal_is_not_found(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY])
    await create_household(client, fake_issuer, "ana")
    await create_household(client, fake_issuer, "eve")
    mid = plan(db, MON, "chicken-curry")

    for undo in (False, True):
        response = await cooked(client, fake_issuer, mid, undo=undo, who="eve")
        assert response.status_code == 404
    assert rows(db, "SELECT cooked_at FROM planned_meals")[0].cooked_at is None


async def test_a_planned_meal_says_what_it_uses_from_the_kitchen(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    # Home's "uses your chicken thigh and chickpeas" (slice 6c): Tracked items only.
    await load([CURRY])
    await create_household(client, fake_issuer, "ana")
    await track(client, fake_issuer, "chicken thigh", "1000")
    await track(client, fake_issuer, "chickpeas", "150")  # not enough, but it's used
    plan(db, MON, "chicken-curry")
    # onion isn't in the Kitchen; vegetable oil is a Staple, which would be noise here.

    body = (
        await client.get("/meal-plan", params={"start": MON}, headers=fake_issuer.headers("ana"))
    ).json()
    assert body["meals"][0]["kitchen_uses"] == ["chicken thigh", "chickpeas"]


async def test_an_unknown_item_isnt_claimed_as_used(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY])
    await create_household(client, fake_issuer, "ana")
    await track(client, fake_issuer, "chicken thigh", "1000")
    await track(client, fake_issuer, "chickpeas", "400")
    with db.begin() as conn:  # confirmed long ago: it might not be there any more
        conn.execute(
            text(
                "UPDATE kitchen_items SET last_confirmed_at = now() - interval '90 days'"
                " WHERE ingredient_id = (SELECT id FROM ingredients WHERE name = 'chickpeas'"
                " AND household_id IS NULL)"
            )
        )
    plan(db, MON, "chicken-curry")

    body = (
        await client.get("/meal-plan", params={"start": MON}, headers=fake_issuer.headers("ana"))
    ).json()
    assert body["meals"][0]["kitchen_uses"] == ["chicken thigh"]


async def test_once_cooked_it_says_what_was_taken_out(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    # After Cooked the Kitchen has changed (chickpeas ran out), so the list comes from
    # what was actually deducted, not from today's Kitchen.
    await load([CURRY])
    await create_household(client, fake_issuer, "ana")
    await track(client, fake_issuer, "chicken thigh", "1000")
    await track(client, fake_issuer, "chickpeas", "150")
    await track(client, fake_issuer, "onion", None)
    mid = plan(db, MON, "chicken-curry", servings=2)

    response = await cooked(client, fake_issuer, mid)
    assert response.json()["kitchen_uses"] == ["chicken thigh", "chickpeas", "onion"]
    body = (
        await client.get("/meal-plan", params={"start": MON}, headers=fake_issuer.headers("ana"))
    ).json()
    assert body["meals"][0]["kitchen_uses"] == ["chicken thigh", "chickpeas", "onion"]

    undone = await cooked(client, fake_issuer, mid, undo=True)
    assert undone.json()["kitchen_uses"] == ["chicken thigh", "chickpeas", "onion"]


async def test_a_planned_meal_says_how_long_it_takes(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    """The Plan tab shows "25 min · Serves 4" per day, so the time comes with the meal."""
    await load([CURRY, PASTA])
    await create_household(client, fake_issuer, "ana")
    plan(db, MON, "chicken-curry")
    with db.begin() as conn:
        conn.execute(text("UPDATE recipes SET total_minutes = 35 WHERE slug = 'chicken-curry'"))

    body = (
        await client.get("/meal-plan", params={"start": MON}, headers=fake_issuer.headers("ana"))
    ).json()
    assert body["meals"][0]["total_minutes"] == 35
