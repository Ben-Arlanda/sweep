"""Who is calling? Verifies login tokens (JWTs) from trusted issuers.

This answers authentication only ("who is this?"). Whether they may touch something is
decided in the services, using our own Household and Member tables.

Nothing here is Clerk-specific: any issuer that signs standard RS256 JWTs and publishes
a JWKS (its public keys as JSON) can be added through settings.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import jwt

from app.config import TrustedIssuer

# Only accept the algorithm we expect. Letting the token pick its own algorithm is a
# classic hole: "alg": "none" (no signature) or HS256 signed with our *public* key.
ALLOWED_ALGORITHMS = ["RS256"]
CLOCK_SKEW_SECONDS = 30


@dataclass(frozen=True)
class Identity:
    """A verified caller. Not yet a Member: they may not have a Household."""

    issuer: str
    subject: str


class InvalidToken(Exception):
    pass


class KeySource(Protocol):
    def signing_key(self, token: str) -> Any:
        """Return the public key that should have signed this token."""
        ...


class JwksKeySource:
    """Fetches and caches an issuer's public keys, picking the one named by the token's `kid`."""

    def __init__(self, jwks_url: str) -> None:
        self._client = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)

    def signing_key(self, token: str) -> Any:
        return self._client.get_signing_key_from_jwt(token).key


@dataclass(frozen=True)
class IssuerTrust:
    keys: KeySource
    audience: str | None = None


class TokenVerifier:
    def __init__(self, issuers: Mapping[str, IssuerTrust]) -> None:
        self._issuers = dict(issuers)

    @classmethod
    def from_settings(cls, issuers: list[TrustedIssuer]) -> "TokenVerifier":
        return cls(
            {
                i.issuer: IssuerTrust(keys=JwksKeySource(i.jwks_url), audience=i.audience)
                for i in issuers
            }
        )

    def verify(self, token: str) -> Identity:
        try:
            # Peek at `iss` (unverified!) only to choose which issuer's keys to check with.
            # Nothing from this peek is trusted until the real decode below succeeds.
            unverified_issuer = jwt.decode(token, options={"verify_signature": False}).get("iss")
            trust = self._issuers.get(unverified_issuer) if unverified_issuer else None
            if trust is None:
                raise InvalidToken("Token issuer is not trusted")

            claims = jwt.decode(
                token,
                key=trust.keys.signing_key(token),
                algorithms=ALLOWED_ALGORITHMS,
                issuer=unverified_issuer,
                audience=trust.audience,
                leeway=CLOCK_SKEW_SECONDS,
                options={
                    "require": ["exp", "iat", "iss", "sub"],
                    "verify_aud": trust.audience is not None,
                },
            )
        except jwt.PyJWTError as error:
            raise InvalidToken(str(error)) from error

        return Identity(issuer=claims["iss"], subject=claims["sub"])
