"""Smoke tests for the eventing service scaffold."""

from fastapi.testclient import TestClient

from messaging.main import app


def test_health() -> None:
    """Health endpoint should respond with the service identity."""
    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "eventing"}
