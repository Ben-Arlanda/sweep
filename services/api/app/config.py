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
    # Agent evals (slice 8): its own database, so evals never touch dev data.
    eval_database_url: str = "postgresql://sweep:sweep@localhost:5433/sweep_eval"
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
    # The planning agent (slice 5).
    # Haiku since slice 8 (ADR 0018): passed the same Scenarios as Sonnet at ~1/13 the
    # cost. Set AGENT_MODEL=claude-sonnet-5-5 to go back; re-run the evals before
    # changing it either way.
    agent_model: str = "claude-haiku-5-5"
    # How hard it thinks: "medium" (Haiku 5.5's default too), as measured by the slice 8
    # evals. Re-run them before changing it.
    agent_effort: str = "medium"
    # Langfuse tracing (slice 8b, app/tracing.py). Off unless both keys are set; tests
    # force it off with LANGFUSE_TRACING=false so a local .env never sends test traces.
    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"  # EU region
    langfuse_tracing: bool = True
    langfuse_environment: str = "development"
    # Tokens (in + out) one Household may use per day, so one user can't run up the bill.
    agent_daily_token_budget: int = 300_000


settings = Settings()
