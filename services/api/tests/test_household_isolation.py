"""A Member can never read or change another Household's data.

These are the most important tests in this slice: every later feature (lists, Cabinet,
the agent) relies on this boundary holding.
"""

import httpx
import pytest

from tests.conftest import FakeIssuer
from tests.helpers import create_household, invite, join, member_ids

pytestmark = pytest.mark.anyio


async def test_members_only_see_their_own_household(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice", name="Alice's")
    await create_household(client, fake_issuer, "mallory", name="Mallory's")

    response = await client.get("/households/current", headers=fake_issuer.headers("mallory"))

    assert response.json()["name"] == "Mallory's"
    assert [m["display_name"] for m in response.json()["members"]] == ["mallory"]


async def test_owner_cannot_remove_a_member_of_another_household(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    await join(client, fake_issuer, "bob", await invite(client, fake_issuer, "alice"))
    await create_household(client, fake_issuer, "mallory")
    bob_id = (await member_ids(client, fake_issuer, "alice"))[1]

    response = await client.delete(
        f"/households/current/members/{bob_id}", headers=fake_issuer.headers("mallory")
    )

    # 404, not 403: don't confirm that the id exists somewhere else.
    assert response.status_code == 404
    assert len(await member_ids(client, fake_issuer, "alice")) == 2


async def test_member_of_one_household_cannot_join_another(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    await create_household(client, fake_issuer, "mallory")
    code = await invite(client, fake_issuer, "alice")

    response = await join(client, fake_issuer, "mallory", code)

    assert response.status_code == 409
    assert response.json()["code"] == "already_in_household"


async def test_removed_member_loses_access(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    await join(client, fake_issuer, "bob", await invite(client, fake_issuer, "alice"))
    bob_id = (await member_ids(client, fake_issuer, "alice"))[1]

    removed = await client.delete(
        f"/households/current/members/{bob_id}", headers=fake_issuer.headers("alice")
    )
    after = await client.get("/households/current", headers=fake_issuer.headers("bob"))

    assert removed.status_code == 204
    assert after.status_code == 403


async def test_non_owner_cannot_remove_members(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    await join(client, fake_issuer, "bob", await invite(client, fake_issuer, "alice"))
    alice_id = (await member_ids(client, fake_issuer, "alice"))[0]

    response = await client.delete(
        f"/households/current/members/{alice_id}", headers=fake_issuer.headers("bob")
    )

    assert response.status_code == 403


async def test_owner_cannot_remove_themselves(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    alice_id = (await member_ids(client, fake_issuer, "alice"))[0]

    response = await client.delete(
        f"/households/current/members/{alice_id}", headers=fake_issuer.headers("alice")
    )

    assert response.status_code == 409
