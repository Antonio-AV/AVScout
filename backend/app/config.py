"""Runtime configuration for the API."""

from dataclasses import dataclass
from os import environ

from dotenv import load_dotenv

load_dotenv()


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_env: str
    api_host: str
    api_port: int
    cors_origins: list[str]
    database_path: str
    openai_api_key: str | None
    openai_model: str


def get_settings() -> Settings:
    """Build settings from environment variables with local defaults."""

    return Settings(
        app_env=environ.get("APP_ENV", "development"),
        api_host=environ.get("API_HOST", "0.0.0.0"),
        api_port=int(environ.get("API_PORT", "8000")),
        cors_origins=_csv(environ.get("CORS_ORIGINS", "http://localhost:3000")),
        database_path=environ.get("DATABASE_PATH", "data/avscout.duckdb"),
        openai_api_key=environ.get("OPENAI_API_KEY") or None,
        openai_model=environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
    )
