"""Swapping a day of a pending Proposal (slice 6e, ADR 0025): a fourth answer to the
paused graph, handled by plain code. The old Proposal is superseded and a new one shown.
No model call: the scripted model has nothing queued for the swap, so one would fail."""

from typing import Any

import httpx
import pytest
from sqlalchemy import Engine

from tests.conftest import ClientFor, FakeIssuer, Loader
from tests.fake_model import ScriptedModel
from tests.fake_model import text as say_text
from tests.helpers import context_json, create_household, idem
from tests.test_agent import MON, TUE, rid_in_db, say
from tests.test_approvals import decide, propose, rows, two_dinners
from tests.test_dietary_rules import SALAD
from tests.test_recipes import CURRY, PASTA, STIR_FRY

pytestmark = pytest.mark.anyio


async def setup(load: Loader, db: Engine) -> dict[str, str]:
    await load([CURRY, PASTA, STIR_FRY, SALAD])
    return {
        slug: await rid_in_db(db, slug)
        for slug in ("chicken-curry", "tomato-pasta", "beef-stir-fry", "chickpea-salad")
    }


def plan(ids: dict[str, str]) -> ScriptedModel:
    """Curry Monday, pasta Tuesday; onion (curry), parmesan (pasta), rice (asked for)."""
    return ScriptedModel(
        two_dinners(ids["chicken-curry"], ids["tomato-pasta"], "onion", "parmesan", "rice")
    )


async def alternatives(
    client: httpx.AsyncClient, issuer: FakeIssuer, pid: str, day: str
) -> httpx.Response:
    return await client.get(
        f"/proposals/{pid}/alternatives", params={"date": day}, headers=issuer.headers("ana")
    )


async def swap(
    client: httpx.AsyncClient, issuer: FakeIssuer, pid: str, day: str, rid: str
) -> httpx.Response:
    return await decide(client, issuer, pid, {"action": "swap", "date": day, "recipe_id": rid})


async def test_alternatives_leave_out_the_plans_recipes(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    ids = await setup(load, db)
    async with client_for(plan(ids)) as client:
        await create_household(client, fake_issuer, "ana")
        _, proposal = await propose(client, fake_issuer)

        response = await alternatives(client, fake_issuer, proposal["id"], TUE)

        assert response.status_code == 200, response.text
        titles = {i["title"] for i in response.json()}
        assert titles == {"Beef and broccoli stir-fry", "Chickpea salad"}
        assert {"missing", "kitchen_uses", "favourite"} <= set(response.json()[0])


async def test_swapping_a_day_shows_a_new_proposal_without_a_model_call(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    ids = await setup(load, db)
    async with client_for(plan(ids)) as client:
        await create_household(client, fake_issuer, "ana")
        _, proposal = await propose(client, fake_issuer)

        response = await swap(client, fake_issuer, proposal["id"], TUE, ids["beef-stir-fry"])

        assert response.status_code == 200, response.text
        new = response.json()
        assert new["id"] != proposal["id"]
        assert new["status"] == "pending"
        assert [(m["date"], m["title"]) for m in new["meals"]] == [
            (MON, "Chicken and chickpea curry"),
            (TUE, "Beef and broccoli stir-fry"),
        ]
        assert new["meals"][1]["servings"] == 2  # the swapped day keeps its servings
        statuses = rows(db, "SELECT status FROM proposals ORDER BY created_at")
        assert [r.status for r in statuses] == ["superseded", "pending"]


async def test_a_swap_redoes_only_that_days_shopping(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    ids = await setup(load, db)
    async with client_for(plan(ids)) as client:
        await create_household(client, fake_issuer, "ana")
        _, proposal = await propose(client, fake_issuer)

        new = (await swap(client, fake_issuer, proposal["id"], TUE, ids["beef-stir-fry"])).json()

        names = sorted(a["name"].lower() for a in new["list_additions"])
        # parmesan was only for the pasta; onion is the curry's; rice was asked for (and
        # the stir-fry needs it too: not added twice); beef and broccoli are new.
        assert names == ["beef steak", "broccoli", "onion", "rice"]
        reasons = {a["name"].lower(): a["reason"] for a in new["list_additions"]}
        assert reasons["beef steak"] == "meal" and reasons["onion"] == "meal"


async def test_the_swapped_plan_can_be_approved(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    ids = await setup(load, db)
    async with client_for(plan(ids)) as client:
        await create_household(client, fake_issuer, "ana")
        _, proposal = await propose(client, fake_issuer)
        new = (await swap(client, fake_issuer, proposal["id"], TUE, ids["beef-stir-fry"])).json()

        old = await decide(client, fake_issuer, proposal["id"], {"action": "approve"})
        assert old.status_code == 409  # the superseded one is closed
        approved = await decide(client, fake_issuer, new["id"], {"action": "approve"})
        assert approved.status_code == 200, approved.text

        saved = rows(
            db,
            "SELECT pm.date, r.title FROM planned_meals pm JOIN recipes r ON r.id = pm.recipe_id"
            " ORDER BY pm.date",
        )
        assert [(str(r.date), r.title) for r in saved] == [
            (MON, "Chicken and chickpea curry"),
            (TUE, "Beef and broccoli stir-fry"),
        ]


async def test_the_next_turn_sees_the_swap(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    ids = await setup(load, db)
    model = ScriptedModel(
        [
            *two_dinners(ids["chicken-curry"], ids["tomato-pasta"]),
            [say_text("Sure.")],
        ]
    )
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid, proposal = await propose(client, fake_issuer)
        await swap(client, fake_issuer, proposal["id"], TUE, ids["beef-stir-fry"])

        await say(client, fake_issuer, cid, "make Monday quicker")
        context = context_json(model.calls[-1][-1]["content"][0]["text"])
        assert [m["title"] for m in context["current_draft_plan"]] == [
            "Chicken and chickpea curry",
            "Beef and broccoli stir-fry",
        ]


async def test_a_swap_is_checked_before_the_graph_resumes(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    ids = await setup(load, db)
    async with client_for(plan(ids)) as client:
        await create_household(client, fake_issuer, "ana")
        _, proposal = await propose(client, fake_issuer)
        pid = proposal["id"]

        other_day = await swap(client, fake_issuer, pid, "2099-01-01", ids["beef-stir-fry"])
        assert other_day.status_code == 422
        unknown = await swap(client, fake_issuer, pid, TUE, "00000000-0000-0000-0000-000000000000")
        assert unknown.status_code == 404
        missing: dict[str, Any] = {"action": "swap", "date": TUE}
        assert (await decide(client, fake_issuer, pid, missing)).status_code == 422

        response = await client.put(
            "/households/current/dietary-rules",
            json={"diets": ["vegetarian"], "excluded_ingredient_ids": []},
            headers=fake_issuer.headers("ana") | idem(),
        )
        assert response.status_code == 200, response.text
        meat = await swap(client, fake_issuer, pid, TUE, ids["beef-stir-fry"])
        assert meat.status_code == 409
        assert "Dietary Rules" in meat.json()["detail"]
        # Nothing changed: still the one pending Proposal.
        assert [r.status for r in rows(db, "SELECT status FROM proposals")] == ["pending"]
