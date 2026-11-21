"""The gap report (ADR 0032): foods recipes keep adding that Sweep should learn."""

import httpx
import pytest

from app import gap_report
from app.db import make_engine, make_sessionmaker
from tests.conftest import FakeIssuer
from tests.helpers import create_household, idem

pytestmark = pytest.mark.anyio


async def import_lines(
    client: httpx.AsyncClient, issuer: FakeIssuer, who: str, lines: list[str]
) -> None:
    body = {
        "title": "Gumbo",
        "servings": 4,
        "course": "main",
        "lines": [{"raw_text": t} for t in lines],
    }
    saved = await client.post("/recipes/imported", json=body, headers=issuer.headers(who) | idem())
    assert saved.status_code == 201, saved.text


async def test_lists_new_foods_three_households_added_with_their_diet_verdict(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, database_url: str
) -> None:
    for who in ("ana", "ben", "cat"):
        await create_household(client, fake_issuer, who, name=f"{who}'s")
        await import_lines(client, fake_issuer, who, ["200 g andouille sausage", "1 onion"])
    for who in ("ana", "ben"):  # only two: not listed, it could identify a Household
        await import_lines(client, fake_issuer, who, ["1 tsp glorp"])
    await import_lines(client, fake_issuer, "ana", ["50 g andouille sausage"])  # counted once

    engine = make_engine(database_url)
    async with make_sessionmaker(engine)() as session:
        gaps = await gap_report.gaps(session)
    await engine.dispose()

    assert gaps == [
        gap_report.Gap(
            name="andouille sausage",
            households=3,
            held_back=["vegetarian", "vegan"],
            check_label=["gluten free"],
        )
    ]
    assert gap_report.line(gaps[0]) == (
        "andouille sausage: 3 Households · held back: vegetarian, vegan"
        " · check the label: gluten free"
    )
