"""Shared test setup.

- A real Postgres test database (`sweep_test`), built by running our Alembic migrations,
  so the migrations themselves are tested on every run.
- A fake login provider: we generate our own RSA key and sign tokens with it, and the
  app trusts that key. The real verification code runs; only the key source differs.
"""

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import jwt
import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import Engine, create_engine, text

from app.auth import IssuerTrust, TokenVerifier
from app.config import Settings
from app.db import Base, sqlalchemy_url
from app.main import create_app

API_DIR = Path(__file__).resolve().parent.parent
TEST_ISSUER = "https://issuer.test"
# Loaded by migrations and shared by every Household; tests must not empty them.
REFERENCE_TABLES = {"ingredients", "ingredient_aliases"}


@dataclass
class StaticKeySource:
    public_key: Any

    def signing_key(self, token: str) -> Any:
        return self.public_key


@dataclass
class FakeIssuer:
    """Signs tokens the way Clerk would, with a key the test app trusts."""

    private_key: rsa.RSAPrivateKey = field(
        default_factory=lambda: rsa.generate_private_key(public_exponent=65537, key_size=2048)
    )
    issuer: str = TEST_ISSUER

    def token(self, subject: str, *, expires_in: timedelta = timedelta(minutes=5)) -> str:
        now = datetime.now(UTC)
        claims = {"iss": self.issuer, "sub": subject, "iat": now, "exp": now + expires_in}
        return jwt.encode(claims, self.private_key, algorithm="RS256")

    def headers(self, subject: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token(subject)}"}

    def verifier(self) -> TokenVerifier:
        keys = StaticKeySource(self.private_key.public_key())
        return TokenVerifier({self.issuer: IssuerTrust(keys=keys)})


@pytest.fixture(scope="session")
def fake_issuer() -> FakeIssuer:
    return FakeIssuer()  # RSA key generation is slow-ish, so once per run


@pytest.fixture(scope="session")
def database_url() -> str:
    """Rebuild the test schema from scratch with Alembic, once per test run."""
    url = Settings().test_database_url
    engine = create_engine(sqlalchemy_url(url))
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    engine.dispose()

    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", sqlalchemy_url(url))
    command.upgrade(config, "head")
    return url


@pytest.fixture
def db(database_url: str) -> Iterator[Engine]:
    """A plain sync connection for arranging and checking data. Empties tables afterwards."""
    engine = create_engine(sqlalchemy_url(database_url))
    yield engine
    tables = ", ".join(
        t.name for t in Base.metadata.sorted_tables if t.name not in REFERENCE_TABLES
    )
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    engine.dispose()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client(
    database_url: str, db: Engine, fake_issuer: FakeIssuer
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(Settings(database_url=database_url), token_verifier=fake_issuer.verifier())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    await app.state.engine.dispose()
