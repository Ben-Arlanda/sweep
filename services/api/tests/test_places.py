"""Places in the Kitchen: Fridge, Freezer or Cupboard (ADR 0011)."""

from typing import Any

import httpx
import pytest

from app.data.ingredients import INGREDIENTS
from app.data.places import Place, default_place
from tests.conftest import FakeIssuer
from tests.helpers import create_household, idem
from tests.test_kitchen import ingredient_id, kitchen

pytestmark = pytest.mark.anyio


# --- Default Place (pure) ------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "category", "expected"),
    [
        ("chicken thigh", "meat", Place.FRIDGE),
        ("milk", "dairy", Place.FRIDGE),
        ("salmon", "seafood", Place.FRIDGE),
        ("kimchi", "chilled", Place.FRIDGE),
        ("frozen peas", "frozen", Place.FREEZER),
        ("rice", "pantry", Place.CUPBOARD),
        ("cumin", "spices", Place.CUPBOARD),
        ("bread", "bakery", Place.CUPBOARD),
        ("lettuce", "produce", Place.FRIDGE),
        ("onion", "produce", Place.CUPBOARD),  # kept out of the fridge
        ("bananas", "produce", Place.CUPBOARD),
    ],
)
def test_default_place_comes_from_the_category(name: str, category: str, expected: Place) -> None:
    assert default_place(name, category) == expected


def test_every_starter_ingredient_has_a_place() -> None:
    # A new category added without a Place would otherwise vanish from every filter.
    for seed in INGREDIENTS:
        assert default_place(seed.name, seed.category) in Place, seed.name


# --- Through the API -----------------------------------------------------------------


def places(view: dict[str, Any]) -> dict[str, str]:
    rows = view["tracked"] + view["staples"]
    return {r["ingredient"]["name"]: r["place"] for r in rows}


async def track(client: httpx.AsyncClient, issuer: FakeIssuer, name: str) -> str:
    iid = await ingredient_id(client, issuer, "alice", name)
    response = await client.put(
        f"/kitchen/items/{iid}", json={"quantity": "1"}, headers=issuer.headers("alice") | idem()
    )
    assert response.status_code == 200, response.text
    return iid


async def move(
    client: httpx.AsyncClient, issuer: FakeIssuer, iid: str, place: str | None
) -> httpx.Response:
    return await client.put(
        f"/kitchen/places/{iid}", json={"place": place}, headers=issuer.headers("alice") | idem()
    )


async def test_items_show_their_default_place(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    await track(client, fake_issuer, "frozen peas")
    await track(client, fake_issuer, "chicken thigh")

    got = places(await kitchen(client, fake_issuer, "alice"))

    assert got["frozen peas"] == "freezer"
    assert got["chicken thigh"] == "fridge"
    assert got["salt"] == "cupboard"  # a default Staple


async def test_a_member_can_move_an_item_and_put_it_back(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    chicken = await track(client, fake_issuer, "chicken thigh")
    before = (await kitchen(client, fake_issuer, "alice"))["version"]

    moved = await move(client, fake_issuer, chicken, "freezer")
    after_move = await kitchen(client, fake_issuer, "alice")
    reset = await move(client, fake_issuer, chicken, None)

    assert moved.status_code == 200, moved.text
    assert moved.json() == {"place": "freezer"}
    assert places(after_move)["chicken thigh"] == "freezer"
    assert after_move["version"] > before  # other devices refetch
    assert reset.json() == {"place": "fridge"}  # back to the default


async def test_staples_can_be_moved_too(client: httpx.AsyncClient, fake_issuer: FakeIssuer) -> None:
    await create_household(client, fake_issuer, "alice")
    salt = await ingredient_id(client, fake_issuer, "alice", "salt")

    await move(client, fake_issuer, salt, "fridge")

    assert places(await kitchen(client, fake_issuer, "alice"))["salt"] == "fridge"


async def test_moving_needs_the_item_in_your_kitchen_and_a_real_place(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "alice")
    chicken = await ingredient_id(client, fake_issuer, "alice", "chicken thigh")
    await create_household(client, fake_issuer, "mallory")
    tracked_by_alice = await track(client, fake_issuer, "frozen peas")

    not_in_kitchen = await move(client, fake_issuer, chicken, "fridge")
    bad_place = await move(client, fake_issuer, tracked_by_alice, "garage")
    other_household = await client.put(
        f"/kitchen/places/{tracked_by_alice}",
        json={"place": "fridge"},
        headers=fake_issuer.headers("mallory") | idem(),
    )

    assert not_in_kitchen.status_code == 404
    assert bad_place.status_code == 422
    assert other_household.status_code == 404
    assert places(await kitchen(client, fake_issuer, "alice"))["frozen peas"] == "freezer"
