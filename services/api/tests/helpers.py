"""Small API helpers so tests read like the user journey."""

from typing import Any

import httpx

from tests.conftest import FakeIssuer


async def create_household(
    client: httpx.AsyncClient, issuer: FakeIssuer, subject: str, name: str = "Home"
) -> dict[str, Any]:
    response = await client.post(
        "/households",
        json={"name": name, "display_name": subject},
        headers=issuer.headers(subject),
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def invite(client: httpx.AsyncClient, issuer: FakeIssuer, owner: str) -> str:
    response = await client.post("/households/current/invites", headers=issuer.headers(owner))
    assert response.status_code == 201, response.text
    code: str = response.json()["code"]
    return code


async def join(
    client: httpx.AsyncClient, issuer: FakeIssuer, subject: str, code: str
) -> httpx.Response:
    return await client.post(
        f"/invites/{code}/accept",
        json={"display_name": subject},
        headers=issuer.headers(subject),
    )


async def member_ids(client: httpx.AsyncClient, issuer: FakeIssuer, subject: str) -> list[str]:
    response = await client.get("/households/current", headers=issuer.headers(subject))
    assert response.status_code == 200, response.text
    return [m["id"] for m in response.json()["members"]]
