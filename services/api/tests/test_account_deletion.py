"""In-app account deletion (App Store guideline 5.1.1(v))."""

import httpx
import pytest
from sqlalchemy import Engine, text

from tests.conftest import FakeIssuer
from tests.helpers import create_household, invite, join

pytestmark = pytest.mark.anyio


def count(db: Engine, table: str) -> int:
    with db.connect() as conn:
        return int(conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


async def test_last_member_deleting_removes_the_household(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    await create_household(client, fake_issuer, "alice")
    await invite(client, fake_issuer, "alice")

    response = await client.delete("/me", headers=fake_issuer.headers("alice"))

    assert response.status_code == 204
    assert count(db, "households") == 0
    assert count(db, "members") == 0
    assert count(db, "household_invites") == 0


async def test_owner_leaving_hands_ownership_to_longest_standing_member(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    await join(client, fake_issuer, "bob", await invite(client, fake_issuer, "alice"))
    await join(client, fake_issuer, "carol", await invite(client, fake_issuer, "alice"))

    await client.delete("/me", headers=fake_issuer.headers("alice"))

    bob = await client.get("/me", headers=fake_issuer.headers("bob"))
    carol = await client.get("/me", headers=fake_issuer.headers("carol"))
    assert bob.json()["member"]["role"] == "owner"
    assert carol.json()["member"]["role"] == "member"


async def test_member_deleting_leaves_the_household_intact(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    await join(client, fake_issuer, "bob", await invite(client, fake_issuer, "alice"))

    await client.delete("/me", headers=fake_issuer.headers("bob"))

    household = await client.get("/households/current", headers=fake_issuer.headers("alice"))
    assert [m["display_name"] for m in household.json()["members"]] == ["alice"]


async def test_deleted_account_can_start_fresh(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice", name="Old")
    await client.delete("/me", headers=fake_issuer.headers("alice"))

    fresh = await create_household(client, fake_issuer, "alice", name="New")

    assert fresh["household"]["name"] == "New"
