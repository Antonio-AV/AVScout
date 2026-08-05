"""Runtime configuration for the API."""

from dataclasses import dataclass
from os import environ

from dotenv import load_dotenv

load_dotenv()


def _csv(value: str) -> list[str]:
    """Parse a comma-separated environment value.

    Args:
        value: Comma-separated string to parse.

    Returns:
        A list of trimmed, non-empty values.
    """
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Runtime settings used by the FastAPI application.

    Attributes:
        app_env: Name of the current application environment.
        api_host: Host interface used by the API server.
        api_port: Port used by the API server.
        cors_origins: Browser origins allowed to call the API.
        database_path: Path to the local analytical database.
        openai_api_key: Optional backend-only OpenAI credential.
        openai_model: OpenAI model identifier used by later features.
    """

    app_env: str
    api_host: str
    api_port: int
    cors_origins: list[str]
    database_path: str
    openai_api_key: str | None
    openai_model: str


def get_settings() -> Settings:
    """Build settings from environment variables with local defaults.

    Returns:
        A frozen ``Settings`` instance populated from the process environment.

    Raises:
        ValueError: If ``API_PORT`` is not a valid integer.
    """

    return Settings(
        app_env=environ.get("APP_ENV", "development"),
        api_host=environ.get("API_HOST", "0.0.0.0"),
        api_port=int(environ.get("API_PORT", "8000")),
        cors_origins=_csv(environ.get("CORS_ORIGINS", "http://localhost:3000")),
        database_path=environ.get("DATABASE_PATH", "data/avscout.duckdb"),
        openai_api_key=environ.get("OPENAI_API_KEY") or None,
        openai_model=environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
    )
