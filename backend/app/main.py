"""HTTP entrypoint for the AVScout backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings

settings = get_settings()
app = FastAPI(title="AVScout API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Report whether the API process is ready to receive requests."""

    return {
        "status": "ok",
        "service": "avscout-api",
        "environment": settings.app_env,
    }
