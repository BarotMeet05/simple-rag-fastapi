# tests/test_health.py
"""
Health Endpoint Tests
=====================
These tests verify the /health endpoint returns the expected shape and values.

Testing philosophy for health checks:
- Don't test that Python works (e.g., "2 + 2 == 4")
- DO test your specific contract: what fields are in the response?
- DO test error conditions: what happens when a dependency is down?
  (We'll add dependency health checks in Phase 2)
"""

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    """Health check must return HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_has_required_fields(client: TestClient) -> None:
    """Health response must contain all expected fields."""
    response = client.get("/health")
    body = response.json()

    assert "status" in body
    assert "service" in body
    assert "version" in body
    assert "environment" in body
    assert "timestamp" in body


def test_health_status_is_ok(client: TestClient) -> None:
    """Status field must be 'ok' when the service is healthy."""
    response = client.get("/health")
    assert response.json()["status"] == "ok"


def test_health_timestamp_is_iso8601(client: TestClient) -> None:
    """Timestamp must be a parseable ISO 8601 datetime string."""
    from datetime import datetime

    response = client.get("/health")
    timestamp_str = response.json()["timestamp"]

    # This will raise ValueError if not parseable — which becomes a test failure
    dt = datetime.fromisoformat(timestamp_str)
    assert dt is not None


def test_health_content_type_is_json(client: TestClient) -> None:
    """Response Content-Type must be application/json."""
    response = client.get("/health")
    assert "application/json" in response.headers["content-type"]
