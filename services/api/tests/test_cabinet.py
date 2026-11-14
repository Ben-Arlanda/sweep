"""The Cabinet: Staples and Tracked Ingredients, fed by ticking off the Shopping List."""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text

from app.models import CabinetItem, ChangeSource
from app.services.cabinet import Status, status_of
from tests.conftest import FakeIssuer
from tests.helpers import create_household, idem, invite, join

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 11, 14, 12, tzinfo=UTC)


# --- Calculated status (pure) --------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "age", "expected"),
    [
        (ChangeSource.PURCHASE, timedelta(days=1), Status.CONFIRMED),
        (ChangeSource.MANUAL, timedelta(days=6), Status.CONFIRMED),
        (ChangeSource.MANUAL, timedelta(days=7), Status.ESTIMATED),  # nobody re-checked
        (ChangeSource.COOKED, timedelta(hours=1), Status.ESTIMATED),  # deductions are guesses
        (ChangeSource.COOKED, timedelta(days=13), Status.ESTIMATED),
        (ChangeSource.PURCHASE, timedelta(days=14), Status.UNKNOWN),
        (ChangeSource.COOKED, timedelta(days=30), Status.UNKNOWN),
    ],
)
def test_status_is_calculated_from_source_and_age(
    source: ChangeSource, age: timedelta, expected: Status
) -> None:
    item = CabinetItem(last_change_source=source, last_confirmed_at=NOW - age)

    assert status_of(item, NOW) == expected


# --- Helpers ------------------------------------------------------------------------


async def cabinet(client: httpx.AsyncClient, issuer: FakeIssuer, subject: str) -> dict[str, Any]:
    response = await client.get("/cabinet", headers=issuer.headers(subject))
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def tracked(cab: dict[str, Any]) -> dict[str, tuple[str | None, str, str]]:
    """{ingredient name: (quantity, unit, status)}"""
    return {
        t["ingredient"]["name"]: (t["quantity"], t["unit"], t["status"]) for t in cab["tracked"]
    }


def staples(cab: dict[str, Any]) -> dict[str, bool]:
    return {s["ingredient"]["name"]: s["have"] for s in cab["staples"]}


async def list_id_of(client: httpx.AsyncClient, issuer: FakeIssuer, subject: str) -> str:
    lid: str = (await client.get("/lists", headers=issuer.headers(subject))).json()[0]["id"]
    return lid


async def add(
    client: httpx.AsyncClient, issuer: FakeIssuer, subject: str, text: str, **extra: Any
) -> dict[str, Any]:
    list_id = await list_id_of(client, issuer, subject)
    response = await client.post(
        f"/lists/{list_id}/items",
        json={"text": text, **extra},
        headers=issuer.headers(subject) | idem(),
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def tick(
    client: httpx.AsyncClient,
    issuer: FakeIssuer,
    subject: str,
    item: dict[str, Any],
    on: bool = True,
) -> dict[str, Any]:
    list_id = await list_id_of(client, issuer, subject)
    response = await client.put(
        f"/lists/{list_id}/items/{item['id']}/checked",
        json={"checked": on},
        headers=issuer.headers(subject) | idem(),
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def ingredient_id(client: httpx.AsyncClient, issuer: FakeIssuer, subject: str, q: str) -> str:
    response = await client.get("/ingredients", params={"q": q}, headers=issuer.headers(subject))
    assert response.status_code == 200, response.text
    found: str = response.json()[0]["id"]
    return found


# --- Defaults ------------------------------------------------------------------------


async def test_a_new_household_starts_with_default_staples_and_nothing_tracked(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")

    cab = await cabinet(client, fake_issuer, "alice")

    assert cab["tracked"] == []
    assert staples(cab)["salt"] is True
    assert staples(cab)["olive oil"] is True
    assert "pasta" not in staples(cab)


# --- Adding items: reading amounts and linking Ingredients ---------------------------


async def test_adding_reads_the_amount_and_links_the_ingredient(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")

    item = await add(client, fake_issuer, "alice", "500g pasta")

    assert (item["text"], item["quantity"], item["unit"]) == ("Pasta", "500", "g")
    assert item["ingredient"]["name"] == "pasta"


@pytest.mark.parametrize(
    ("typed", "ingredient"),
    [
        ("Chicken thighs", "chicken thigh"),  # plural of the name
        ("all-purpose flour", "plain flour"),  # US alias
        ("Cilantro", "coriander"),
        ("lemon", "lemons"),  # singular of the name
        ("2 kg Beef Mince", "beef mince"),
    ],
)
async def test_common_names_link_to_the_right_ingredient(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, typed: str, ingredient: str
) -> None:
    await create_household(client, fake_issuer, "alice")

    item = await add(client, fake_issuer, "alice", typed)

    assert item["ingredient"]["name"] == ingredient


async def test_things_that_are_not_ingredients_stay_unlinked(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")

    item = await add(client, fake_issuer, "alice", "Birthday candles")
    await tick(client, fake_issuer, "alice", item)

    assert item["ingredient"] is None
    assert (await cabinet(client, fake_issuer, "alice"))["tracked"] == []


async def test_a_member_can_fix_or_remove_the_link(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    item = await add(client, fake_issuer, "alice", "Mince")  # beef, by default
    pork = await ingredient_id(client, fake_issuer, "alice", "pork mince")
    url = f"/lists/{await list_id_of(client, fake_issuer, 'alice')}/items/{item['id']}"

    relinked = await client.patch(
        url, json={"ingredient_id": pork}, headers=fake_issuer.headers("alice") | idem()
    )
    unlinked = await client.patch(
        url, json={"ingredient_id": None}, headers=fake_issuer.headers("alice") | idem()
    )

    assert relinked.json()["ingredient"]["name"] == "pork mince"
    assert unlinked.json()["ingredient"] is None


# --- Ticking off → Cabinet -----------------------------------------------------------


async def test_ticking_puts_the_amount_in_the_cabinet_as_confirmed(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    await join(client, fake_issuer, "bob", await invite(client, fake_issuer, "alice"))
    item = await add(client, fake_issuer, "alice", "1.5kg chicken thighs")

    await tick(client, fake_issuer, "bob", item)

    # Stored in the Ingredient's own unit (grams), and visible to the whole Household.
    assert tracked(await cabinet(client, fake_issuer, "alice")) == {
        "chicken thigh": ("1500", "g", "confirmed")
    }


async def test_buying_more_adds_to_what_is_there(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    await tick(client, fake_issuer, "alice", await add(client, fake_issuer, "alice", "2L milk"))
    await tick(client, fake_issuer, "alice", await add(client, fake_issuer, "alice", "500ml milk"))

    assert tracked(await cabinet(client, fake_issuer, "alice"))["milk"] == (
        "2500",
        "ml",
        "confirmed",
    )


async def test_an_amount_that_cannot_be_converted_is_recorded_as_some(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    # Chicken is tracked in grams; "2 chicken breasts" is a count. Don't guess a weight.
    await tick(
        client, fake_issuer, "alice", await add(client, fake_issuer, "alice", "2 chicken breasts")
    )

    assert tracked(await cabinet(client, fake_issuer, "alice"))["chicken breast"] == (
        None,
        "g",
        "confirmed",
    )


async def test_unticking_takes_it_back_out(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    first = await add(client, fake_issuer, "alice", "1kg rice")
    second = await add(client, fake_issuer, "alice", "500g rice")
    await tick(client, fake_issuer, "alice", first)
    await tick(client, fake_issuer, "alice", second)

    await tick(client, fake_issuer, "alice", second, on=False)
    after_one = tracked(await cabinet(client, fake_issuer, "alice"))
    await tick(client, fake_issuer, "alice", first, on=False)
    after_both = tracked(await cabinet(client, fake_issuer, "alice"))

    assert after_one["rice"][0] == "1000"
    assert "rice" not in after_both  # back to nothing, not "0 g"


async def test_ticking_twice_only_adds_once(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    await join(client, fake_issuer, "bob", await invite(client, fake_issuer, "alice"))
    item = await add(client, fake_issuer, "alice", "1kg rice")

    await tick(client, fake_issuer, "alice", item)
    await tick(client, fake_issuer, "bob", item)  # Bob ticks it too, on his phone

    assert tracked(await cabinet(client, fake_issuer, "alice"))["rice"][0] == "1000"


async def test_buying_something_unknown_replaces_the_guess(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    await create_household(client, fake_issuer, "alice")
    await tick(client, fake_issuer, "alice", await add(client, fake_issuer, "alice", "1kg rice"))
    with db.begin() as conn:  # a month passes with nobody checking the rice
        conn.execute(
            text("UPDATE cabinet_items SET last_confirmed_at = now() - interval '30 days'")
        )
    assert tracked(await cabinet(client, fake_issuer, "alice"))["rice"][2] == "unknown"

    await tick(client, fake_issuer, "alice", await add(client, fake_issuer, "alice", "500g rice"))

    # We don't trust the old 1 kg, but we do know about the 500 g just bought.
    assert tracked(await cabinet(client, fake_issuer, "alice"))["rice"] == ("500", "g", "confirmed")


async def test_buying_a_staple_marks_it_as_in_stock(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    salt = await ingredient_id(client, fake_issuer, "alice", "salt")
    await client.put(
        f"/cabinet/staples/{salt}",
        json={"have": False},
        headers=fake_issuer.headers("alice") | idem(),
    )
    ran_out = staples(await cabinet(client, fake_issuer, "alice"))["salt"]

    await tick(client, fake_issuer, "alice", await add(client, fake_issuer, "alice", "Salt"))

    assert ran_out is False
    assert staples(await cabinet(client, fake_issuer, "alice"))["salt"] is True
    assert "salt" not in tracked(await cabinet(client, fake_issuer, "alice"))


# --- Manual edits --------------------------------------------------------------------


async def test_members_can_set_and_remove_tracked_amounts(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    pasta = await ingredient_id(client, fake_issuer, "alice", "pasta")
    url = f"/cabinet/items/{pasta}"
    alice = fake_issuer.headers("alice")

    set_amount = await client.put(url, json={"quantity": "750"}, headers=alice | idem())
    some = await client.put(url, json={"quantity": None}, headers=alice | idem())
    removed = await client.delete(url, headers=alice | idem())
    removed_again = await client.delete(url, headers=alice | idem())

    assert (set_amount.json()["quantity"], set_amount.json()["status"]) == ("750", "confirmed")
    assert set_amount.json()["last_change_source"] == "manual"
    assert some.json()["quantity"] is None
    assert (removed.status_code, removed_again.status_code) == (204, 204)
    assert (await cabinet(client, fake_issuer, "alice"))["tracked"] == []


async def test_a_staple_has_no_quantity(client: httpx.AsyncClient, fake_issuer: FakeIssuer) -> None:
    await create_household(client, fake_issuer, "alice")
    salt = await ingredient_id(client, fake_issuer, "alice", "salt")

    response = await client.put(
        f"/cabinet/items/{salt}",
        json={"quantity": "100"},
        headers=fake_issuer.headers("alice") | idem(),
    )

    assert response.status_code == 409


async def test_members_choose_which_ingredients_are_staples(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    alice = fake_issuer.headers("alice")
    rice = await ingredient_id(client, fake_issuer, "alice", "rice")
    salt = await ingredient_id(client, fake_issuer, "alice", "salt")
    await client.put(f"/cabinet/items/{rice}", json={"quantity": "1000"}, headers=alice | idem())

    made_staple = await client.put(
        f"/cabinet/staples/{rice}", json={"have": True}, headers=alice | idem()
    )
    no_longer = await client.delete(f"/cabinet/staples/{salt}", headers=alice | idem())
    cab = await cabinet(client, fake_issuer, "alice")

    assert made_staple.status_code == 200
    assert no_longer.status_code == 204
    assert staples(cab)["rice"] is True
    assert "rice" not in tracked(cab)  # a Staple carries no quantity
    assert "salt" not in staples(cab)


async def test_unknown_ingredients_are_not_found(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")

    response = await client.put(
        "/cabinet/items/00000000-0000-0000-0000-000000000000",
        json={"quantity": "1"},
        headers=fake_issuer.headers("alice") | idem(),
    )

    assert response.status_code == 404


# --- Search and isolation ------------------------------------------------------------


@pytest.mark.parametrize(
    ("query", "expected_first"), [("flour", "plain flour"), ("cilantro", "coriander")]
)
async def test_ingredient_search_finds_names_and_aliases(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, query: str, expected_first: str
) -> None:
    await create_household(client, fake_issuer, "alice")

    response = await client.get(
        "/ingredients", params={"q": query}, headers=fake_issuer.headers("alice")
    )

    assert response.json()[0]["name"] == expected_first


async def test_each_household_has_its_own_cabinet(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    await create_household(client, fake_issuer, "mallory")
    salt = await ingredient_id(client, fake_issuer, "mallory", "salt")
    await tick(client, fake_issuer, "alice", await add(client, fake_issuer, "alice", "1kg rice"))

    await client.put(
        f"/cabinet/staples/{salt}",
        json={"have": False},
        headers=fake_issuer.headers("mallory") | idem(),
    )

    assert tracked(await cabinet(client, fake_issuer, "mallory")) == {}
    assert staples(await cabinet(client, fake_issuer, "alice"))["salt"] is True


async def test_relinking_a_ticked_item_moves_its_stock(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    item = await add(client, fake_issuer, "alice", "500g mince")  # beef, by default
    await tick(client, fake_issuer, "alice", item)
    pork = await ingredient_id(client, fake_issuer, "alice", "pork mince")

    await client.patch(
        f"/lists/{await list_id_of(client, fake_issuer, 'alice')}/items/{item['id']}",
        json={"ingredient_id": pork},
        headers=fake_issuer.headers("alice") | idem(),
    )

    assert tracked(await cabinet(client, fake_issuer, "alice")) == {
        "pork mince": ("500", "g", "confirmed")
    }
