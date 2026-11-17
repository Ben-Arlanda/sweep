"""Stock status the Member sets: In stock, Running low, Out (ADR 0024).

A Staple that runs out goes straight on the Shopping List; a Non-staple that runs out
stays in the Kitchen as Out and the app only offers to add it. Out Non-staples never
count as "have" for the planner or the agent.
"""

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from tests.conftest import FakeIssuer
from tests.helpers import create_household, idem
from tests.test_kitchen import add, ingredient_id, kitchen, list_id_of, tick

pytestmark = pytest.mark.anyio


async def set_stock(
    client: httpx.AsyncClient,
    issuer: FakeIssuer,
    iid: str,
    stock: str,
    key: dict[str, str] | None = None,
) -> httpx.Response:
    return await client.put(
        f"/kitchen/stock/{iid}",
        json={"stock": stock},
        headers=issuer.headers("ana") | (key or idem()),
    )


async def to_list(client: httpx.AsyncClient, issuer: FakeIssuer, iid: str) -> httpx.Response:
    return await client.post(f"/kitchen/to-list/{iid}", headers=issuer.headers("ana") | idem())


async def list_items(client: httpx.AsyncClient, issuer: FakeIssuer) -> list[dict[str, Any]]:
    body = (await client.get("/list", headers=issuer.headers("ana"))).json()
    items: list[dict[str, Any]] = body["items"]
    return items


async def set_amount(client: httpx.AsyncClient, issuer: FakeIssuer, iid: str, q: str) -> None:
    response = await client.put(
        f"/kitchen/items/{iid}", json={"quantity": q}, headers=issuer.headers("ana") | idem()
    )
    assert response.status_code == 200, response.text


def stock_of(cab: dict[str, Any]) -> dict[str, str]:
    return {r["ingredient"]["name"]: r["stock"] for r in cab["tracked"] + cab["staples"]}


async def test_everything_starts_in_stock(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    eggs = await ingredient_id(client, fake_issuer, "ana", "eggs")
    await set_amount(client, fake_issuer, eggs, "6")

    stock = stock_of(await kitchen(client, fake_issuer, "ana"))

    assert stock["eggs"] == "in_stock"
    assert stock["salt"] == "in_stock"


async def test_a_staple_running_low_stays_have_and_off_the_list(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    salt = await ingredient_id(client, fake_issuer, "ana", "salt")

    response = await set_stock(client, fake_issuer, salt, "low")

    assert response.status_code == 200, response.text
    assert response.json() == {"stock": "low", "list_id": None, "list_item_id": None}
    [row] = [
        s
        for s in (await kitchen(client, fake_issuer, "ana"))["staples"]
        if s["ingredient"]["name"] == "salt"
    ]
    assert (row["stock"], row["have"]) == ("low", True)
    assert await list_items(client, fake_issuer) == []


async def test_a_staple_out_goes_straight_on_the_list(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    salt = await ingredient_id(client, fake_issuer, "ana", "salt")

    response = await set_stock(client, fake_issuer, salt, "out")

    [item] = await list_items(client, fake_issuer)
    assert item["text"] == "Salt"
    assert response.json() == {
        "stock": "out",
        "list_id": await list_id_of(client, fake_issuer, "ana"),
        "list_item_id": item["id"],
    }
    assert stock_of(await kitchen(client, fake_issuer, "ana"))["salt"] == "out"


async def test_a_staple_out_already_on_the_list_isnt_added_twice(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    await add(client, fake_issuer, "ana", "2 L milk")
    milk = await ingredient_id(client, fake_issuer, "ana", "milk")  # a Staple

    response = await set_stock(client, fake_issuer, milk, "out")

    assert response.json()["list_item_id"] is None
    assert [i["text"] for i in await list_items(client, fake_issuer)] == ["Milk"]


async def test_a_non_staple_out_stays_in_the_kitchen_and_off_the_list(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    cheese = await ingredient_id(client, fake_issuer, "ana", "goat cheese")
    await set_amount(client, fake_issuer, cheese, "150")

    response = await set_stock(client, fake_issuer, cheese, "out")

    assert response.json() == {"stock": "out", "list_id": None, "list_item_id": None}
    [row] = (await kitchen(client, fake_issuer, "ana"))["tracked"]
    assert (row["ingredient"]["name"], row["stock"], row["quantity"]) == (
        "goat cheese",
        "out",
        "150",
    )
    assert await list_items(client, fake_issuer) == []


async def test_back_in_stock_clears_out_and_low(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    cheese = await ingredient_id(client, fake_issuer, "ana", "goat cheese")
    salt = await ingredient_id(client, fake_issuer, "ana", "salt")
    await set_amount(client, fake_issuer, cheese, "150")
    await set_stock(client, fake_issuer, cheese, "out")
    await set_stock(client, fake_issuer, salt, "low")

    await set_stock(client, fake_issuer, cheese, "in_stock")
    await set_stock(client, fake_issuer, salt, "in_stock")

    stock = stock_of(await kitchen(client, fake_issuer, "ana"))
    assert (stock["goat cheese"], stock["salt"]) == ("in_stock", "in_stock")


async def test_buying_it_clears_out_and_low(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    cheese = await ingredient_id(client, fake_issuer, "ana", "goat cheese")
    await set_amount(client, fake_issuer, cheese, "150")
    await set_stock(client, fake_issuer, cheese, "out")
    item = await add(client, fake_issuer, "ana", "200g goat cheese")

    await tick(client, fake_issuer, "ana", item)

    [row] = (await kitchen(client, fake_issuer, "ana"))["tracked"]
    # Out meant none left, so the purchase is all there is.
    assert (row["stock"], row["quantity"]) == ("in_stock", "200")


def test_out_non_staples_dont_count_as_have_for_planning() -> None:
    # get_kitchen hands planners and the agent `tracked` only; Out rows go to `tracked_out`.
    from app.models import KitchenItem
    from app.services.kitchen import split_out

    have = KitchenItem(ran_out_at=None)
    gone = KitchenItem(ran_out_at=datetime(2026, 11, 17, tzinfo=UTC))

    assert split_out([have, gone]) == ([have], [gone])


async def test_add_to_list_adds_once_and_leaves_the_kitchen_alone(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    cheese = await ingredient_id(client, fake_issuer, "ana", "goat cheese")
    await set_amount(client, fake_issuer, cheese, "150")
    await set_stock(client, fake_issuer, cheese, "out")

    first = await to_list(client, fake_issuer, cheese)
    again = await to_list(client, fake_issuer, cheese)

    assert first.status_code == 200, first.text
    assert first.json()["list_item_id"] is not None
    assert again.json()["list_item_id"] is None  # already there, unticked
    assert [i["text"] for i in await list_items(client, fake_issuer)] == ["Goat cheese"]
    assert stock_of(await kitchen(client, fake_issuer, "ana"))["goat cheese"] == "out"


async def test_repeating_a_stock_change_adds_it_once(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    salt = await ingredient_id(client, fake_issuer, "ana", "salt")
    key = idem()

    first = await set_stock(client, fake_issuer, salt, "out", key)
    again = await set_stock(client, fake_issuer, salt, "out", key)

    assert again.json() == first.json()
    assert len(await list_items(client, fake_issuer)) == 1


async def test_something_not_in_the_kitchen_is_a_404(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    eggs = await ingredient_id(client, fake_issuer, "ana", "eggs")

    assert (await set_stock(client, fake_issuer, eggs, "out")).status_code == 404
    assert (await to_list(client, fake_issuer, eggs)).status_code == 404
    assert await list_items(client, fake_issuer) == []


async def test_another_households_ingredient_is_a_404(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    await create_household(client, fake_issuer, "ben", name="Ben's")
    made = await client.post(
        "/ingredients", json={"name": "finger lime"}, headers=fake_issuer.headers("ben") | idem()
    )

    assert (await set_stock(client, fake_issuer, made.json()["id"], "out")).status_code == 404


async def test_an_unknown_stock_is_rejected(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    salt = await ingredient_id(client, fake_issuer, "ana", "salt")

    assert (await set_stock(client, fake_issuer, salt, "gone")).status_code == 422


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
