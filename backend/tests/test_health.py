from fastapi.testclient import TestClient

from app.main import app, settings

client = TestClient(app)


def test_health_check_returns_ready_status() -> None:
    """Return a ready status from the public health endpoint.

    Returns:
        None.
    """
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "avscout-api",
        "environment": settings.app_env,
    }
