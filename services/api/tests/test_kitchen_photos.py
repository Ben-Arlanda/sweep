"""Kitchen Photos, applying the approved rows (slice 3e step 1, ADR 0023).

A photo of items laid out shows what the Household has, so its amount replaces what's
stored (never adds), it never removes anything, and new items go to the photo's Place.
"""

import uuid
from collections.abc import Awaitable, Callable, Sequence
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import Engine, text

from app import errors
from app.data.places import Place
from app.db import make_engine, make_sessionmaker
from app.models import ChangeSource, KitchenItem, utcnow
from app.services import kitchen as kitchen_service
from app.services.kitchen import PhotoItem, Status, status_of
from tests.conftest import FakeIssuer
from tests.helpers import create_household, idem
from tests.test_kitchen import ingredient_id, kitchen, staples, tracked
from tests.test_places import places

pytestmark = pytest.mark.anyio

Apply = Callable[[str, Place, Sequence[tuple[str, str | None]]], Awaitable[None]]


@pytest.fixture
def apply(database_url: str, db: Engine) -> Apply:
    """Apply approved rows the way the apply route will: (ingredient id, amount)."""

    async def run(household_id: str, place: Place, rows: Sequence[tuple[str, str | None]]) -> None:
        engine = make_engine(database_url)
        try:
            async with make_sessionmaker(engine)() as session:
                await kitchen_service.apply_photo(
                    session,
                    uuid.UUID(household_id),
                    place,
                    [
                        PhotoItem(uuid.UUID(iid), Decimal(q) if q is not None else None)
                        for iid, q in rows
                    ],
                )
                await session.commit()
        finally:
            await engine.dispose()

    return run


async def home(client: httpx.AsyncClient, issuer: FakeIssuer, who: str = "alice") -> str:
    made = await create_household(client, issuer, who, name=f"{who}'s")
    household_id: str = made["household"]["id"]
    return household_id


async def set_amount(
    client: httpx.AsyncClient, issuer: FakeIssuer, iid: str, quantity: str | None
) -> None:
    response = await client.put(
        f"/kitchen/items/{iid}",
        json={"quantity": quantity},
        headers=issuer.headers("alice") | idem(),
    )
    assert response.status_code == 200, response.text


def age(db: Engine, iid: str, days: int, source: str = "manual") -> None:
    with db.begin() as conn:
        conn.execute(
            text(
                "UPDATE kitchen_items SET last_confirmed_at = now() - make_interval(days => :d),"
                " last_change_source = :s WHERE ingredient_id = :i"
            ),
            {"d": days, "s": source, "i": iid},
        )


def test_a_photo_counts_as_confirmed() -> None:
    now = utcnow()
    item = KitchenItem(last_change_source=ChangeSource.PHOTO, last_confirmed_at=now)

    assert status_of(item, now) == Status.CONFIRMED
    assert status_of(item, now + timedelta(days=8)) == Status.ESTIMATED


async def test_new_items_are_added_confirmed_with_their_amount(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, apply: Apply
) -> None:
    household = await home(client, fake_issuer)
    eggs = await ingredient_id(client, fake_issuer, "alice", "eggs")
    chicken = await ingredient_id(client, fake_issuer, "alice", "chicken thigh")

    await apply(household, Place.FRIDGE, [(eggs, "6"), (chicken, None)])

    got = tracked(await kitchen(client, fake_issuer, "alice"))
    assert got["eggs"] == ("6", "count", "confirmed")
    assert got["chicken thigh"] == (None, "g", "confirmed")  # "have some"


async def test_new_items_go_to_the_photos_place(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, apply: Apply
) -> None:
    household = await home(client, fake_issuer)
    chicken = await ingredient_id(client, fake_issuer, "alice", "chicken thigh")
    peas = await ingredient_id(client, fake_issuer, "alice", "frozen peas")

    await apply(household, Place.FREEZER, [(chicken, None), (peas, None)])

    got = places(await kitchen(client, fake_issuer, "alice"))
    assert got["chicken thigh"] == "freezer"  # moved from its default, the Fridge
    assert got["frozen peas"] == "freezer"


async def test_a_photo_amount_replaces_never_adds(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, apply: Apply
) -> None:
    household = await home(client, fake_issuer)
    eggs = await ingredient_id(client, fake_issuer, "alice", "eggs")
    await set_amount(client, fake_issuer, eggs, "4")

    await apply(household, Place.FRIDGE, [(eggs, "6")])

    assert tracked(await kitchen(client, fake_issuer, "alice"))["eggs"][0] == "6"


async def test_no_amount_keeps_a_trusted_amount_and_reconfirms_it(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, apply: Apply, db: Engine
) -> None:
    household = await home(client, fake_issuer)
    chicken = await ingredient_id(client, fake_issuer, "alice", "chicken thigh")
    await set_amount(client, fake_issuer, chicken, "500")
    age(db, chicken, days=2, source="cooked")  # Estimated after a Cooked meal

    await apply(household, Place.FRIDGE, [(chicken, None)])

    assert tracked(await kitchen(client, fake_issuer, "alice"))["chicken thigh"] == (
        "500",
        "g",
        "confirmed",
    )


async def test_no_amount_turns_an_unknown_amount_into_have_some(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, apply: Apply, db: Engine
) -> None:
    household = await home(client, fake_issuer)
    chicken = await ingredient_id(client, fake_issuer, "alice", "chicken thigh")
    await set_amount(client, fake_issuer, chicken, "500")
    age(db, chicken, days=20)  # Unknown: the 500 g isn't trusted any more

    await apply(household, Place.FRIDGE, [(chicken, None)])

    assert tracked(await kitchen(client, fake_issuer, "alice"))["chicken thigh"] == (
        None,
        "g",
        "confirmed",
    )


async def test_existing_items_keep_their_place(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, apply: Apply
) -> None:
    household = await home(client, fake_issuer)
    chicken = await ingredient_id(client, fake_issuer, "alice", "chicken thigh")
    await set_amount(client, fake_issuer, chicken, "500")

    await apply(household, Place.FREEZER, [(chicken, None)])

    assert places(await kitchen(client, fake_issuer, "alice"))["chicken thigh"] == "fridge"


async def test_a_staple_in_the_photo_is_marked_have(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, apply: Apply
) -> None:
    household = await home(client, fake_issuer)
    salt = await ingredient_id(client, fake_issuer, "alice", "salt")
    response = await client.put(
        f"/kitchen/staples/{salt}",
        json={"have": False},
        headers=fake_issuer.headers("alice") | idem(),
    )
    assert response.status_code == 200, response.text

    await apply(household, Place.CUPBOARD, [(salt, "3")])  # a Staple has no amount

    view = await kitchen(client, fake_issuer, "alice")
    assert staples(view)["salt"] is True
    assert "salt" not in tracked(view)


async def test_nothing_missing_from_the_photo_is_removed(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, apply: Apply
) -> None:
    household = await home(client, fake_issuer)
    eggs = await ingredient_id(client, fake_issuer, "alice", "eggs")
    milk = await ingredient_id(client, fake_issuer, "alice", "milk")
    await set_amount(client, fake_issuer, milk, "1000")

    await apply(household, Place.FRIDGE, [(eggs, "6")])

    assert tracked(await kitchen(client, fake_issuer, "alice"))["milk"][0] == "1000"


async def test_one_photo_bumps_the_kitchen_version_once(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, apply: Apply
) -> None:
    household = await home(client, fake_issuer)
    eggs = await ingredient_id(client, fake_issuer, "alice", "eggs")
    milk = await ingredient_id(client, fake_issuer, "alice", "milk")
    before = (await kitchen(client, fake_issuer, "alice"))["version"]

    await apply(household, Place.FRIDGE, [(eggs, "6"), (milk, None)])

    assert (await kitchen(client, fake_issuer, "alice"))["version"] == before + 1


async def test_the_same_ingredient_twice_is_refused(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, apply: Apply
) -> None:
    household = await home(client, fake_issuer)
    eggs = await ingredient_id(client, fake_issuer, "alice", "eggs")

    with pytest.raises(errors.InvalidInput):
        await apply(household, Place.FRIDGE, [(eggs, "6"), (eggs, "12")])


async def test_a_negative_amount_is_refused(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, apply: Apply
) -> None:
    household = await home(client, fake_issuer)
    eggs = await ingredient_id(client, fake_issuer, "alice", "eggs")

    with pytest.raises(errors.InvalidInput):
        await apply(household, Place.FRIDGE, [(eggs, "-1")])


async def test_another_households_ingredient_is_not_found(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, apply: Apply
) -> None:
    household = await home(client, fake_issuer)
    await home(client, fake_issuer, "ben")
    response = await client.post(
        "/ingredients", json={"name": "finger lime"}, headers=fake_issuer.headers("ben") | idem()
    )
    assert response.status_code == 200, response.text
    theirs: str = response.json()["id"]

    with pytest.raises(errors.NotFound):
        await apply(household, Place.FRIDGE, [(theirs, None)])
