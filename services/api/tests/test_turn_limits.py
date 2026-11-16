"""Rate limits on the agent (slice 10): one turn at a time per Member, and at most 30
messages per Member per hour. Counted in Postgres (agent_turns), so they hold across
every copy of the API. The Household's daily token budget stays the cost ceiling."""

from datetime import timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text

from app.models import utcnow
from app.services.turn_limits import MAX_PER_HOUR
from tests.conftest import ClientFor, FakeIssuer
from tests.fake_model import ScriptedModel
from tests.fake_model import text as say_text
from tests.helpers import create_household, invite, join
from tests.test_agent import say, start

pytestmark = pytest.mark.anyio


def member_id(db: Engine, subject: str) -> str:
    with db.connect() as conn:
        found = conn.execute(
            text("SELECT id FROM members WHERE auth_subject = :s"), {"s": subject}
        ).scalar_one()
    return str(found)


def past_turns(
    db: Engine, subject: str, cid: str, ago: list[timedelta], finished: bool = True
) -> None:
    """Turns that already happened, `ago` before now."""
    now = utcnow()
    with db.begin() as conn:
        for delta in ago:
            conn.execute(
                text(
                    "INSERT INTO agent_turns (id, member_id, conversation_id, started_at, "
                    "finished_at) VALUES (gen_random_uuid(), :m, :c, :s, :f)"
                ),
                {
                    "m": member_id(db, subject),
                    "c": cid,
                    "s": now - delta,
                    "f": now - delta + timedelta(seconds=5) if finished else None,
                },
            )


async def post(
    client: httpx.AsyncClient, issuer: FakeIssuer, cid: str, who: str = "ana"
) -> httpx.Response:
    """Send a message and read the whole reply (stream or error)."""
    async with client.stream(
        "POST", f"/conversations/{cid}/messages", json={"text": "hi"}, headers=issuer.headers(who)
    ) as response:
        await response.aread()
    return response


def turns(db: Engine) -> list[Any]:
    with db.connect() as conn:
        return list(conn.execute(text("SELECT started_at, finished_at FROM agent_turns")))


async def test_a_turn_is_recorded_and_finished(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine
) -> None:
    async with client_for(ScriptedModel([[say_text("Hi.")], [say_text("Hi again.")]])) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await start(client, fake_issuer)
        await say(client, fake_issuer, cid, "hello")
        await say(client, fake_issuer, cid, "hello again")  # not blocked by the first

    recorded = turns(db)
    assert len(recorded) == 2
    assert all(row.finished_at is not None for row in recorded)


async def test_the_31st_message_in_an_hour_waits(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine
) -> None:
    model = ScriptedModel([])  # any model call would fail the test
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await start(client, fake_issuer)
        # 30 in the last hour; the oldest was 50 minutes ago, so a slot frees in 10.
        ago = [timedelta(minutes=50)] + [timedelta(minutes=m) for m in range(1, MAX_PER_HOUR)]
        past_turns(db, "ana", cid, ago)

        response = await post(client, fake_issuer, cid)

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    assert 595 <= int(response.headers["Retry-After"]) <= 601
    assert len(turns(db)) == MAX_PER_HOUR  # a refused message isn't counted


async def test_messages_older_than_an_hour_dont_count(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine
) -> None:
    async with client_for(ScriptedModel([[say_text("Hi.")]])) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await start(client, fake_issuer)
        past_turns(db, "ana", cid, [timedelta(minutes=61)] * MAX_PER_HOUR)

        assert (await post(client, fake_issuer, cid)).status_code == 200


async def test_one_turn_at_a_time_across_all_of_a_members_conversations(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine
) -> None:
    async with client_for(ScriptedModel([[say_text("Hi, Bo.")]])) as client:
        await create_household(client, fake_issuer, "ana")
        await join(client, fake_issuer, "bo", await invite(client, fake_issuer, "ana"))
        first, other = await start(client, fake_issuer), await start(client, fake_issuer)
        past_turns(db, "ana", first, [timedelta(seconds=5)], finished=False)  # still running

        busy = await post(client, fake_issuer, other)  # a second chat doesn't get round it
        someone_else = await post(client, fake_issuer, await start(client, fake_issuer, "bo"), "bo")

    assert busy.status_code == 409
    assert busy.json()["code"] == "turn_in_progress"
    assert someone_else.status_code == 200  # per Member, not per Household


async def test_a_turn_left_running_by_a_crash_stops_blocking(
    client_for: ClientFor, fake_issuer: FakeIssuer, db: Engine
) -> None:
    """A server that dies mid-turn never sets finished_at. After the turn timeout (plus a
    margin) it no longer counts as running, or the Member would be locked out for good."""
    async with client_for(ScriptedModel([[say_text("Hi.")]])) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await start(client, fake_issuer)
        past_turns(db, "ana", cid, [timedelta(minutes=5)], finished=False)

        assert (await post(client, fake_issuer, cid)).status_code == 200
