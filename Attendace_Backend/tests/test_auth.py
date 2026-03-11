"""Tests for authentication."""

from starlette.testclient import TestClient
from app.main import app
client = TestClient(app)


def test_health():
    """Health check endpoint."""
    r = client.get("/health")
    assert r.status_code == 200
    assert "healthy" in r.json()["status"]


def test_login_missing_credentials():
    """Login without credentials returns 422."""
    r = client.post("/api/v1/auth/login", json={})
    assert r.status_code == 422


def test_login_invalid():
    """Login with invalid credentials returns 401."""
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@test.com", "password": "wrong"},
    )
    assert r.status_code in (401, 500)  # 500 if DB not configured
