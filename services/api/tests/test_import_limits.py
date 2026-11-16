"""Limits on the import doors (slice 4d step 7).

- 20 attempts per Member per hour across paste, photo, file and link: attempts, so a
  failed one counts too (otherwise junk could be sent forever for free)
- the model doors share the Household's daily token budget with the agent, and every
  call's tokens are counted, even when the answer turns out not to be a recipe
- typing a recipe has no limit: no model, nothing fetched
"""

import uuid
from datetime import timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text

from app import errors
from app.agent.prompt import today_in_sydney
from app.models import utcnow
from app.services.import_limits import MAX_PER_HOUR
from tests.conftest import FakeIssuer
from tests.fake_model import ScriptedFetcher, ScriptedReader
from tests.helpers import create_household, idem, invite, join
from tests.test_recipe_import import PASTED, reading

pytestmark = pytest.mark.anyio


async def paste(client: httpx.AsyncClient, issuer: FakeIssuer, who: str = "ana") -> httpx.Response:
    return await client.post(
        "/recipes/imports/paste", json={"text": PASTED}, headers=issuer.headers(who)
    )


async def link(client: httpx.AsyncClient, issuer: FakeIssuer, who: str = "ana") -> httpx.Response:
    return await client.post(
        "/recipes/imports/link", json={"url": "https://a.example/r"}, headers=issuer.headers(who)
    )


def tokens_today(db: Engine, household_id: str) -> int:
    with db.connect() as conn:
        used = conn.execute(
            text(
                "SELECT input_tokens + output_tokens FROM agent_usage"
                " WHERE household_id = :hh AND day = :day"
            ),
            {"hh": household_id, "day": today_in_sydney()},
        ).scalar()
    return int(used or 0)


async def test_twenty_attempts_an_hour_then_a_clear_429(
    client: httpx.AsyncClient,
    fake_issuer: FakeIssuer,
    reader: ScriptedReader,
    fetcher: ScriptedFetcher,
) -> None:
    await create_household(client, fake_issuer, "ana")
    fetcher.pages["https://a.example/r"] = errors.InvalidInput("That page couldn't be opened.")
    half = MAX_PER_HOUR // 2
    for _ in range(half):  # failed links count: they're attempts
        assert (await link(client, fake_issuer)).status_code == 422
    reader.answers.extend([reading()] * (MAX_PER_HOUR - half))
    for _ in range(MAX_PER_HOUR - half):
        assert (await paste(client, fake_issuer)).status_code == 200

    response = await paste(client, fake_issuer)
    assert response.status_code == 429, response.text
    assert 0 < int(response.headers["retry-after"]) <= 3600
    assert "minutes" in response.json()["detail"] or "minute" in response.json()["detail"]
    assert len(reader.calls) == MAX_PER_HOUR - half  # the 21st never reached the model


async def test_the_limit_is_per_member_and_typing_is_never_limited(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, fetcher: ScriptedFetcher, db: Engine
) -> None:
    home = await create_household(client, fake_issuer, "ana")
    await join(client, fake_issuer, "cat", await invite(client, fake_issuer, "ana"))
    fill_the_hour(db, home, "ana")
    assert (await link(client, fake_issuer, "ana")).status_code == 429

    fetcher.pages["https://a.example/r"] = errors.InvalidInput("That page couldn't be opened.")
    assert (await link(client, fake_issuer, "cat")).status_code == 422  # Cat isn't limited

    body: dict[str, Any] = {
        "title": "Typed ragu",
        "servings": 4,
        "course": "main",
        "lines": [{"raw_text": "500g beef mince"}],
    }
    headers = fake_issuer.headers("ana")
    lines = await client.post("/recipes/lines", json={"lines": ["1 onion"]}, headers=headers)
    saved = await client.post("/recipes/imported", json=body, headers=headers | idem())
    assert (lines.status_code, saved.status_code) == (200, 201)


def fill_the_hour(db: Engine, home: dict[str, Any], who: str, minutes_ago: int = 5) -> None:
    started = utcnow() - timedelta(minutes=minutes_ago)
    with db.begin() as conn:
        member = conn.execute(
            text("SELECT id FROM members WHERE display_name = :who AND household_id = :hh"),
            {"who": who, "hh": home["household"]["id"]},
        ).scalar_one()
        for _ in range(MAX_PER_HOUR):
            conn.execute(
                text(
                    "INSERT INTO recipe_imports (id, member_id, door, started_at)"
                    " VALUES (:id, :m, 'paste', :at)"
                ),
                {"id": uuid.uuid4(), "m": member, "at": started},
            )


async def test_attempts_over_an_hour_old_dont_count(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader, db: Engine
) -> None:
    home = await create_household(client, fake_issuer, "ana")
    fill_the_hour(db, home, "ana", minutes_ago=61)
    reader.answers.append(reading())
    assert (await paste(client, fake_issuer)).status_code == 200


async def test_every_model_call_counts_toward_the_daily_budget(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader, db: Engine
) -> None:
    home = await create_household(client, fake_issuer, "ana")
    hh = home["household"]["id"]
    reader.answers.append(reading())
    assert (await paste(client, fake_issuer)).status_code == 200
    assert tokens_today(db, hh) == 700  # the scripted call: 500 in, 200 out

    # Not a recipe: refused, but the call happened, so it still counts.
    reader.answers.append(reading(found_recipe=False, title="", ingredient_lines=[]))
    assert (await paste(client, fake_issuer)).status_code == 422
    assert tokens_today(db, hh) == 1400


async def test_a_spent_budget_stops_the_model_doors_until_tomorrow(
    client: httpx.AsyncClient,
    fake_issuer: FakeIssuer,
    reader: ScriptedReader,
    fetcher: ScriptedFetcher,
    db: Engine,
) -> None:
    home = await create_household(client, fake_issuer, "ana")
    with db.begin() as conn:  # the agent (or imports) used it all today
        conn.execute(
            text(
                "INSERT INTO agent_usage (household_id, day, input_tokens, output_tokens)"
                " VALUES (:hh, :day, 300000, 0)"
            ),
            {"hh": home["household"]["id"], "day": today_in_sydney()},
        )
    response = await paste(client, fake_issuer)
    assert response.status_code == 429, response.text
    assert "tomorrow" in response.json()["detail"]
    assert 0 < int(response.headers["retry-after"]) <= 24 * 3600
    assert reader.calls == []

    # A link uses no model, so it still works.
    fetcher.pages["https://a.example/r"] = errors.InvalidInput("That page couldn't be opened.")
    assert (await link(client, fake_issuer)).status_code == 422
