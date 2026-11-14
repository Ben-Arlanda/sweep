"""Creating a Household, inviting and joining."""

import httpx
import pytest
from sqlalchemy import Engine, text

from tests.conftest import FakeIssuer
from tests.helpers import create_household, invite, join

pytestmark = pytest.mark.anyio


async def test_creating_a_household_makes_you_its_owner(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    created = await create_household(client, fake_issuer, "alice", name="The Flat")

    me = await client.get("/me", headers=fake_issuer.headers("alice"))

    assert me.status_code == 200
    assert me.json()["household"]["name"] == "The Flat"
    assert me.json()["member"]["role"] == "owner"
    assert me.json() == created


async def test_cannot_create_a_second_household(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")

    response = await client.post(
        "/households",
        json={"name": "Another", "display_name": "alice"},
        headers=fake_issuer.headers("alice"),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "already_in_household"


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
async def test_household_name_is_validated(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, name: str
) -> None:
    response = await client.post(
        "/households",
        json={"name": name, "display_name": "alice"},
        headers=fake_issuer.headers("alice"),
    )

    assert response.status_code == 422


async def test_invited_person_joins_as_member(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    code = await invite(client, fake_issuer, "alice")

    joined = await join(client, fake_issuer, "bob", code)

    assert joined.status_code == 200
    assert joined.json()["member"]["role"] == "member"
    household = await client.get("/households/current", headers=fake_issuer.headers("alice"))
    assert sorted(m["display_name"] for m in household.json()["members"]) == ["alice", "bob"]


async def test_invite_codes_are_case_insensitive(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    code = await invite(client, fake_issuer, "alice")

    joined = await join(client, fake_issuer, "bob", code.lower())

    assert joined.status_code == 200


async def test_only_the_owner_can_invite(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    await join(client, fake_issuer, "bob", await invite(client, fake_issuer, "alice"))

    response = await client.post("/households/current/invites", headers=fake_issuer.headers("bob"))

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


async def test_invite_can_only_be_used_once(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    code = await invite(client, fake_issuer, "alice")
    await join(client, fake_issuer, "bob", code)

    response = await join(client, fake_issuer, "carol", code)

    assert response.status_code == 404
    assert response.json()["code"] == "invite_invalid"


async def test_expired_invite_is_rejected(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    await create_household(client, fake_issuer, "alice")
    code = await invite(client, fake_issuer, "alice")
    with db.begin() as conn:
        conn.execute(text("UPDATE household_invites SET expires_at = now() - interval '1 minute'"))

    response = await join(client, fake_issuer, "bob", code)

    assert response.status_code == 404
    assert response.json()["code"] == "invite_invalid"


async def test_unknown_invite_is_rejected(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    response = await join(client, fake_issuer, "bob", "NOPE2345")

    assert response.status_code == 404


async def test_invite_expires_in_seven_days(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    await create_household(client, fake_issuer, "alice")
    await invite(client, fake_issuer, "alice")

    with db.connect() as conn:
        lifetime = conn.execute(
            text("SELECT expires_at - created_at FROM household_invites")
        ).scalar_one()

    assert lifetime.days == 7
