"""Food groups for the Shopping List and Kitchen (ADR 0030): plain meats are starters, and a
new Household Ingredient starts in the group its words name instead of Other."""

import httpx
import pytest
from sqlalchemy import Engine, text

from app.data.food_groups import guess_category
from app.seed import regroup_household_ingredients
from tests.conftest import FakeIssuer
from tests.helpers import create_household
from tests.test_household_ingredients import add

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    ("name", "category"),
    [
        ("wagyu beef", "meat"),
        ("free range chicken", "meat"),
        ("lamb ribs", "meat"),
        ("atlantic salmon", "seafood"),
        ("king prawns", "seafood"),
        ("goat cheese", "dairy"),
        ("oat milk", "dairy"),
        ("dutch carrots", "produce"),
        ("sourdough loaf", "bakery"),
        ("apple juice", "drinks"),
        ("chicken stock cubes", "pantry"),  # the last word names the thing: stock, not chicken
        ("frozen peas", "frozen"),
        ("ice cream", "frozen"),
        ("smoked paprika", "spices"),
        ("birthday candles", "other"),
        ("hamburger buns", "bakery"),
        ("hamburg", "other"),  # whole words only
    ],
)
def test_a_new_foods_words_name_its_group(name: str, category: str) -> None:
    assert guess_category(name) == category


@pytest.mark.parametrize(
    ("typed", "starter"),
    [
        ("Chicken", "chicken"),
        ("Beef", "beef"),
        ("Lamb", "lamb"),
        ("Pork", "pork"),
        ("Mince beef", "beef mince"),
        ("Mince lamb", "lamb mince"),
        ("Mince pork", "pork mince"),
    ],
)
async def test_plain_meats_are_starters_in_meat(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, typed: str, starter: str
) -> None:
    await create_household(client, fake_issuer, "ana")
    ingredient = (await add(client, fake_issuer, "ana", typed))["ingredient"]
    assert (ingredient["name"], ingredient["category"]) == (starter, "meat")
    assert ingredient["is_household_ingredient"] is False


async def test_a_new_food_starts_in_the_group_its_words_name(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    ingredient = (await add(client, fake_issuer, "ana", "Wagyu beef"))["ingredient"]
    assert (ingredient["name"], ingredient["category"]) == ("wagyu beef", "meat")
    assert ingredient["is_household_ingredient"] is True


async def test_existing_foods_in_other_are_regrouped_once(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    home = await create_household(client, fake_issuer, "ana")
    with db.begin() as conn:
        for name in ("wagyu beef", "bin bags"):
            conn.execute(
                text(
                    "INSERT INTO ingredients (id, household_id, name, category, default_unit,"
                    " is_default_staple) VALUES (gen_random_uuid(), :h, :n, 'other', 'count',"
                    " false)"
                ),
                {"h": home["household"]["id"], "n": name},
            )
        regroup_household_ingredients(conn)
        groups: dict[str, str] = dict(
            conn.execute(
                text("SELECT name, category FROM ingredients WHERE household_id = :h"),
                {"h": home["household"]["id"]},
            ).all()
        )
    assert groups == {"wagyu beef": "meat", "bin bags": "other"}
