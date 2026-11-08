from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://sweep:sweep@localhost:5432/sweep"
    # Origins allowed to call the API from a browser (Expo web dev server by default).
    cors_origins: list[str] = ["http://localhost:8081"]


settings = Settings()
