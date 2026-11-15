"""Household Ingredients (ADR 0012): the Kitchen takes anything, and each Household's own
Ingredients stay private to it.

Visibility rule: a Household sees the shared starter Ingredients plus its own. Another
Household's Ingredient id is "not found" on every route that takes one (404, not 403:
don't confirm the id exists somewhere else).
"""

import uuid

import httpx
import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from tests.conftest import FakeIssuer
from tests.helpers import create_household, idem

pytestmark = pytest.mark.anyio


# --- Helpers ------------------------------------------------------------------------


def household_ingredient(db: Engine, household_id: str, name: str) -> str:
    """Arrange a Household Ingredient directly (the matcher creates them in normal use)."""
    with db.begin() as conn:
        found: uuid.UUID = conn.execute(
            text(
                "INSERT INTO ingredients (id, household_id, name, category, default_unit,"
                " is_default_staple) VALUES (gen_random_uuid(), :h, :n, 'other', 'count', false)"
                " RETURNING id"
            ),
            {"h": household_id, "n": name},
        ).scalar_one()
    return str(found)


async def new_household(
    client: httpx.AsyncClient, issuer: FakeIssuer, db: Engine, subject: str
) -> str:
    """Create a Household named after its owner and return its id."""
    await create_household(client, issuer, subject, name=subject)
    with db.begin() as conn:
        found = conn.execute(text("SELECT id FROM households WHERE name = :n"), {"n": subject})
        return str(found.scalar_one())


async def search(client: httpx.AsyncClient, issuer: FakeIssuer, subject: str, q: str) -> list[str]:
    response = await client.get("/ingredients", params={"q": q}, headers=issuer.headers(subject))
    assert response.status_code == 200, response.text
    return [i["name"] for i in response.json()]


async def list_id_of(client: httpx.AsyncClient, issuer: FakeIssuer, subject: str) -> str:
    response = await client.get("/list", headers=issuer.headers(subject))
    assert response.status_code == 200, response.text
    found: str = response.json()["id"]
    return found


async def two_households(
    client: httpx.AsyncClient, issuer: FakeIssuer, db: Engine
) -> tuple[str, str]:
    """Alice's Household owns "kale"; Mallory's Household owns nothing. Returns ids."""
    alice = await new_household(client, issuer, db, "alice")
    mallory = await new_household(client, issuer, db, "mallory")
    return household_ingredient(db, alice, "kale"), mallory


# --- Schema ------------------------------------------------------------------------


async def test_names_are_unique_per_owner(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    alice = await new_household(client, fake_issuer, db, "alice")
    mallory = await new_household(client, fake_issuer, db, "mallory")

    household_ingredient(db, alice, "kale")
    household_ingredient(db, mallory, "kale")  # another Household may use the name

    with pytest.raises(IntegrityError):
        household_ingredient(db, alice, "kale")
    with pytest.raises(IntegrityError):  # NULLS NOT DISTINCT: starters are one owner too
        with db.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO ingredients (id, name, category, default_unit,"
                    " is_default_staple) VALUES (gen_random_uuid(), 'pasta', 'other', 'count',"
                    " false)"
                )
            )


async def test_deleting_a_household_deletes_its_ingredients(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    alice = await new_household(client, fake_issuer, db, "alice")
    household_ingredient(db, alice, "kale")

    with db.begin() as conn:
        conn.execute(text("DELETE FROM households WHERE id = :h"), {"h": alice})
        left = conn.execute(text("SELECT count(*) FROM ingredients WHERE name = 'kale'"))

    assert left.scalar_one() == 0


# --- Visibility --------------------------------------------------------------------


async def test_search_shows_starters_and_only_your_own_household_ingredients(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    await two_households(client, fake_issuer, db)

    assert "kale" in await search(client, fake_issuer, "alice", "kale")
    assert "kale" not in await search(client, fake_issuer, "mallory", "kale")
    assert "pasta" in await search(client, fake_issuer, "mallory", "pasta")


async def test_another_households_ingredient_is_not_found_in_the_kitchen(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    kale, _ = await two_households(client, fake_issuer, db)
    mallory = fake_issuer.headers("mallory")

    tracked = await client.put(
        f"/kitchen/items/{kale}", json={"quantity": "1"}, headers=mallory | idem()
    )
    staple = await client.put(
        f"/kitchen/staples/{kale}", json={"have": True}, headers=mallory | idem()
    )

    assert tracked.status_code == 404
    assert staple.status_code == 404


async def test_your_own_household_ingredient_works_in_the_kitchen(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    kale, _ = await two_households(client, fake_issuer, db)

    response = await client.put(
        f"/kitchen/items/{kale}",
        json={"quantity": "2"},
        headers=fake_issuer.headers("alice") | idem(),
    )

    assert response.status_code == 200, response.text
    assert response.json()["ingredient"]["name"] == "kale"


async def test_another_households_ingredient_is_not_found_on_the_list(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    kale, _ = await two_households(client, fake_issuer, db)
    mallory = fake_issuer.headers("mallory")
    list_id = await list_id_of(client, fake_issuer, "mallory")

    added = await client.post(
        f"/lists/{list_id}/items",
        json={"text": "Greens", "ingredient_id": kale},
        headers=mallory | idem(),
    )
    item = await client.post(
        f"/lists/{list_id}/items", json={"text": "Greens"}, headers=mallory | idem()
    )
    relinked = await client.patch(
        f"/lists/{list_id}/items/{item.json()['id']}",
        json={"ingredient_id": kale},
        headers=mallory | idem(),
    )

    assert added.status_code == 404
    assert relinked.status_code == 404


async def test_another_households_ingredient_cannot_be_excluded_by_dietary_rules(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    kale, _ = await two_households(client, fake_issuer, db)

    response = await client.put(
        "/households/current/dietary-rules",
        json={"diets": [], "excluded_ingredient_ids": [kale]},
        headers=fake_issuer.headers("mallory") | idem(),
    )

    assert response.status_code == 404
