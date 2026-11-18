"""Favourites (slice 6e, ADR 0025): a recipe the Household has hearted, Seed or Imported.
One heart per Household; any Member can heart or un-heart it; imports start hearted."""

from datetime import date, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text

from app.services.kitchen_match import Match, rank_key
from tests.conftest import ClientFor, FakeIssuer, Loader
from tests.fake_model import ScriptedModel, last_result, tool
from tests.fake_model import text as say_text
from tests.helpers import create_household, invite, join
from tests.test_agent import say
from tests.test_imported_recipes import nonna, save
from tests.test_recipes import CURRY, PASTA, get, seed

pytestmark = pytest.mark.anyio


async def heart(
    client: httpx.AsyncClient, issuer: FakeIssuer, recipe_id: str, who: str = "ana"
) -> httpx.Response:
    return await client.put(f"/recipes/{recipe_id}/favourite", headers=issuer.headers(who))


async def unheart(
    client: httpx.AsyncClient, issuer: FakeIssuer, recipe_id: str, who: str = "ana"
) -> httpx.Response:
    return await client.delete(f"/recipes/{recipe_id}/favourite", headers=issuer.headers(who))


async def by_title(client: httpx.AsyncClient, issuer: FakeIssuer) -> dict[str, dict[str, Any]]:
    return {r["title"]: r for r in (await get(client, issuer, "/recipes")).json()}


async def test_hearting_a_seed_recipe_makes_it_a_favourite_for_the_household(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([CURRY, PASTA])
    await create_household(client, fake_issuer, "ana")
    await join(client, fake_issuer, "ben", await invite(client, fake_issuer, "ana"))
    pasta = (await by_title(client, fake_issuer))["Quick tomato pasta"]["id"]

    assert (await heart(client, fake_issuer, pasta, who="ben")).status_code == 204
    assert (await heart(client, fake_issuer, pasta)).status_code == 204  # twice is fine

    listed = await by_title(client, fake_issuer)
    assert listed["Quick tomato pasta"]["favourite"] is True
    assert listed["Chicken and chickpea curry"]["favourite"] is False
    one = (await get(client, fake_issuer, f"/recipes/{pasta}")).json()
    assert one["favourite"] is True
    only = (await get(client, fake_issuer, "/recipes", favourites="true")).json()
    assert [r["title"] for r in only] == ["Quick tomato pasta"]


async def test_any_member_can_unheart_and_the_recipe_stays(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([PASTA])
    await create_household(client, fake_issuer, "ana")
    await join(client, fake_issuer, "ben", await invite(client, fake_issuer, "ana"))
    pasta = (await by_title(client, fake_issuer))["Quick tomato pasta"]["id"]
    await heart(client, fake_issuer, pasta)

    assert (await unheart(client, fake_issuer, pasta, who="ben")).status_code == 204
    assert (await unheart(client, fake_issuer, pasta)).status_code == 204  # already gone
    assert (await by_title(client, fake_issuer))["Quick tomato pasta"]["favourite"] is False


async def test_hearts_belong_to_one_household(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([PASTA])
    await create_household(client, fake_issuer, "ana")
    await create_household(client, fake_issuer, "zoe")
    pasta = (await by_title(client, fake_issuer))["Quick tomato pasta"]["id"]
    await heart(client, fake_issuer, pasta)

    zoes = (await client.get("/recipes", headers=fake_issuer.headers("zoe"))).json()
    assert zoes[0]["favourite"] is False


async def test_another_households_recipe_cant_be_hearted(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    await create_household(client, fake_issuer, "zoe")
    lasagne = (await save(client, fake_issuer, nonna())).json()["id"]

    assert (await heart(client, fake_issuer, lasagne, who="zoe")).status_code == 404


async def test_an_imported_recipe_starts_hearted_and_survives_unhearting(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    await create_household(client, fake_issuer, "ana")
    saved = await save(client, fake_issuer, nonna())
    assert saved.json()["favourite"] is True
    lasagne = saved.json()["id"]
    imported = (await get(client, fake_issuer, "/recipes/imported")).json()
    assert imported[0]["favourite"] is True

    await unheart(client, fake_issuer, lasagne)
    after = await get(client, fake_issuer, f"/recipes/{lasagne}")
    assert after.status_code == 200
    assert after.json()["favourite"] is False


async def test_who_hearted_it_is_recorded(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([PASTA])
    await create_household(client, fake_issuer, "ana")
    pasta = (await by_title(client, fake_issuer))["Quick tomato pasta"]["id"]
    await heart(client, fake_issuer, pasta)

    with db.connect() as conn:
        who = conn.execute(
            text(
                "SELECT m.display_name FROM favourites f JOIN members m ON m.id = f.hearted_by"
                " WHERE f.recipe_id = :r"
            ),
            {"r": pasta},
        ).scalar_one()
    assert who == "ana"


# --- Ranking: Favourites win ties (ADR 0025) -------------------------------------------

ALPHA = seed("alpha-stew", "Alpha stew", 30, "british", ["500 g beef mince", "1 onion, diced"])
ZETA = seed("zeta-stew", "Zeta stew", 30, "british", ["500 g beef mince", "1 onion, diced"])
CHEAP = seed("cheap-pasta", "Cheap pasta", 20, "italian", ["400 g pasta"])


def test_a_favourite_wins_a_tie_but_never_beats_fewer_things_to_buy() -> None:
    one_missing = Match(have=(), maybe=(), missing=("onion",), tracked_used=0)
    two_missing = Match(have=(), maybe=(), missing=("onion", "beef"), tracked_used=0)

    assert rank_key("Zeta", one_missing, True) < rank_key("Alpha", one_missing)
    assert rank_key("Zeta", two_missing, True) > rank_key("Alpha", one_missing)


async def recipe_id(db: Engine, slug: str) -> str:
    with db.connect() as conn:
        return str(
            conn.execute(text("SELECT id FROM recipes WHERE slug = :s"), {"s": slug}).one()[0]
        )


async def ranked(
    client_for: ClientFor,
    issuer: FakeIssuer,
    hearted: list[str],
    args: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
    arrange: Any = None,
) -> list[dict[str, Any]]:
    """Heart some recipes, then have the scripted model call recipes_from_kitchen."""
    seen: list[Any] = []

    def capture(messages: Any) -> list[dict[str, Any]]:
        seen.append(last_result(messages))
        return [say_text("Done.")]

    model = ScriptedModel([[tool("recipes_from_kitchen", **(args or {}))], capture])
    async with client_for(model) as client:
        await create_household(client, issuer, "ana")
        for rid in hearted:
            assert (await heart(client, issuer, rid)).status_code == 204
        if arrange is not None:
            await arrange()
        response = await client.post("/conversations", json=plan, headers=issuer.headers("ana"))
        assert response.status_code == 201, response.text
        await say(client, issuer, response.json()["id"], "plan from my kitchen")
    found: list[dict[str, Any]] = seen[0]
    return found


async def test_the_agent_sees_favourites_first_among_equals(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([ALPHA, ZETA])
    found = await ranked(client_for, fake_issuer, [await recipe_id(db, "zeta-stew")])

    assert [r["title"] for r in found] == ["Zeta stew", "Alpha stew"]
    assert found[0]["favourite"] is True
    assert "favourite" not in found[1]


async def test_a_favourite_cooked_this_week_loses_its_tie_break(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([ALPHA, ZETA])
    zeta = await recipe_id(db, "zeta-stew")

    async def cooked_yesterday() -> None:
        with db.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO planned_meals (id, household_id, date, recipe_id, servings,"
                    " cooked_at) SELECT gen_random_uuid(), id, CURRENT_DATE - 1, :r, 4,"
                    " now() - interval '1 day' FROM households"
                ),
                {"r": zeta},
            )

    found = await ranked(client_for, fake_issuer, [zeta], arrange=cooked_yesterday)

    assert [r["title"] for r in found] == ["Alpha stew", "Zeta stew"]
    assert found[1]["favourite"] is True  # still a Favourite, just no boost


async def test_new_recipes_mode_gives_favourites_no_boost(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([ALPHA, ZETA])
    days = [(date.today() + timedelta(days=1)).isoformat()]
    found = await ranked(
        client_for,
        fake_issuer,
        [await recipe_id(db, "zeta-stew")],
        plan={"mode": "new", "days": days},
    )

    assert [r["title"] for r in found] == ["Alpha stew", "Zeta stew"]


async def test_the_agent_can_plan_from_favourites_only(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([ALPHA, ZETA, CHEAP])
    found = await ranked(
        client_for,
        fake_issuer,
        [await recipe_id(db, "zeta-stew")],
        args={"only_favourites": True},
    )

    assert [r["title"] for r in found] == ["Zeta stew"]
