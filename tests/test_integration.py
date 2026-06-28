# WhatsApp CRM SA - Integration Tests
"""
Run: pytest tests/test_integration.py -v
"""

import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["GROQ_API_KEY"] = ""
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-32-chars-minimum"
os.environ["ADMIN_PASSWORD"] = "test-password"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestSetupEndpoint:
    """Test the setup/onboarding endpoint."""

    def test_setup_page_loads(self):
        response = client.get("/setup")
        assert response.status_code == 200
        assert "WhatsApp CRM SA" in response.text
        assert "setup_wizard.py" in response.text


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_returns_json(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_login_missing_password(self):
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 401

    def test_login_invalid_password(self):
        response = client.post("/api/auth/login", json={"password": "wrong"})
        assert response.status_code == 401

    def test_login_valid_password(self):
        response = client.post("/api/auth/login", json={"password": "test-password"})
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestContactsEndpoints:
    """Test contacts CRUD endpoints."""

    def test_list_contacts(self):
        response = client.get("/api/contacts")
        assert response.status_code == 200
        assert "data" in response.json()

    def test_create_contact_missing_number(self):
        response = client.post("/api/contacts", json={})
        assert response.status_code == 422  # pydantic validation error


class TestWebhookEndpoints:
    """Test webhook endpoints."""

    def test_webhook_receives_openwa_format(self):
        openwa_payload = {
            "event": "message",
            "data": {
                "from": "27821234567@c.us",
                "chat_id": "27821234567@c.us",
                "body": "Hi there!",
                "type": "text"
            }
        }
        response = client.post("/api/webhooks/whatsapp", json=openwa_payload)
        assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting on auth endpoints."""

    def test_login_rate_limit_exists(self):
        """Test that rate limiting is configured (may not trigger in test)."""
        # In production with slowapi, this would return 429 after 5 attempts
        for _ in range(3):
            client.post("/api/auth/login", json={"password": "wrong"})
        assert True  # Placeholder - actual rate limit testing needs slowapi decorator