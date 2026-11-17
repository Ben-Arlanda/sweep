"""Used up / Ran out: gone from the Kitchen and onto the Shopping List, in one step.

Most households plan dinners only, so breakfast and lunch use never reaches the Kitchen
as a Cooked meal. Saying something's gone is the moment to buy it again. "Remove" (it
was never there) is a different action and doesn't touch the list.
"""

from typing import Any

import httpx
import pytest

from tests.conftest import FakeIssuer
from tests.helpers import create_household, idem
from tests.test_kitchen import add, ingredient_id, kitchen, list_id_of, staples, tracked

pytestmark = pytest.mark.anyio


async def used_up(
    client: httpx.AsyncClient, issuer: FakeIssuer, iid: str, key: dict[str, str] | None = None
) -> httpx.Response:
    return await client.post(
        f"/kitchen/used-up/{iid}", headers=issuer.headers("ana") | (key or idem())
    )


async def list_items(client: httpx.AsyncClient, issuer: FakeIssuer) -> list[dict[str, Any]]:
    body = (await client.get("/list", headers=issuer.headers("ana"))).json()
    items: list[dict[str, Any]] = body["items"]
    return items


async def set_amount(client: httpx.AsyncClient, issuer: FakeIssuer, iid: str, q: str) -> None:
    response = await client.put(
        f"/kitchen/items/{iid}", json={"quantity": q}, headers=issuer.headers("ana") | idem()
    )
    assert response.status_code == 200, response.text


async def test_a_tracked_item_used_up_leaves_the_kitchen_and_goes_on_the_list(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    cheese = await ingredient_id(client, fake_issuer, "ana", "goat cheese")
    await set_amount(client, fake_issuer, cheese, "150")

    response = await used_up(client, fake_issuer, cheese)

    assert response.status_code == 200, response.text
    assert "goat cheese" not in tracked(await kitchen(client, fake_issuer, "ana"))
    [item] = await list_items(client, fake_issuer)
    assert item["text"] == "Goat cheese"
    assert item["ingredient"]["name"] == "goat cheese"
    assert response.json() == {
        "list_id": await list_id_of(client, fake_issuer, "ana"),
        "list_item_id": item["id"],
    }


async def test_a_staple_ran_out_stays_a_staple_and_goes_on_the_list(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    salt = await ingredient_id(client, fake_issuer, "ana", "salt")

    response = await used_up(client, fake_issuer, salt)

    assert response.status_code == 200, response.text
    assert staples(await kitchen(client, fake_issuer, "ana"))["salt"] is False
    assert [i["text"] for i in await list_items(client, fake_issuer)] == ["Salt"]


async def test_already_on_the_list_unticked_isnt_added_twice(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    await add(client, fake_issuer, "ana", "2 L milk")
    milk = await ingredient_id(client, fake_issuer, "ana", "milk")  # a Staple

    response = await used_up(client, fake_issuer, milk)

    assert response.json()["list_item_id"] is None
    assert [i["text"] for i in await list_items(client, fake_issuer)] == ["Milk"]


async def test_repeating_the_request_adds_it_once(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    salt = await ingredient_id(client, fake_issuer, "ana", "salt")
    key = idem()

    first = await used_up(client, fake_issuer, salt, key)
    again = await used_up(client, fake_issuer, salt, key)

    assert again.json() == first.json()
    assert len(await list_items(client, fake_issuer)) == 1


async def test_something_not_in_the_kitchen_is_a_404_and_nothing_is_added(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    eggs = await ingredient_id(client, fake_issuer, "ana", "eggs")

    response = await used_up(client, fake_issuer, eggs)

    assert response.status_code == 404
    assert await list_items(client, fake_issuer) == []


async def test_another_households_ingredient_is_a_404(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    await create_household(client, fake_issuer, "ben", name="Ben's")
    made = await client.post(
        "/ingredients", json={"name": "finger lime"}, headers=fake_issuer.headers("ben") | idem()
    )

    assert (await used_up(client, fake_issuer, made.json()["id"])).status_code == 404


async def test_remove_is_still_just_remove(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    # "It was never there" (a misread photo): out of the Kitchen, not onto the list.
    await create_household(client, fake_issuer, "ana")
    eggs = await ingredient_id(client, fake_issuer, "ana", "eggs")
    await set_amount(client, fake_issuer, eggs, "6")

    response = await client.delete(
        f"/kitchen/items/{eggs}", headers=fake_issuer.headers("ana") | idem()
    )

    assert response.status_code == 204
    assert await list_items(client, fake_issuer) == []


def test_milk_is_a_default_staple() -> None:
    # Used a little at a time in meals nobody plans: "have" until it runs out.
    from app.data.ingredients import INGREDIENTS

    [milk] = [i for i in INGREDIENTS if i.name == "milk"]
    assert milk.is_default_staple
