"""Shops: Household labels for where to buy a Shopping List item (ADR 0009)."""

from typing import Any

import httpx
import pytest

from tests.conftest import FakeIssuer
from tests.helpers import create_household, idem, invite, join
from tests.test_shopping_lists import add_item, default_list_id

pytestmark = pytest.mark.anyio


async def the_list(client: httpx.AsyncClient, issuer: FakeIssuer, subject: str) -> dict[str, Any]:
    response = await client.get("/list", headers=issuer.headers(subject))
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def shop_id(client: httpx.AsyncClient, issuer: FakeIssuer, subject: str, name: str) -> str:
    shops = (await the_list(client, issuer, subject))["shops"]
    return str(next(s["id"] for s in shops if s["name"] == name))


async def two_members(client: httpx.AsyncClient, issuer: FakeIssuer) -> str:
    await create_household(client, issuer, "alice")
    await join(client, issuer, "bob", await invite(client, issuer, "alice"))
    return await default_list_id(client, issuer, "alice")


async def test_members_add_rename_and_delete_shops(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await two_members(client, fake_issuer)
    alice, bob = fake_issuer.headers("alice"), fake_issuer.headers("bob")

    added = await client.post("/shops", json={"name": "  IGA "}, headers=alice | idem())
    renamed = await client.patch(
        f"/shops/{added.json()['id']}", json={"name": "IGA Newtown"}, headers=bob | idem()
    )
    coles = await shop_id(client, fake_issuer, "bob", "Coles")
    deleted = await client.delete(f"/shops/{coles}", headers=bob | idem())

    assert added.status_code == 201
    assert added.json()["name"] == "IGA"  # trimmed
    assert renamed.json()["name"] == "IGA Newtown"
    assert deleted.status_code == 204
    names = [s["name"] for s in (await the_list(client, fake_issuer, "alice"))["shops"]]
    assert names == ["Aldi", "IGA Newtown", "Woolies"]


async def test_shop_names_are_unique_in_a_household_ignoring_case(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    alice = fake_issuer.headers("alice")
    aldi = await shop_id(client, fake_issuer, "alice", "Aldi")

    clash = await client.post("/shops", json={"name": "coles"}, headers=alice | idem())
    rename_clash = await client.patch(
        f"/shops/{aldi}", json={"name": "COLES"}, headers=alice | idem()
    )

    assert clash.status_code == 409
    assert rename_clash.status_code == 409


async def test_shop_names_are_validated(client: httpx.AsyncClient, fake_issuer: FakeIssuer) -> None:
    await create_household(client, fake_issuer, "alice")
    alice = fake_issuer.headers("alice")

    for bad in ("", "   ", "x" * 41):
        response = await client.post("/shops", json={"name": bad}, headers=alice | idem())
        assert response.status_code == 422, bad


async def test_a_household_has_at_most_20_shops(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    alice = fake_issuer.headers("alice")
    for n in range(17):  # plus the three it starts with
        ok = await client.post("/shops", json={"name": f"Shop {n}"}, headers=alice | idem())
        assert ok.status_code == 201

    response = await client.post("/shops", json={"name": "One too many"}, headers=alice | idem())

    assert response.status_code == 409
    assert response.json()["code"] == "limit_reached"


async def test_items_are_tagged_when_added_and_retagged_or_cleared_later(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await two_members(client, fake_issuer)
    aldi = await shop_id(client, fake_issuer, "alice", "Aldi")
    coles = await shop_id(client, fake_issuer, "alice", "Coles")
    bob = fake_issuer.headers("bob")

    item = await add_item(client, fake_issuer, "alice", list_id, "Bread", shop_id=aldi)
    moved = await client.patch(
        f"/lists/{list_id}/items/{item['id']}", json={"shop_id": coles}, headers=bob | idem()
    )
    cleared = await client.patch(
        f"/lists/{list_id}/items/{item['id']}", json={"shop_id": None}, headers=bob | idem()
    )
    untagged = await add_item(client, fake_issuer, "alice", list_id, "Milk")

    assert item["shop_id"] == aldi
    assert moved.json()["shop_id"] == coles
    assert cleared.json()["shop_id"] is None
    assert untagged["shop_id"] is None


async def test_deleting_a_shop_keeps_its_items_as_any_shop(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await two_members(client, fake_issuer)
    aldi = await shop_id(client, fake_issuer, "alice", "Aldi")
    await add_item(client, fake_issuer, "alice", list_id, "Bread", shop_id=aldi)

    await client.delete(f"/shops/{aldi}", headers=fake_issuer.headers("bob") | idem())
    again = await client.delete(f"/shops/{aldi}", headers=fake_issuer.headers("bob") | idem())

    items = (await the_list(client, fake_issuer, "alice"))["items"]
    assert [(i["text"], i["shop_id"]) for i in items] == [("Bread", None)]
    assert again.status_code == 204  # already gone is fine


async def test_shop_changes_bump_the_list_version(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    # Devices refetch on a newer version; a renamed Shop changes how the list looks.
    await create_household(client, fake_issuer, "alice")
    before = (await the_list(client, fake_issuer, "alice"))["version"]

    await client.post("/shops", json={"name": "IGA"}, headers=fake_issuer.headers("alice") | idem())

    assert (await the_list(client, fake_issuer, "alice"))["version"] == before + 1


async def test_shops_never_cross_households(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await two_members(client, fake_issuer)
    await create_household(client, fake_issuer, "mallory")
    mallory = fake_issuer.headers("mallory")
    alices_aldi = await shop_id(client, fake_issuer, "alice", "Aldi")
    mallory_list = await default_list_id(client, fake_issuer, "mallory")
    item = await add_item(client, fake_issuer, "alice", list_id)

    attempts = [
        await client.patch(f"/shops/{alices_aldi}", json={"name": "x"}, headers=mallory | idem()),
        # Alice's Shop on Mallory's own item, and on a new item.
        await client.post(
            f"/lists/{mallory_list}/items",
            json={"text": "x", "shop_id": alices_aldi},
            headers=mallory | idem(),
        ),
    ]
    mallory_delete = await client.delete(f"/shops/{alices_aldi}", headers=mallory | idem())
    mallory_item = await add_item(client, fake_issuer, "mallory", mallory_list)
    retag = await client.patch(
        f"/lists/{mallory_list}/items/{mallory_item['id']}",
        json={"shop_id": alices_aldi},
        headers=mallory | idem(),
    )

    assert [r.status_code for r in attempts] == [404, 404]
    assert retag.status_code == 404
    # Deleting is "make sure it's gone from MY Household": quietly does nothing here.
    assert mallory_delete.status_code == 204
    alice_view = await the_list(client, fake_issuer, "alice")
    assert "Aldi" in [s["name"] for s in alice_view["shops"]]
    assert alice_view["items"][0]["id"] == item["id"]
