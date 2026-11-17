"""Recipe Adaptations, the data (slice 5e step 1, ADR 0021).

An Adaptation is a recipes row of its own kind: a Household-only copy of its parent with
some lines swapped. There is no route that creates one: only an approved Proposal does
(step 3), so these tests make them through the service, as the commit will.
"""

import uuid
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from app import errors
from app.db import make_engine, make_sessionmaker
from app.services import adaptations
from tests.conftest import FakeIssuer, Loader
from tests.helpers import create_household, idem, invite, join
from tests.test_imported_recipes import nonna, save
from tests.test_recipes import PASTA, STIR_FRY

pytestmark = pytest.mark.anyio

Adapt = Callable[..., Awaitable[str]]


@pytest.fixture
def adapt(database_url: str, db: Engine) -> Adapt:
    """Make an Adaptation the way an approved Proposal will, and return its id."""

    async def run(
        household_id: str, parent_id: str, swaps: Sequence[tuple[int, str]], label: str
    ) -> str:
        engine = make_engine(database_url)
        try:
            async with make_sessionmaker(engine)() as session:
                made = await adaptations.create(
                    session,
                    uuid.UUID(household_id),
                    uuid.UUID(parent_id),
                    [adaptations.SwapIn(position, line) for position, line in swaps],
                    label,
                )
                await session.commit()
                return str(made.id)
        finally:
            await engine.dispose()

    return run


def seed_id(db: Engine, slug: str) -> str:
    with db.connect() as conn:
        found = conn.execute(text("SELECT id FROM recipes WHERE slug = :s"), {"s": slug})
        return str(found.scalar_one())


async def get(client: httpx.AsyncClient, issuer: FakeIssuer, path: str, who: str = "ana") -> Any:
    response = await client.get(path, headers=issuer.headers(who))
    assert response.status_code == 200, response.text
    return response.json()


async def test_an_adaptation_is_a_private_copy_with_its_swaps(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine, adapt: Adapt
) -> None:
    await load([STIR_FRY])
    home = await create_household(client, fake_issuer, "ana")
    parent = seed_id(db, "beef-stir-fry")
    made = await adapt(home["household"]["id"], parent, [(0, "400 g firm tofu")], "with tofu")

    recipe = await get(client, fake_issuer, f"/recipes/{made}")
    assert (recipe["kind"], recipe["parent_recipe_id"]) == ("adaptation", parent)
    assert recipe["title"] == "Beef and broccoli stir-fry · with tofu"
    lines = recipe["ingredients"]
    assert [line["raw_text"] for line in lines] == [
        "400 g firm tofu",
        "1 broccoli",
        "2 tbsp soy sauce",
        "1 cup rice",
    ]
    # The swapped line is read and linked like any other, and remembers what it replaced.
    assert (lines[0]["ingredient"]["name"], lines[0]["replaces"]) == ("tofu", "500 g beef steak")
    assert [line["replaces"] for line in lines[1:]] == [None, None, None]
    assert recipe["method"] == (await get(client, fake_issuer, f"/recipes/{parent}"))["method"]

    # Another Household can't see it: same 404 as an id that doesn't exist.
    await create_household(client, fake_issuer, "ben", name="Ben's")
    other = await client.get(f"/recipes/{made}", headers=fake_issuer.headers("ben"))
    assert other.status_code == 404


async def test_adaptations_list_under_their_parent_not_in_browse(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine, adapt: Adapt
) -> None:
    await load([STIR_FRY, PASTA])
    home = await create_household(client, fake_issuer, "ana")
    parent = seed_id(db, "beef-stir-fry")
    made = await adapt(home["household"]["id"], parent, [(0, "400 g firm tofu")], "with tofu")

    under = await get(client, fake_issuer, f"/recipes/{parent}/adaptations")
    assert [(a["id"], a["swaps"]) for a in under] == [
        (made, [{"replaces": "500 g beef steak", "raw_text": "400 g firm tofu"}])
    ]
    browse = await get(client, fake_issuer, "/recipes")
    assert sorted(r["kind"] for r in browse) == ["seed", "seed"]

    await create_household(client, fake_issuer, "ben", name="Ben's")
    assert await get(client, fake_issuer, f"/recipes/{parent}/adaptations", who="ben") == []


async def test_any_member_can_delete_one_and_only_their_households(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine, adapt: Adapt
) -> None:
    await load([STIR_FRY])
    home = await create_household(client, fake_issuer, "ana")
    await join(client, fake_issuer, "cal", await invite(client, fake_issuer, "ana"))
    await create_household(client, fake_issuer, "ben", name="Ben's")
    parent = seed_id(db, "beef-stir-fry")
    made = await adapt(home["household"]["id"], parent, [(0, "400 g firm tofu")], "with tofu")

    path = f"/recipes/adaptations/{made}"
    # Not another Household's, and not a Seed Recipe through this door.
    for who, target in [("ben", path), ("ana", f"/recipes/adaptations/{parent}")]:
        refused = await client.delete(target, headers=fake_issuer.headers(who) | idem())
        assert refused.status_code == 404, refused.text

    response = await client.delete(path, headers=fake_issuer.headers("cal") | idem())
    assert response.status_code == 204, response.text
    assert await get(client, fake_issuer, f"/recipes/{parent}/adaptations") == []
    assert (await get(client, fake_issuer, f"/recipes/{parent}"))["kind"] == "seed"


async def test_deleting_a_favourite_deletes_its_adaptations(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine, adapt: Adapt
) -> None:
    home = await create_household(client, fake_issuer, "ana")
    favourite = (await save(client, fake_issuer, nonna())).json()
    made = await adapt(
        home["household"]["id"], favourite["id"], [(0, "2 x 400g cans lentils")], "with lentils"
    )

    headers = fake_issuer.headers("ana")
    deleted = await client.delete(f"/recipes/imported/{favourite['id']}", headers=headers | idem())
    assert deleted.status_code == 204, deleted.text
    assert (await client.get(f"/recipes/{made}", headers=headers)).status_code == 404


async def test_only_a_visible_seed_or_imported_recipe_can_be_adapted(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine, adapt: Adapt
) -> None:
    await load([STIR_FRY])
    home = await create_household(client, fake_issuer, "ana")
    ben = await create_household(client, fake_issuer, "ben", name="Ben's")
    bens_favourite = (await save(client, fake_issuer, nonna(), who="ben")).json()
    made = await adapt(
        home["household"]["id"], seed_id(db, "beef-stir-fry"), [(0, "400 g firm tofu")], "with tofu"
    )

    for parent in [bens_favourite["id"], made, str(uuid.uuid4())]:  # not theirs; an Adaptation
        with pytest.raises(errors.NotFound):
            await adapt(home["household"]["id"], parent, [(0, "400 g firm tofu")], "with tofu")
    # A Swap must point at a line the parent has.
    with pytest.raises(errors.InvalidInput):
        await adapt(
            ben["household"]["id"], bens_favourite["id"], [(9, "400 g firm tofu")], "with tofu"
        )


async def test_the_database_keeps_kind_and_parent_in_step(db: Engine) -> None:
    """Belt and braces under the service: an Adaptation always has a parent, and nothing
    else does. Same idea as seed_has_no_household."""
    with db.connect() as conn, pytest.raises(IntegrityError):
        conn.execute(
            text(
                "INSERT INTO recipes (id, kind, household_id, title, summary, course,"
                " servings, licence, attribution) VALUES (gen_random_uuid(), 'seed', NULL,"
                " 'x', '', 'main', 2, 'x', 'x')"
                " RETURNING id"
            )
        ).scalar_one()
        conn.execute(text("UPDATE recipes SET parent_recipe_id = id WHERE kind = 'seed'"))
