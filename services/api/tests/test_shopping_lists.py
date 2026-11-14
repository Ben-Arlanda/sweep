"""Shared Shopping Lists: what Members can do, and the rules that keep retries safe."""

import uuid
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text

from tests.conftest import FakeIssuer
from tests.helpers import create_household, idem, invite, join

pytestmark = pytest.mark.anyio


async def default_list_id(client: httpx.AsyncClient, issuer: FakeIssuer, subject: str) -> str:
    response = await client.get("/lists", headers=issuer.headers(subject))
    assert response.status_code == 200, response.text
    list_id: str = response.json()[0]["id"]
    return list_id


async def get_list(
    client: httpx.AsyncClient, issuer: FakeIssuer, subject: str, list_id: str
) -> dict[str, Any]:
    response = await client.get(f"/lists/{list_id}", headers=issuer.headers(subject))
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def add_item(
    client: httpx.AsyncClient,
    issuer: FakeIssuer,
    subject: str,
    list_id: str,
    text: str = "Milk",
    **extra: Any,
) -> dict[str, Any]:
    response = await client.post(
        f"/lists/{list_id}/items",
        json={"text": text, **extra},
        headers=issuer.headers(subject) | idem(),
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def household_of_two(client: httpx.AsyncClient, issuer: FakeIssuer) -> str:
    await create_household(client, issuer, "alice")
    await join(client, issuer, "bob", await invite(client, issuer, "alice"))
    return await default_list_id(client, issuer, "alice")


# --- Lists -------------------------------------------------------------------------


async def test_a_new_household_starts_with_one_shopping_list(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")

    response = await client.get("/lists", headers=fake_issuer.headers("alice"))

    assert [(lst["name"], lst["unchecked_count"]) for lst in response.json()] == [
        ("Shopping List", 0)
    ]


async def test_members_can_create_rename_and_delete_lists(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await household_of_two(client, fake_issuer)
    alice, bob = fake_issuer.headers("alice"), fake_issuer.headers("bob")

    created = await client.post("/lists", json={"name": "Party"}, headers=alice | idem())
    list_id = created.json()["id"]
    renamed = await client.patch(f"/lists/{list_id}", json={"name": "BBQ"}, headers=bob | idem())
    names = [lst["name"] for lst in (await client.get("/lists", headers=bob)).json()]
    deleted = await client.delete(f"/lists/{list_id}", headers=bob | idem())
    after = [lst["name"] for lst in (await client.get("/lists", headers=alice)).json()]

    assert created.status_code == 201
    assert renamed.json()["name"] == "BBQ"
    assert names == ["Shopping List", "BBQ"]
    assert deleted.status_code == 204
    assert after == ["Shopping List"]


async def test_list_summary_counts_items_still_to_buy(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await household_of_two(client, fake_issuer)
    milk = await add_item(client, fake_issuer, "alice", list_id, "Milk")
    await add_item(client, fake_issuer, "alice", list_id, "Eggs")
    await client.put(
        f"/lists/{list_id}/items/{milk['id']}/checked",
        json={"checked": True},
        headers=fake_issuer.headers("alice") | idem(),
    )

    response = await client.get("/lists", headers=fake_issuer.headers("bob"))

    assert response.json()[0]["unchecked_count"] == 1


async def test_a_household_has_at_most_20_lists(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    alice = fake_issuer.headers("alice")
    for n in range(19):
        ok = await client.post("/lists", json={"name": f"L{n}"}, headers=alice | idem())
        assert ok.status_code == 201

    response = await client.post("/lists", json={"name": "One too many"}, headers=alice | idem())

    assert response.status_code == 409
    assert response.json()["code"] == "limit_reached"


# --- Items -------------------------------------------------------------------------


async def test_one_member_adds_an_item_and_the_other_sees_it(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await household_of_two(client, fake_issuer)

    item = await add_item(
        client, fake_issuer, "alice", list_id, "  Chicken thighs ", quantity="1.5", unit="kg"
    )
    seen = await get_list(client, fake_issuer, "bob", list_id)

    assert item["text"] == "Chicken thighs"
    assert item["quantity"] == "1.5"
    assert item["checked"] is False
    assert seen["items"] == [item]
    assert seen["version"] == 2  # created at 1, then one change


async def test_checking_states_intent_so_repeating_it_is_harmless(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await household_of_two(client, fake_issuer)
    item = await add_item(client, fake_issuer, "alice", list_id)
    url = f"/lists/{list_id}/items/{item['id']}/checked"

    first = await client.put(
        url, json={"checked": True}, headers=fake_issuer.headers("alice") | idem()
    )
    # Bob, on his own device, ticks the same item a moment later.
    second = await client.put(
        url, json={"checked": True}, headers=fake_issuer.headers("bob") | idem()
    )
    unchecked = await client.put(
        url, json={"checked": False}, headers=fake_issuer.headers("bob") | idem()
    )

    assert first.json()["checked"] is True
    # Still checked, and still credited to whoever ticked it first. A toggle would have
    # un-ticked it here.
    assert second.json()["checked"] is True
    assert second.json()["checked_at"] == first.json()["checked_at"]
    assert second.json()["checked_by"] == first.json()["checked_by"]
    assert unchecked.json()["checked"] is False
    assert unchecked.json()["checked_by"] is None


async def test_edits_only_change_the_fields_they_send(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await household_of_two(client, fake_issuer)
    item = await add_item(client, fake_issuer, "alice", list_id, "Milk", quantity="1", unit="L")
    url = f"/lists/{list_id}/items/{item['id']}"

    # Both edit at the same time from stale screens: one renames, one changes quantity.
    await client.patch(
        url, json={"text": "Oat milk"}, headers=fake_issuer.headers("alice") | idem()
    )
    await client.patch(url, json={"quantity": "2"}, headers=fake_issuer.headers("bob") | idem())
    cleared = await client.patch(
        url, json={"unit": None}, headers=fake_issuer.headers("bob") | idem()
    )

    # Last write wins per field, so neither edit is lost.
    assert (cleared.json()["text"], cleared.json()["quantity"], cleared.json()["unit"]) == (
        "Oat milk",
        "2",
        None,
    )


async def test_deleting_an_item_that_is_already_gone_succeeds(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await household_of_two(client, fake_issuer)
    item = await add_item(client, fake_issuer, "alice", list_id)
    url = f"/lists/{list_id}/items/{item['id']}"

    first = await client.delete(url, headers=fake_issuer.headers("alice") | idem())
    # Bob deletes it too, from a screen that hadn't refreshed yet.
    second = await client.delete(url, headers=fake_issuer.headers("bob") | idem())

    assert (first.status_code, second.status_code) == (204, 204)
    assert (await get_list(client, fake_issuer, "bob", list_id))["items"] == []


@pytest.mark.parametrize(
    "body",
    [
        {"text": ""},
        {"text": "x" * 201},
        {"text": "Milk", "quantity": "0"},
        {"text": "Milk", "quantity": "-1"},
    ],
)
async def test_item_input_is_validated(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, body: dict[str, Any]
) -> None:
    list_id = await household_of_two(client, fake_issuer)

    response = await client.post(
        f"/lists/{list_id}/items", json=body, headers=fake_issuer.headers("alice") | idem()
    )

    assert response.status_code == 422


# --- Idempotency -------------------------------------------------------------------


async def test_mutations_require_an_idempotency_key(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await household_of_two(client, fake_issuer)

    response = await client.post(
        f"/lists/{list_id}/items", json={"text": "Milk"}, headers=fake_issuer.headers("alice")
    )

    assert response.status_code == 422


async def test_a_retried_request_is_applied_once(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await household_of_two(client, fake_issuer)
    headers = fake_issuer.headers("alice") | idem()

    # The phone sent this, lost signal before the reply arrived, and sent it again.
    first = await client.post(f"/lists/{list_id}/items", json={"text": "Milk"}, headers=headers)
    retry = await client.post(f"/lists/{list_id}/items", json={"text": "Milk"}, headers=headers)

    assert first.status_code == retry.status_code == 201
    assert retry.json() == first.json()
    assert len((await get_list(client, fake_issuer, "alice", list_id))["items"]) == 1


async def test_reusing_a_key_for_a_different_request_is_rejected(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await household_of_two(client, fake_issuer)
    headers = fake_issuer.headers("alice") | idem()
    await client.post(f"/lists/{list_id}/items", json={"text": "Milk"}, headers=headers)

    response = await client.post(f"/lists/{list_id}/items", json={"text": "Eggs"}, headers=headers)

    assert response.status_code == 422
    assert response.json()["code"] == "idempotency_key_reused"


async def test_keys_belong_to_one_member(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await household_of_two(client, fake_issuer)
    key = idem()

    await client.post(
        f"/lists/{list_id}/items", json={"text": "Milk"}, headers=fake_issuer.headers("alice") | key
    )
    bobs = await client.post(
        f"/lists/{list_id}/items", json={"text": "Milk"}, headers=fake_issuer.headers("bob") | key
    )

    # Bob's request happened to use the same key; it's his own request, not a replay.
    assert bobs.status_code == 201
    assert len((await get_list(client, fake_issuer, "alice", list_id))["items"]) == 2


async def test_a_failed_request_is_not_remembered(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    list_id = await household_of_two(client, fake_issuer)
    missing = f"/lists/{list_id}/items/{uuid.uuid4()}"
    headers = fake_issuer.headers("alice") | idem()

    response = await client.patch(missing, json={"text": "x"}, headers=headers)

    assert response.status_code == 404
    with db.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM idempotency_keys")).scalar_one() == 0


# --- Household isolation -----------------------------------------------------------


async def test_members_cannot_touch_another_households_list(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await household_of_two(client, fake_issuer)
    item = await add_item(client, fake_issuer, "alice", list_id)
    await create_household(client, fake_issuer, "mallory")
    mallory = fake_issuer.headers("mallory")
    own_list = await default_list_id(client, fake_issuer, "mallory")

    attempts = [
        await client.get(f"/lists/{list_id}", headers=mallory),
        await client.post(f"/lists/{list_id}/items", json={"text": "x"}, headers=mallory | idem()),
        await client.patch(f"/lists/{list_id}", json={"name": "x"}, headers=mallory | idem()),
        await client.delete(f"/lists/{list_id}", headers=mallory | idem()),
        # Alice's item id, smuggled in under Mallory's own list.
        await client.put(
            f"/lists/{own_list}/items/{item['id']}/checked",
            json={"checked": True},
            headers=mallory | idem(),
        ),
        await client.patch(
            f"/lists/{own_list}/items/{item['id']}", json={"text": "x"}, headers=mallory | idem()
        ),
    ]

    assert [r.status_code for r in attempts] == [404] * len(attempts)
    after = await get_list(client, fake_issuer, "alice", list_id)
    assert after["items"] == [item]
    assert [lst["name"] for lst in (await client.get("/lists", headers=mallory)).json()] == [
        "Shopping List"
    ]


async def test_deleting_the_last_member_removes_the_households_lists(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    await create_household(client, fake_issuer, "alice")
    list_id = await default_list_id(client, fake_issuer, "alice")
    await add_item(client, fake_issuer, "alice", list_id)

    await client.delete("/me", headers=fake_issuer.headers("alice"))

    with db.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM shopping_lists")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM shopping_list_items")).scalar_one() == 0


async def test_items_outlive_the_member_who_added_them(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    list_id = await household_of_two(client, fake_issuer)
    await add_item(client, fake_issuer, "bob", list_id)

    await client.delete("/me", headers=fake_issuer.headers("bob"))

    items = (await get_list(client, fake_issuer, "alice", list_id))["items"]
    assert len(items) == 1
    assert items[0]["added_by_member_id"] is None


async def test_the_device_may_choose_the_new_items_id(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    # Lets a phone add an item and tick it before the add has reached the server.
    list_id = await household_of_two(client, fake_issuer)
    chosen = str(uuid.uuid4())

    item = await add_item(client, fake_issuer, "alice", list_id, id=chosen)
    clash = await client.post(
        f"/lists/{list_id}/items",
        json={"id": chosen, "text": "Other"},
        headers=fake_issuer.headers("bob") | idem(),
    )

    assert item["id"] == chosen
    assert clash.status_code == 409
