from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TrustedIssuer(BaseModel):
    """A login provider whose tokens we accept (Clerk today; more can be added as config)."""

    issuer: str  # must match the token's `iss` claim exactly
    jwks_url: str  # where the issuer publishes its public signing keys
    audience: str | None = None  # checked against `aud` when set


class Settings(BaseSettings):
    """App settings, read from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://sweep:sweep@localhost:5433/sweep"
    test_database_url: str = "postgresql://sweep:sweep@localhost:5433/sweep_test"
    # Origins allowed to call the API from a browser (Expo web dev server by default).
    cors_origins: list[str] = ["http://localhost:8081"]
    # JSON list, e.g. AUTH_ISSUERS='[{"issuer": "https://x.clerk.accounts.dev",
    #   "jwks_url": "https://x.clerk.accounts.dev/.well-known/jwks.json"}]'
    auth_issuers: list[TrustedIssuer] = []

    # AI providers. Without a key the feature that needs it is switched off, not broken:
    # tests and CI run with fakes and no keys at all.
    anthropic_api_key: SecretStr | None = None
    voyage_api_key: SecretStr | None = None
    # Small, fast model for reading ingredient lines the rules couldn't (plan §8).
    parsing_model: str = "claude-haiku-5-5"
    # Reviews draft Seed Recipes (slice 4c). Start small; the eval decides if it's enough.
    review_model: str = "claude-haiku-5-5"
    embedding_model: str = "voyage-3.5"


settings = Settings()
