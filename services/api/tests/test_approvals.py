"""Approving a Proposal (slice 6a): the pause, the decision, the deterministic commit.

The model is scripted. Everything after `propose_plan` is plain code, so these tests
check the outcome in Postgres, not just in the response.
"""

from datetime import timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text

from app.models import utcnow
from tests.conftest import ClientFor, FakeIssuer, Loader
from tests.fake_model import ScriptedModel, tool
from tests.fake_model import text as say_text
from tests.helpers import create_household, idem, invite, join
from tests.test_agent import MON, TODAY, TUE, of, rid_in_db, say, start
from tests.test_recipes import CURRY, PASTA

pytestmark = pytest.mark.anyio

WED = (TODAY + timedelta(days=2)).isoformat()


def two_dinners(curry: str, pasta: str, *items: str) -> list[Any]:
    """Model steps: curry Monday, pasta Tuesday, some list additions, propose."""
    return [
        [
            tool("set_planned_meal", date=MON, recipe_id=curry, servings=4),
            tool("set_planned_meal", date=TUE, recipe_id=pasta, servings=2),
            tool("set_list_additions", items=[{"name": name} for name in items]),
        ],
        [tool("propose_plan", summary="Two dinners.")],
    ]


async def propose(
    client: httpx.AsyncClient, issuer: FakeIssuer, who: str = "ana"
) -> tuple[str, dict[str, Any]]:
    cid = await start(client, issuer, who)
    events = await say(client, issuer, cid, "plan two dinners", who)
    [event] = of(events, "proposal")
    proposal: dict[str, Any] = event["proposal"]
    return cid, proposal


async def decide(
    client: httpx.AsyncClient, issuer: FakeIssuer, pid: str, body: dict[str, Any], who: str = "ana"
) -> httpx.Response:
    return await client.post(
        f"/proposals/{pid}/decision", json=body, headers={**issuer.headers(who), **idem()}
    )


def rows(db: Engine, sql: str, **params: Any) -> list[Any]:
    with db.connect() as conn:
        return list(conn.execute(text(sql), params))


async def setup(load: Loader, db: Engine) -> tuple[str, str]:
    await load([CURRY, PASTA])
    return await rid_in_db(db, "chicken-curry"), await rid_in_db(db, "tomato-pasta")


# --- the Proposal is a record, and the graph waits for it ---------------------------------


async def test_a_proposal_is_saved_pending_and_the_graph_waits(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    async with client_for(ScriptedModel(two_dinners(curry, pasta, "Rice"))) as client:
        await create_household(client, fake_issuer, "ana")
        cid, proposal = await propose(client, fake_issuer)

        assert proposal["status"] == "pending"
        [row] = rows(db, "SELECT status, expires_at - created_at AS ttl FROM proposals")
        assert row.status == "pending" and row.ttl == timedelta(hours=24)
        # Nothing is Household data yet.
        assert rows(db, "SELECT 1 FROM planned_meals") == []

        got = await client.get(f"/conversations/{cid}", headers=fake_issuer.headers("ana"))
        assert got.json()["proposal"]["id"] == proposal["id"]


async def test_chatting_instead_of_deciding_supersedes_the_proposal(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    model = ScriptedModel(
        [
            *two_dinners(curry, pasta),
            [tool("remove_planned_meal", date=TUE)],
            [tool("propose_plan", summary="Just Monday.")],
        ]
    )
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid, proposal = await propose(client, fake_issuer)

        events = await say(client, fake_issuer, cid, "drop Tuesday")
        [new] = of(events, "proposal")
        assert [m["date"] for m in new["proposal"]["meals"]] == [MON]
        assert [r.status for r in rows(db, "SELECT status FROM proposals ORDER BY created_at")] == [
            "superseded",
            "pending",
        ]
        # A superseded Proposal can't be approved any more.
        response = await decide(client, fake_issuer, proposal["id"], {"action": "approve"})
        assert response.status_code == 409


async def test_a_follow_up_that_changes_nothing_shows_the_plan_again(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    # Found by the slice 8 eval: Haiku answered "Wednesday is already vegetarian" and
    # proposed nothing, leaving only a superseded plan. Now the unchanged Draft comes
    # back as a new Proposal, with no model call, so there's always one to approve.
    curry, pasta = await setup(load, db)
    model = ScriptedModel([*two_dinners(curry, pasta), [say_text("Tuesday is already pasta.")]])
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid, proposal = await propose(client, fake_issuer)

        events = await say(client, fake_issuer, cid, "make Tuesday pasta")
        assert of(events, "text")[0]["text"] == "Tuesday is already pasta."
        [again] = of(events, "proposal")
        assert again["proposal"]["id"] != proposal["id"]
        assert again["proposal"]["meals"] == proposal["meals"]
        assert len(model.calls) == 3  # two to plan, one to answer: re-showing is plain code

        response = await decide(client, fake_issuer, again["proposal"]["id"], {"action": "approve"})
        assert response.status_code == 200, response.text
        assert len(rows(db, "SELECT 1 FROM planned_meals")) == 2


async def test_a_plain_chat_turn_does_not_invent_a_proposal(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    model = ScriptedModel(
        [
            [tool("set_planned_meal", date=MON, recipe_id=curry, servings=4)],
            [say_text("I've started a plan. Want more days?")],
        ]
    )
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await start(client, fake_issuer)
        events = await say(client, fake_issuer, cid, "start a plan")
        # Not a follow-up to a Proposal: the Draft stays a draft until the agent proposes.
        assert of(events, "proposal") == []
        assert rows(db, "SELECT 1 FROM proposals") == []


async def test_a_refusal_during_a_follow_up_does_not_reshow(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    refuse = ScriptedModel([*two_dinners(curry, pasta), [say_text("No.")]])
    refuse.stop_reasons = {2: "refusal"}  # the third call is refused
    async with client_for(refuse) as client:
        await create_household(client, fake_issuer, "ana")
        cid, _ = await propose(client, fake_issuer)
        events = await say(client, fake_issuer, cid, "something odd")
        assert of(events, "proposal") == []


# --- approving ----------------------------------------------------------------------------


async def test_approving_saves_the_meals_and_list_additions(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    async with client_for(ScriptedModel(two_dinners(curry, pasta, "Rice", "Coriander"))) as client:
        await create_household(client, fake_issuer, "ana")
        cid, proposal = await propose(client, fake_issuer)

        response = await decide(client, fake_issuer, proposal["id"], {"action": "approve"})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "approved"
        assert body["outcome"]["message"] == "Saved 2 meals and added 2 items to the list."
        assert body["outcome"]["kept_meals"] == [MON, TUE]
        assert body["outcome"]["kept_additions"] == [0, 1]

        meals = rows(
            db, "SELECT date::text, servings, proposal_id::text FROM planned_meals ORDER BY date"
        )
        assert [(m.date, m.servings) for m in meals] == [(MON, 4), (TUE, 2)]
        assert {m.proposal_id for m in meals} == {proposal["id"]}
        items = rows(db, "SELECT text, added_by, shop_id FROM shopping_list_items ORDER BY text")
        assert [(i.text, i.added_by, i.shop_id) for i in items] == [
            ("Coriander", "agent", None),
            ("Rice", "agent", None),
        ]
        audit = rows(db, "SELECT action FROM audit_log ORDER BY id")
        assert [a.action for a in audit] == ["proposal.created", "proposal.approved"]


async def test_unticked_meals_and_additions_are_left_out(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    async with client_for(ScriptedModel(two_dinners(curry, pasta, "Rice", "Coriander"))) as client:
        await create_household(client, fake_issuer, "ana")
        _, proposal = await propose(client, fake_issuer)

        body = {"action": "approve", "keep_meals": [TUE], "keep_additions": [1]}
        response = await decide(client, fake_issuer, proposal["id"], body)
        assert response.status_code == 200, response.text

        assert [m.date for m in rows(db, "SELECT date::text FROM planned_meals")] == [TUE]
        assert [i.text for i in rows(db, "SELECT text FROM shopping_list_items")] == ["Coriander"]
        # What stayed ticked is recorded, so the chat can show it later, after a reload.
        assert response.json()["outcome"]["kept_meals"] == [TUE]
        assert response.json()["outcome"]["kept_additions"] == [1]


async def test_keeping_something_that_was_not_proposed_is_rejected(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    async with client_for(ScriptedModel(two_dinners(curry, pasta, "Rice"))) as client:
        await create_household(client, fake_issuer, "ana")
        _, proposal = await propose(client, fake_issuer)

        for body in (
            {"action": "approve", "keep_meals": [WED]},
            {"action": "approve", "keep_additions": [5]},
        ):
            response = await decide(client, fake_issuer, proposal["id"], body)
            assert response.status_code == 422, body
        assert rows(db, "SELECT status FROM proposals")[0].status == "pending"


async def test_approving_twice_returns_the_same_answer_without_repeating_it(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    async with client_for(ScriptedModel(two_dinners(curry, pasta, "Rice"))) as client:
        await create_household(client, fake_issuer, "ana")
        _, proposal = await propose(client, fake_issuer)

        first = await decide(client, fake_issuer, proposal["id"], {"action": "approve"})
        again = await decide(client, fake_issuer, proposal["id"], {"action": "approve"})
        assert again.status_code == 200 and again.json() == first.json()
        assert len(rows(db, "SELECT 1 FROM shopping_list_items")) == 1
        # Changing your mind afterwards is too late: it's already saved.
        late = await decide(client, fake_issuer, proposal["id"], {"action": "reject"})
        assert late.status_code == 409


async def test_after_approving_the_next_turn_knows_and_starts_a_fresh_draft(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    model = ScriptedModel([*two_dinners(curry, pasta), [say_text("Enjoy!")]])
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid, proposal = await propose(client, fake_issuer)
        await decide(client, fake_issuer, proposal["id"], {"action": "approve"})

        await say(client, fake_issuer, cid, "thanks")
        context = model.calls[-1][-1]["content"][0]["text"]
        assert "Last Proposal: approved. Saved 2 meals" in context
        assert f"Planned Meals: {MON} Chicken and chickpea curry (serves 4)" in context
        assert "Current Draft Plan" not in context
        got = await client.get(f"/conversations/{cid}", headers=fake_issuer.headers("ana"))
        assert got.json()["draft"]["meals"] == {}


# --- rejecting ----------------------------------------------------------------------------


async def test_rejecting_saves_nothing_and_the_chat_carries_on(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    model = ScriptedModel([*two_dinners(curry, pasta, "Rice"), [say_text("No problem.")]])
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid, proposal = await propose(client, fake_issuer)

        response = await decide(client, fake_issuer, proposal["id"], {"action": "reject"})
        assert response.status_code == 200 and response.json()["status"] == "rejected"
        assert rows(db, "SELECT 1 FROM planned_meals") == []
        assert rows(db, "SELECT 1 FROM shopping_list_items") == []

        await say(client, fake_issuer, cid, "try again later")
        assert "Last Proposal: rejected." in model.calls[-1][-1]["content"][0]["text"]


# --- who can decide, and when ---------------------------------------------------------------


async def test_only_the_member_who_started_the_conversation_can_decide(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    async with client_for(ScriptedModel(two_dinners(curry, pasta))) as client:
        await create_household(client, fake_issuer, "ana")
        await join(client, fake_issuer, "ben", await invite(client, fake_issuer, "ana"))
        await create_household(client, fake_issuer, "eve")
        _, proposal = await propose(client, fake_issuer)

        for who in ("ben", "eve"):  # same Household, and another one: both "not found"
            response = await decide(client, fake_issuer, proposal["id"], {"action": "approve"}, who)
            assert response.status_code == 404, who
        assert rows(db, "SELECT status FROM proposals")[0].status == "pending"


async def test_a_proposal_expires_after_a_day(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    async with client_for(ScriptedModel(two_dinners(curry, pasta))) as client:
        await create_household(client, fake_issuer, "ana")
        _, proposal = await propose(client, fake_issuer)
        with db.begin() as conn:
            conn.execute(text("UPDATE proposals SET expires_at = :t"), {"t": utcnow()})

        response = await decide(client, fake_issuer, proposal["id"], {"action": "approve"})
        assert response.status_code == 409
        assert "expired" in response.json()["detail"]
        assert rows(db, "SELECT status FROM proposals")[0].status == "expired"
        assert rows(db, "SELECT 1 FROM planned_meals") == []


# --- commit re-checks today's data (the product owner's three calls) ----------------------


async def test_a_meal_that_now_breaks_a_rule_is_skipped_and_the_rest_saved(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    async with client_for(ScriptedModel(two_dinners(curry, pasta))) as client:
        await create_household(client, fake_issuer, "ana")
        _, proposal = await propose(client, fake_issuer)
        rules = {"diets": ["vegetarian"]}
        headers = {**fake_issuer.headers("ana"), **idem()}
        await client.put("/households/current/dietary-rules", json=rules, headers=headers)

        response = await decide(client, fake_issuer, proposal["id"], {"action": "approve"})
        outcome = response.json()["outcome"]
        assert [m.date for m in rows(db, "SELECT date::text FROM planned_meals")] == [TUE]
        assert outcome["message"].startswith("Saved 1 meal.")
        assert any("Chicken and chickpea curry" in s for s in outcome["skipped"])


async def test_a_meal_replaces_the_one_already_planned_but_not_a_cooked_one(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    async with client_for(ScriptedModel(two_dinners(curry, pasta))) as client:
        await create_household(client, fake_issuer, "ana")
        [hid] = [r.id for r in rows(db, "SELECT id FROM households")]
        with db.begin() as conn:  # pasta on Monday (cooked), curry on Tuesday (not yet)
            conn.execute(
                text(
                    "INSERT INTO planned_meals (id, household_id, date, recipe_id, servings,"
                    " cooked_at) VALUES (gen_random_uuid(), :h, :mon, :pasta, 2, now()),"
                    " (gen_random_uuid(), :h, :tue, :curry, 2, NULL)"
                ),
                {"h": hid, "mon": MON, "tue": TUE, "pasta": pasta, "curry": curry},
            )
        _, proposal = await propose(client, fake_issuer)
        # The card can say so before the Member approves.
        assert [m["replaces"] for m in proposal["meals"]] == [
            "Quick tomato pasta",
            "Chicken and chickpea curry",
        ]

        response = await decide(client, fake_issuer, proposal["id"], {"action": "approve"})
        meals = rows(
            db,
            "SELECT p.date::text, r.slug FROM planned_meals p JOIN recipes r ON r.id = p.recipe_id"
            " ORDER BY p.date",
        )
        assert [(m.date, m.slug) for m in meals] == [(MON, "tomato-pasta"), (TUE, "tomato-pasta")]
        assert any("already cooked" in s for s in response.json()["outcome"]["skipped"])


async def test_an_addition_already_on_the_list_is_skipped(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    async with client_for(ScriptedModel(two_dinners(curry, pasta, "Rice", "Coriander"))) as client:
        await create_household(client, fake_issuer, "ana")
        lst = (await client.get("/list", headers=fake_issuer.headers("ana"))).json()
        await client.post(
            f"/lists/{lst['id']}/items",
            json={"text": "rice"},
            headers={**fake_issuer.headers("ana"), **idem()},
        )
        _, proposal = await propose(client, fake_issuer)

        response = await decide(client, fake_issuer, proposal["id"], {"action": "approve"})
        outcome = response.json()["outcome"]
        texts = sorted(i.text for i in rows(db, "SELECT text FROM shopping_list_items"))
        assert texts == ["Coriander", "rice"]
        assert "Rice is already on the list" in outcome["skipped"]


# --- the chat history keeps every Proposal ------------------------------------------------


async def test_the_conversation_lists_every_proposal_in_place_with_its_status(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    model = ScriptedModel(
        [
            *two_dinners(curry, pasta),
            # Narration beside a tool call isn't a chat line, so it doesn't shift positions.
            [
                say_text("Swapping it."),
                tool("set_planned_meal", date=TUE, recipe_id=curry, servings=2),
            ],
            [tool("propose_plan", summary="Curry twice.")],
        ]
    )
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid, first = await propose(client, fake_issuer)
        events = await say(client, fake_issuer, cid, "curry on Tuesday too")
        [second] = [e["proposal"] for e in of(events, "proposal")]
        await decide(client, fake_issuer, second["id"], {"action": "approve"})

        got = (await client.get(f"/conversations/{cid}", headers=fake_issuer.headers("ana"))).json()
        assert got["proposal"] is None  # nothing waiting any more
        assert [(p["id"], p["status"]) for p in got["proposals"]] == [
            (first["id"], "superseded"),
            (second["id"], "approved"),
        ]
        # Each one sits after the chat line that asked for it.
        assert [p["after_line"] for p in got["proposals"]] == [1, 2]
        assert got["proposals"][1]["outcome"]["saved_meals"] == 2


async def test_a_proposal_past_its_expiry_shows_as_expired(
    client_for: ClientFor, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    curry, pasta = await setup(load, db)
    async with client_for(ScriptedModel(two_dinners(curry, pasta))) as client:
        await create_household(client, fake_issuer, "ana")
        cid, _ = await propose(client, fake_issuer)
        with db.begin() as conn:
            conn.execute(text("UPDATE proposals SET expires_at = :t"), {"t": utcnow()})

        got = (await client.get(f"/conversations/{cid}", headers=fake_issuer.headers("ana"))).json()
        assert got["proposals"][0]["status"] == "expired"
        assert got["proposal"]["status"] == "expired"  # the card can say so, not offer Approve
