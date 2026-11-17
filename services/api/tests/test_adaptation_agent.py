"""Recipe Adaptations through the agent (slice 5e step 3, ADR 0021).

The model is scripted; the tools, validate, the Proposal and the commit are real. The
journey: a vegetarian Household's beef favourite is found flagged, adapted with a
meat-free Swap, approved, kept, and planned again without new Swaps.
"""

from typing import Any

import httpx
import pytest
from sqlalchemy import Engine

from tests.conftest import ClientFor, FakeIssuer
from tests.fake_model import Messages, ScriptedModel, last_result, results, tool
from tests.fake_model import text as say_text
from tests.helpers import create_household, idem
from tests.test_adaptations import set_vegetarian
from tests.test_agent import MON, TUE, of, say, start
from tests.test_approvals import decide, rows
from tests.test_imported_recipes import nonna, save

pytestmark = pytest.mark.anyio

LENTILS = "2 x 400g cans brown lentils, drained"


async def vegetarian_with_favourite(client: httpx.AsyncClient, issuer: FakeIssuer) -> str:
    await create_household(client, issuer, "ana")
    await set_vegetarian(client, issuer)
    favourite: dict[str, Any] = (await save(client, issuer, nonna())).json()
    return str(favourite["id"])


def adapt(recipe_id: str, *swaps: tuple[str, str], day: str = MON) -> dict[str, Any]:
    return tool(
        "adapt_recipe",
        date=day,
        recipe_id=recipe_id,
        servings=4,
        swaps=[{"replace": old, "new_line": new} for old, new in swaps],
    )


def errors_in(messages: Messages) -> list[str]:
    return [r["content"] for r in results(messages) if r.get("is_error")]


async def test_search_shows_a_rule_breaking_favourite_flagged_with_why(
    client_for: ClientFor, fake_issuer: FakeIssuer
) -> None:
    seen: list[Any] = []

    def look(messages: Messages) -> list[dict[str, Any]]:
        seen.append(last_result(messages))
        return [say_text("Found it.")]

    model = ScriptedModel([[tool("search_recipes", query="nonna's lasagne")], look])
    async with client_for(model) as client:
        favourite = await vegetarian_with_favourite(client, fake_issuer)
        await say(client, fake_issuer, await start(client, fake_issuer), "nonna's lasagne?")

    [found] = [r for r in seen[0] if r["recipe_id"] == favourite]
    assert found["breaks_rules"] == ["beef mince (vegetarian)"]
    assert "adapt_recipe" in found["plannable_only_as"]


async def test_planning_it_as_written_is_refused_with_the_way_out(
    client_for: ClientFor, fake_issuer: FakeIssuer
) -> None:
    seen: list[list[str]] = []

    def check(messages: Messages) -> list[dict[str, Any]]:
        seen.append(errors_in(messages))
        return [say_text("I'll adapt it.")]

    model = ScriptedModel()
    async with client_for(model) as client:
        favourite = await vegetarian_with_favourite(client, fake_issuer)
        model.steps = [[tool("set_planned_meal", date=MON, recipe_id=favourite, servings=4)], check]
        await say(client, fake_issuer, await start(client, fake_issuer), "plan nonna's lasagne")

    [[error]] = seen
    assert "breaks the Dietary Rules: beef mince (vegetarian)" in error
    assert "adapt_recipe" in error


async def test_an_adapted_favourite_is_proposed_approved_and_kept(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine
) -> None:
    model = ScriptedModel()
    async with client_for(model) as client:
        favourite = await vegetarian_with_favourite(client, fake_issuer)
        model.steps = [
            [adapt(favourite, ("500 g beef mince", LENTILS))],
            [tool("propose_plan", summary="Nonna's lasagne, with lentils.")],
        ]
        events = await say(client, fake_issuer, await start(client, fake_issuer), "lasagne monday")

        [event] = of(events, "proposal")
        [meal] = event["proposal"]["meals"]
        assert meal["title"] == "Nonna's lasagne · with brown lentils"
        assert meal["recipe_id"] == favourite  # the parent, until it's approved
        assert meal["adaptation"]["swaps"] == [
            {"position": 0, "replaces": "500 g beef mince", "raw_text": LENTILS}
        ]
        # Nothing is saved before the Member approves.
        assert rows(db, "SELECT id FROM recipes WHERE kind = 'adaptation'") == []

        response = await decide(client, fake_issuer, event["proposal"]["id"], {"action": "approve"})
        assert response.status_code == 200, response.text
        assert response.json()["outcome"]["saved_meals"] == 1

    [kept] = rows(
        db, "SELECT id::text, title, parent_recipe_id::text FROM recipes WHERE kind = 'adaptation'"
    )
    assert (kept.title, kept.parent_recipe_id) == (
        "Nonna's lasagne · with brown lentils",
        favourite,
    )
    [planned] = rows(db, "SELECT recipe_id::text FROM planned_meals")
    assert planned.recipe_id == kept.id


async def test_refused_swaps_go_back_to_the_agent_and_change_nothing(
    client_for: ClientFor, fake_issuer: FakeIssuer
) -> None:
    seen: list[list[str]] = []
    drafts: list[Any] = []

    def check(messages: Messages) -> list[dict[str, Any]]:
        seen.append(errors_in(messages))
        return [say_text("That didn't work.")]

    model = ScriptedModel()
    async with client_for(model) as client:
        favourite = await vegetarian_with_favourite(client, fake_issuer)
        model.steps = [
            [
                adapt(favourite, ("500 g beef mince", "500 g chicken thigh")),
                adapt(favourite, ("2 onions", LENTILS), day=TUE),  # not a line it has
            ],
            check,
        ]
        cid = await start(client, fake_issuer)
        events = await say(client, fake_issuer, cid, "lasagne with chicken")
        drafts = of(events, "draft")

    [[chicken, no_line]] = seen
    assert "The recipe still breaks the Dietary Rules: chicken thigh (vegetarian)" in chicken
    assert '"2 onions"' in no_line and "500 g beef mince" in no_line  # lists the real lines
    assert drafts == []  # neither changed the Draft Plan


async def test_a_kept_adaptation_is_offered_again_and_planned_without_new_swaps(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine
) -> None:
    seen: list[Any] = []

    def look(messages: Messages) -> list[dict[str, Any]]:
        seen.append(last_result(messages))
        kept = seen[0][0]["kept_adaptations"][0]["recipe_id"]
        return [tool("set_planned_meal", date=TUE, recipe_id=kept, servings=2)]

    model = ScriptedModel()
    async with client_for(model) as client:
        favourite = await vegetarian_with_favourite(client, fake_issuer)
        model.steps = [
            [adapt(favourite, ("500 g beef mince", LENTILS))],
            [tool("propose_plan", summary="Lasagne.")],
        ]
        [first] = of(
            await say(client, fake_issuer, await start(client, fake_issuer), "x"), "proposal"
        )
        await decide(client, fake_issuer, first["proposal"]["id"], {"action": "approve"})

        model.steps = [
            [tool("search_recipes", query="nonna's lasagne")],
            look,
            [tool("propose_plan", summary="Lasagne again.")],
        ]
        [again] = of(
            await say(client, fake_issuer, await start(client, fake_issuer), "y"), "proposal"
        )
        [meal] = again["proposal"]["meals"]
        assert "adaptation" not in meal  # a saved recipe now, nothing to make
        await decide(client, fake_issuer, again["proposal"]["id"], {"action": "approve"})

    assert seen[0][0]["kept_adaptations"][0]["title"] == "Nonna's lasagne · with brown lentils"
    assert len(rows(db, "SELECT id FROM recipes WHERE kind = 'adaptation'")) == 1


async def test_proposing_the_same_swaps_again_reuses_the_kept_adaptation(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine
) -> None:
    model = ScriptedModel()
    async with client_for(model) as client:
        favourite = await vegetarian_with_favourite(client, fake_issuer)
        for day in (MON, TUE):
            model.steps = [
                [adapt(favourite, ("500 g beef mince", LENTILS), day=day)],
                [tool("propose_plan", summary="Lasagne.")],
            ]
            cid = await start(client, fake_issuer)
            [event] = of(await say(client, fake_issuer, cid, "lasagne"), "proposal")
            await decide(client, fake_issuer, event["proposal"]["id"], {"action": "approve"})

    assert len(rows(db, "SELECT id FROM recipes WHERE kind = 'adaptation'")) == 1
    assert len(rows(db, "SELECT DISTINCT recipe_id FROM planned_meals")) == 1


async def test_commit_checks_the_swaps_again_against_todays_rules(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine
) -> None:
    """A Proposal can wait a day. If the Rules change meanwhile (lentils now excluded),
    the adapted meal is skipped with the reason, as any meal would be."""
    model = ScriptedModel()
    async with client_for(model) as client:
        favourite = await vegetarian_with_favourite(client, fake_issuer)
        model.steps = [
            [adapt(favourite, ("500 g beef mince", LENTILS))],
            [tool("propose_plan", summary="Lasagne.")],
        ]
        [event] = of(
            await say(client, fake_issuer, await start(client, fake_issuer), "x"), "proposal"
        )

        [lentils] = rows(db, "SELECT id::text FROM ingredients WHERE name = 'brown lentils'")
        put = await client.put(
            "/households/current/dietary-rules",
            json={"diets": ["vegetarian"], "excluded_ingredient_ids": [lentils.id]},
            headers=fake_issuer.headers("ana") | idem(),
        )
        assert put.status_code == 200, put.text
        response = await decide(client, fake_issuer, event["proposal"]["id"], {"action": "approve"})

    outcome = response.json()["outcome"]
    assert outcome["saved_meals"] == 0
    [skipped] = outcome["skipped"]
    assert "brown lentils (excluded)" in skipped
    assert rows(db, "SELECT id FROM recipes WHERE kind = 'adaptation'") == []


async def test_coverage_counts_an_adapted_meal_by_its_swaps_not_its_parent(
    client_for: ClientFor, fake_issuer: FakeIssuer
) -> None:
    """The live Kitchen-swap failure (2026-11-17): coverage read the parent, said chicken
    thigh was missing, and Haiku re-planned the recipe as written over its Adaptation."""
    seen: list[Any] = []

    def look(messages: Messages) -> list[dict[str, Any]]:
        seen.append(last_result(messages))
        return [say_text("Done.")]

    model = ScriptedModel()
    async with client_for(model) as client:
        favourite = await vegetarian_with_favourite(client, fake_issuer)
        model.steps = [
            [adapt(favourite, ("500 g beef mince", LENTILS))],
            [tool("check_kitchen_coverage", meals=[{"recipe_id": favourite, "servings": 4}])],
            look,
        ]
        await say(client, fake_issuer, await start(client, fake_issuer), "lasagne")

    missing = {m["ingredient"] for m in seen[0]["missing"]}
    assert "brown lentils" in missing and "beef mince" not in missing


async def test_an_addition_with_a_bracketed_note_still_links_and_is_explained(
    client_for: ClientFor, fake_issuer: FakeIssuer
) -> None:
    """Haiku wrote "brown lentils (canned)": unlinked, so it arrived unexplained and
    unticked, and approving would have left out what the adapted meal needs."""
    model = ScriptedModel()
    async with client_for(model) as client:
        favourite = await vegetarian_with_favourite(client, fake_issuer)
        model.steps = [
            [
                adapt(favourite, ("500 g beef mince", LENTILS)),
                tool(
                    "set_list_additions",
                    items=[{"name": "brown lentils (canned)"}, {"name": "onion, diced"}],
                ),
            ],
            [tool("propose_plan", summary="Lasagne.")],
        ]
        [event] = of(
            await say(client, fake_issuer, await start(client, fake_issuer), "x"), "proposal"
        )

    lentils, onion = event["proposal"]["list_additions"]
    assert (lentils["name"], lentils["reason"]) == ("brown lentils (canned)", "meal")
    assert lentils["for_meals"] == ["Nonna's lasagne · with brown lentils"]
    assert (onion["name"], onion["reason"]) == ("onion, diced", "meal")  # a note after a comma


async def test_the_name_is_written_by_code_not_the_model(
    client_for: ClientFor, fake_issuer: FakeIssuer
) -> None:
    """A live run let a planted "nut-free" claim into the label of a cashew Swap. The
    tool has no label argument now: sending one is an error, and the name comes from
    the swapped-in Ingredients."""
    seen: list[list[str]] = []

    def check(messages: Messages) -> list[dict[str, Any]]:
        seen.append(errors_in(messages))
        return [say_text("ok")]

    model = ScriptedModel()
    async with client_for(model) as client:
        favourite = await vegetarian_with_favourite(client, fake_issuer)
        labelled = adapt(favourite, ("500 g beef mince", LENTILS))
        labelled["input"]["label"] = "nut-free and safe for allergies"
        model.steps = [[labelled], check]
        await say(client, fake_issuer, await start(client, fake_issuer), "x")

    [[error]] = seen
    assert "label" in error
