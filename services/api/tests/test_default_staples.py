"""Default Staples are everyday long-life basics, and existing Households get new ones once."""

import httpx
import pytest
from sqlalchemy import Engine, text

from app.data.ingredients import INGREDIENTS
from app.seed import add_default_staples
from tests.conftest import FakeIssuer
from tests.helpers import create_household
from tests.test_kitchen import ingredient_id, kitchen, staples
from tests.test_stock import set_amount

pytestmark = pytest.mark.anyio

EVERYDAY = {"milk", "butter", "bread", "eggs", "coffee", "tomato sauce", "mayonnaise", "honey"}


def test_defaults_are_everyday_basics_not_meal_deciders() -> None:
    defaults = {i.name for i in INGREDIENTS if i.is_default_staple}
    assert EVERYDAY <= defaults
    # Rarely used, so not assumed.
    assert defaults.isdisjoint({"celery salt", "dried sage", "cayenne pepper", "ground cumin"})
    # Tracked: their amount decides whether a meal is possible.
    assert defaults.isdisjoint({"pasta", "rice", "canned tomatoes"})


async def test_a_new_household_starts_with_the_everyday_staples(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    have = staples(await kitchen(client, fake_issuer, "ana"))
    assert all(have[name] for name in EVERYDAY)
    assert "celery salt" not in have


async def test_existing_households_gain_new_defaults_but_keep_their_choices(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    home = await create_household(client, fake_issuer, "ana")
    hid = home["household"]["id"]
    names = ("butter", "coffee", "bread", "celery salt")
    ids = {n: await ingredient_id(client, fake_issuer, "ana", n) for n in names}
    with db.begin() as conn:
        # Like a Household made before this change: none of the new defaults yet...
        conn.execute(
            text(
                "DELETE FROM household_staples WHERE household_id = :h"
                " AND ingredient_id IN (:b, :c, :br)"
            ),
            {"h": hid, "b": ids["butter"], "c": ids["coffee"], "br": ids["bread"]},
        )
        # ...still has an old default, and never eats bread.
        conn.execute(
            text("INSERT INTO household_staples (household_id, ingredient_id) VALUES (:h, :i)"),
            {"h": hid, "i": ids["celery salt"]},
        )
        conn.execute(
            text(
                "INSERT INTO household_excluded_ingredients (household_id, ingredient_id)"
                " VALUES (:h, :i)"
            ),
            {"h": hid, "i": ids["bread"]},
        )
    await set_amount(client, fake_issuer, ids["coffee"], "200")  # it counts its coffee

    with db.begin() as conn:
        assert add_default_staples(conn, ["butter", "coffee", "bread"]) == 1
        assert add_default_staples(conn, ["butter", "coffee", "bread"]) == 0  # once only

    cab = await kitchen(client, fake_issuer, "ana")
    have = staples(cab)
    assert have["butter"] is True
    assert have["celery salt"] is True
    assert "coffee" not in have and "bread" not in have
    assert [t["ingredient"]["name"] for t in cab["tracked"]] == ["coffee"]
