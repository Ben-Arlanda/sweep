"""Slice 6d: a proposed list addition is the extra to buy, on top of what's already on
the Shopping List (ADR 0016).

- check_kitchen_coverage takes off what's on the list, so the agent proposes only the rest
- approving tops up a matching unticked item instead of skipping it, when the amounts
  can be combined honestly; otherwise it skips and says why
- the card says how much is already on the list
"""

from typing import Any

import httpx
import pytest
from sqlalchemy import Engine

from app.agent.prompt import SYSTEM
from tests.conftest import ClientFor, FakeIssuer, Loader
from tests.fake_model import ScriptedModel, last_result, tool
from tests.fake_model import text as say_text
from tests.helpers import create_household, idem
from tests.test_agent import MON, of, rid_in_db, say, start
from tests.test_approvals import decide, rows
from tests.test_recipes import CURRY

pytestmark = pytest.mark.anyio


async def on_list(client: httpx.AsyncClient, issuer: FakeIssuer, *texts: str) -> None:
    lst = (await client.get("/list", headers=issuer.headers("ana"))).json()
    for text in texts:
        response = await client.post(
            f"/lists/{lst['id']}/items", json={"text": text}, headers=issuer.headers("ana") | idem()
        )
        assert response.status_code == 201, response.text


def curry_plan(curry: str, *additions: dict[str, Any]) -> list[Any]:
    return [
        [
            tool("set_planned_meal", date=MON, recipe_id=curry, servings=4),
            tool("set_list_additions", items=list(additions)),
        ],
        [tool("propose_plan", summary="Curry.")],
    ]


async def propose_and_approve(
    client: httpx.AsyncClient, issuer: FakeIssuer
) -> tuple[dict[str, Any], dict[str, Any]]:
    cid = await start(client, issuer)
    # Coriander isn't in the curry: the Member asks for it, so it has a reason (slice 10).
    [event] = of(await say(client, issuer, cid, "plan the curry, plus coriander"), "proposal")
    proposal: dict[str, Any] = event["proposal"]
    response = await decide(client, issuer, proposal["id"], {"action": "approve"})
    assert response.status_code == 200, response.text
    outcome: dict[str, Any] = response.json()["outcome"]
    return proposal, outcome


def list_rows(db: Engine) -> list[tuple[str, str | None, str | None, str]]:
    found = rows(db, "SELECT text, quantity::text, unit, added_by FROM shopping_list_items")
    return sorted(
        (r.text, str(float(r.quantity)) if r.quantity else None, r.unit, r.added_by) for r in found
    )


# --- approving tops up -----------------------------------------------------------------


async def test_approving_tops_up_an_item_already_on_the_list(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY])
    curry = await rid_in_db(db, "chicken-curry")
    extra = {"name": "chicken thigh", "quantity": 300, "unit": "g"}
    async with client_for(ScriptedModel(curry_plan(curry, extra, {"name": "coriander"}))) as client:
        await create_household(client, fake_issuer, "ana")
        await on_list(client, fake_issuer, "200 g chicken thigh")
        proposal, outcome = await propose_and_approve(client, fake_issuer)

    # One line, 200 + 300, still the Member's item; the new one added as usual.
    assert list_rows(db) == [
        ("Chicken thigh", "500.0", "g", "member"),
        ("coriander", None, None, "agent"),
    ]
    assert outcome["topped_up"] == ["chicken thigh: 200 g → 500 g"]
    assert outcome["skipped"] == []
    assert outcome["message"] == (
        "Saved 1 meal, added 1 item to the list and topped up 1 already there."
    )
    # The card said so before approving.
    assert proposal["list_additions"][0]["on_list"] == "200 g"
    assert proposal["list_additions"][1]["on_list"] is None


async def test_topping_up_keeps_the_list_items_unit(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY])
    curry = await rid_in_db(db, "chicken-curry")
    extra = {"name": "chicken thigh", "quantity": 500, "unit": "g"}
    async with client_for(ScriptedModel(curry_plan(curry, extra))) as client:
        await create_household(client, fake_issuer, "ana")
        await on_list(client, fake_issuer, "1 kg chicken thigh")
        _, outcome = await propose_and_approve(client, fake_issuer)

    assert list_rows(db) == [("Chicken thigh", "1.5", "kg", "member")]
    assert outcome["topped_up"] == ["chicken thigh: 1 kg → 1.5 kg"]


async def test_an_item_with_no_amount_on_the_list_is_skipped_with_what_to_check(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY])
    curry = await rid_in_db(db, "chicken-curry")
    extra = {"name": "chicken thigh", "quantity": 300, "unit": "g"}
    async with client_for(ScriptedModel(curry_plan(curry, extra))) as client:
        await create_household(client, fake_issuer, "ana")
        await on_list(client, fake_issuer, "chicken thigh")
        _, outcome = await propose_and_approve(client, fake_issuer)

    assert list_rows(db) == [("chicken thigh", None, None, "member")]
    assert outcome["topped_up"] == []
    assert outcome["skipped"] == [
        "chicken thigh is already on the list with no amount: make sure it covers 300 g more"
    ]


async def test_a_ticked_item_is_not_topped_up(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    """Ticked means bought: a new line goes on, the bought one stays as it was."""
    await load([CURRY])
    curry = await rid_in_db(db, "chicken-curry")
    extra = {"name": "chicken thigh", "quantity": 300, "unit": "g"}
    async with client_for(ScriptedModel(curry_plan(curry, extra))) as client:
        await create_household(client, fake_issuer, "ana")
        await on_list(client, fake_issuer, "200 g chicken thigh")
        lst = (await client.get("/list", headers=fake_issuer.headers("ana"))).json()
        item = lst["items"][0]
        response = await client.put(
            f"/lists/{lst['id']}/items/{item['id']}/checked",
            json={"checked": True},
            headers=fake_issuer.headers("ana") | idem(),
        )
        assert response.status_code == 200, response.text
        _, outcome = await propose_and_approve(client, fake_issuer)

    assert list_rows(db) == [
        ("Chicken thigh", "200.0", "g", "member"),
        ("chicken thigh", "300.0", "g", "agent"),
    ]
    assert outcome["topped_up"] == []


# --- the agent proposes only what's missing -----------------------------------------------


async def test_coverage_takes_off_what_is_already_on_the_list(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY])
    curry = await rid_in_db(db, "chicken-curry")
    seen: list[Any] = []

    def capture(messages: Any) -> list[dict[str, Any]]:
        seen.append(last_result(messages))
        return [say_text("Done.")]

    meals = [{"recipe_id": curry, "servings": 4}]  # the curry serves 4: 500 g chicken thigh
    model = ScriptedModel([[tool("check_kitchen_coverage", meals=meals)], capture])
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        # Partly on the list, fully on the list, and on it with no amount.
        await on_list(client, fake_issuer, "200 g chicken thigh", "1 onion", "chickpeas")
        cid = await start(client, fake_issuer)
        await say(client, fake_issuer, cid, "what do I need?")

    result = seen[0]
    missing = {m["ingredient"]: m for m in result["missing"]}
    assert missing["chicken thigh"]["need"] == 300.0  # 500 needed, 200 on the list
    assert missing["chicken thigh"]["on_list"] == "200 g"
    assert "onion" not in missing
    assert "chickpeas" not in missing
    on = {m["ingredient"]: m for m in result["on_list"]}
    assert on["onion"] == {"ingredient": "onion", "on_list": "1"}
    assert on["chickpeas"] == {"ingredient": "chickpeas", "on_list": "some (no amount)"}


def test_the_prompt_says_additions_are_extra_on_top_of_the_list() -> None:
    assert "extra on top of what's already on the Shopping List" in SYSTEM
