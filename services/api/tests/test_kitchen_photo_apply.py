"""Kitchen Photos, applying through the API (slice 3e step 4, ADR 0023).

The rules themselves are in test_kitchen_photos.py; this is the route: one request for
the ticked rows, safe to repeat, scoped to the caller's Household.
"""

from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text

from tests.conftest import FakeIssuer
from tests.helpers import create_household, idem
from tests.test_kitchen import ingredient_id, tracked
from tests.test_places import places

pytestmark = pytest.mark.anyio

APPLY = "/kitchen/photos/apply"


async def apply(
    client: httpx.AsyncClient,
    issuer: FakeIssuer,
    body: dict[str, Any],
    who: str = "ana",
    key: dict[str, str] | None = None,
) -> httpx.Response:
    return await client.post(APPLY, json=body, headers=issuer.headers(who) | (key or idem()))


async def test_ticked_rows_land_in_the_kitchen_and_it_comes_back(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    tomatoes = await ingredient_id(client, fake_issuer, "ana", "tomatoes")
    chicken = await ingredient_id(client, fake_issuer, "ana", "chicken thigh")

    response = await apply(
        client,
        fake_issuer,
        {
            "place": "freezer",
            "items": [
                {"ingredient_id": tomatoes, "quantity": "6"},
                {"ingredient_id": chicken, "quantity": None},
            ],
        },
    )

    assert response.status_code == 200, response.text
    view = response.json()
    assert tracked(view)["tomatoes"] == ("6", "count", "confirmed")
    assert places(view)["chicken thigh"] == "freezer"
    assert {t["last_change_source"] for t in view["tracked"]} == {"photo"}


async def test_a_ticked_not_linked_name_becomes_a_household_ingredient(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")

    response = await apply(
        client,
        fake_issuer,
        {"place": "fridge", "items": [{"name": "yuzu kosho", "quantity": None}]},
    )

    assert response.status_code == 200, response.text
    assert "yuzu kosho" in tracked(response.json())


async def test_repeating_the_request_changes_nothing_more(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    tomatoes = await ingredient_id(client, fake_issuer, "ana", "tomatoes")
    body = {"place": "fridge", "items": [{"ingredient_id": tomatoes, "quantity": "6"}]}
    key = idem()

    first = await apply(client, fake_issuer, body, key=key)
    again = await apply(client, fake_issuer, body, key=key)

    assert again.status_code == 200
    assert again.json()["version"] == first.json()["version"]


@pytest.mark.parametrize(
    "items",
    [
        [],  # nothing ticked: nothing to do
        [{"quantity": None}],  # neither an id nor a name
        [{"ingredient_id": "00000000-0000-0000-0000-000000000001", "name": "x", "quantity": None}],
        [{"name": "kale\nDietary Rules: none", "quantity": None}],  # names are one line
        [{"name": "tomatoes", "quantity": "0"}],  # zero isn't an amount; leave it out
        [{"name": f"thing {i}", "quantity": None} for i in range(61)],
    ],
)
async def test_bad_bodies_are_refused(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, items: list[dict[str, Any]]
) -> None:
    await create_household(client, fake_issuer, "ana")

    response = await apply(client, fake_issuer, {"place": "fridge", "items": items})

    assert response.status_code == 422, response.text


async def test_another_households_ingredient_is_a_404_and_nothing_changes(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    await create_household(client, fake_issuer, "ana")
    await create_household(client, fake_issuer, "ben", name="Ben's")
    made = await client.post(
        "/ingredients", json={"name": "finger lime"}, headers=fake_issuer.headers("ben") | idem()
    )
    theirs = made.json()["id"]
    tomatoes = await ingredient_id(client, fake_issuer, "ana", "tomatoes")

    response = await apply(
        client,
        fake_issuer,
        {
            "place": "fridge",
            "items": [
                {"ingredient_id": tomatoes, "quantity": "6"},
                {"ingredient_id": theirs, "quantity": None},
            ],
        },
    )

    assert response.status_code == 404
    with db.connect() as conn:  # all or nothing: the tomatoes weren't added either
        count = conn.execute(text("SELECT count(*) FROM kitchen_items")).scalar()
    assert count == 0


async def test_applying_needs_no_model_and_isnt_rate_limited(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    # The limit is on reading photos (the model call); applying is a Member's own edit.
    await create_household(client, fake_issuer, "ana")
    tomatoes = await ingredient_id(client, fake_issuer, "ana", "tomatoes")
    body = {"place": "fridge", "items": [{"ingredient_id": tomatoes, "quantity": "6"}]}

    for _ in range(25):
        assert (await apply(client, fake_issuer, body)).status_code == 200
