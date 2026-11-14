"""Authentication: only correctly signed, unexpired tokens from trusted issuers get in."""

import json
from datetime import timedelta

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.utils import base64url_encode

from tests.conftest import FakeIssuer

pytestmark = pytest.mark.anyio


async def test_missing_token_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.get("/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_garbage_token_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.get("/me", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401


async def test_expired_token_is_rejected(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    token = fake_issuer.token("user_1", expires_in=timedelta(minutes=-5))

    response = await client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


async def test_token_from_untrusted_issuer_is_rejected(client: httpx.AsyncClient) -> None:
    impostor = FakeIssuer(issuer="https://evil.test")

    response = await client.get("/me", headers=impostor.headers("user_1"))

    assert response.status_code == 401


async def test_token_signed_with_wrong_key_is_rejected(client: httpx.AsyncClient) -> None:
    # Right issuer name, but signed by someone else's private key.
    forger = FakeIssuer(private_key=rsa.generate_private_key(public_exponent=65537, key_size=2048))

    response = await client.get("/me", headers=forger.headers("user_1"))

    assert response.status_code == 401


async def test_unsigned_token_is_rejected(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    # Hand-built "alg: none" token: header.payload. with an empty signature.
    def part(data: dict[str, object]) -> str:
        return base64url_encode(json.dumps(data).encode()).decode()

    claims = {"iss": fake_issuer.issuer, "sub": "user_1", "iat": 0, "exp": 9999999999}
    unsigned = f"{part({'alg': 'none', 'typ': 'JWT'})}.{part(claims)}."

    response = await client.get("/me", headers={"Authorization": f"Bearer {unsigned}"})

    assert response.status_code == 401


async def test_valid_token_without_household_gets_not_in_household(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    response = await client.get("/me", headers=fake_issuer.headers("user_1"))

    assert response.status_code == 403
    assert response.json()["code"] == "not_in_household"
