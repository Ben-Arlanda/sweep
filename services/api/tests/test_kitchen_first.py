"""Kitchen-first planning (ADR 0013): the agent's `recipes_from_kitchen` tool ranks recipes
by what the Household has (fewest things to buy), with Dietary Rules applied in SQL and
Household Ingredients counted by name. The model is scripted; everything else is real.
"""

from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text

from app.agent.prompt import SYSTEM
from tests.conftest import ClientFor, FakeIssuer, Loader
from tests.fake_model import ScriptedModel, last_result, tool
from tests.fake_model import text as say_text
from tests.helpers import create_household, idem
from tests.test_agent import say, start
from tests.test_dietary_rules import SALAD
from tests.test_household_ingredients import add, tick
from tests.test_recipes import CURRY, PASTA, STIR_FRY, seed

pytestmark = pytest.mark.anyio

FINGER_LIME_CHICKEN = seed(
    "finger-lime-chicken",
    "Finger lime chicken",
    25,
    "australian",
    ["500 g chicken thigh", "2 finger limes", "1 onion, diced"],
)


async def ingredient_ids(db: Engine, slug: str) -> list[str]:
    """The Ingredient ids of a loaded recipe's linked lines, in order."""
    with db.connect() as conn:
        found = conn.execute(
            text(
                "SELECT ri.ingredient_id FROM recipe_ingredients ri JOIN recipes r"
                " ON r.id = ri.recipe_id WHERE r.slug = :s AND ri.ingredient_id IS NOT NULL"
                " ORDER BY ri.position"
            ),
            {"s": slug},
        )
        return [str(i) for i in found.scalars()]


async def stock(client: httpx.AsyncClient, issuer: FakeIssuer, ids: list[str]) -> None:
    for ingredient_id in ids:
        response = await client.put(
            f"/kitchen/items/{ingredient_id}",
            json={"quantity": None},
            headers=issuer.headers("ana") | idem(),
        )
        assert response.status_code == 200, response.text


async def run(
    client_for: ClientFor,
    issuer: FakeIssuer,
    name: str,
    args: dict[str, Any],
    arrange: Any = None,
) -> Any:
    """Have the scripted model call one tool, and return what the tool answered."""
    seen: list[Any] = []

    def capture(messages: Any) -> list[dict[str, Any]]:
        seen.append(last_result(messages))
        return [say_text("Done.")]

    model = ScriptedModel([[tool(name, **args)], capture])
    async with client_for(model) as client:
        await create_household(client, issuer, "ana")
        if arrange is not None:
            await arrange(client)
        cid = await start(client, issuer)
        await say(client, issuer, cid, "plan from my kitchen")
    return seen[0]


async def test_recipes_are_ranked_by_fewest_things_to_buy(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine, load: Loader
) -> None:
    await load([CURRY, PASTA, STIR_FRY, SALAD])
    chicken, chickpeas = (await ingredient_ids(db, "chicken-curry"))[:2]

    async def arrange(client: httpx.AsyncClient) -> None:
        await stock(client, fake_issuer, [chicken, chickpeas])

    found = await run(client_for, fake_issuer, "recipes_from_kitchen", {}, arrange)

    assert [r["title"] for r in found] == [
        "Chicken and chickpea curry",  # missing 1 (onion)
        "Chickpea salad",  # missing 2
        "Beef and broccoli stir-fry",  # missing 3 (soy sauce is a Staple)
        "Quick tomato pasta",  # missing 4
    ]
    curry = found[0]
    assert len(curry["missing"]) == 1
    assert "vegetable oil" in curry["have"]  # a default Staple
    assert set(curry) >= {"recipe_id", "title", "have", "maybe", "missing", "minutes"}


async def test_dietary_rules_still_apply(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine, load: Loader
) -> None:
    await load([CURRY, PASTA, STIR_FRY, SALAD])

    async def arrange(client: httpx.AsyncClient) -> None:
        response = await client.put(
            "/households/current/dietary-rules",
            json={"diets": ["vegetarian"], "excluded_ingredient_ids": []},
            headers=fake_issuer.headers("ana") | idem(),
        )
        assert response.status_code == 200, response.text

    found = await run(client_for, fake_issuer, "recipes_from_kitchen", {}, arrange)

    assert {r["title"] for r in found} == {"Quick tomato pasta", "Chickpea salad"}


async def test_already_planned_recipes_can_be_left_out(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine, load: Loader
) -> None:
    await load([CURRY, PASTA])
    with db.connect() as conn:
        curry = str(
            conn.execute(text("SELECT id FROM recipes WHERE slug = 'chicken-curry'")).scalar_one()
        )

    found = await run(
        client_for, fake_issuer, "recipes_from_kitchen", {"exclude_recipe_ids": [curry]}
    )

    assert [r["title"] for r in found] == ["Quick tomato pasta"]


async def test_a_taste_query_finds_candidates_then_the_kitchen_orders_them(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine, load: Loader
) -> None:
    await load([CURRY, PASTA, STIR_FRY, SALAD])
    beef, broccoli = (await ingredient_ids(db, "beef-stir-fry"))[:2]

    async def arrange(client: httpx.AsyncClient) -> None:
        await stock(client, fake_issuer, [beef, broccoli])

    found = await run(
        client_for, fake_issuer, "recipes_from_kitchen", {"query": "something quick"}, arrange
    )

    assert found[0]["title"] == "Beef and broccoli stir-fry"


async def test_a_household_ingredient_in_the_kitchen_counts(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([CURRY, FINGER_LIME_CHICKEN])

    async def arrange(client: httpx.AsyncClient) -> None:
        await tick(client, fake_issuer, "ana", await add(client, fake_issuer, "ana", "Finger lime"))

    found = await run(client_for, fake_issuer, "recipes_from_kitchen", {}, arrange)

    lime = next(r for r in found if r["title"] == "Finger lime chicken")
    assert "finger lime" in lime["have"]


async def test_must_use_finds_recipes_naming_a_household_ingredient(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([CURRY, FINGER_LIME_CHICKEN])

    async def arrange(client: httpx.AsyncClient) -> None:
        await add(client, fake_issuer, "ana", "Finger lime")  # now a Household Ingredient

    found = await run(
        client_for,
        fake_issuer,
        "search_recipes",
        {"query": "dinner", "must_use_ingredients": ["finger lime"]},
        arrange,
    )

    assert [r["title"] for r in found] == ["Finger lime chicken"]


def test_the_prompt_says_plans_start_from_the_kitchen() -> None:
    assert "recipes_from_kitchen" in SYSTEM
