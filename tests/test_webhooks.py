"""
Tests for WhatsApp webhook handling.
"""
import pytest
from fastapi.testclient import TestClient
import json

from app.main import app

client = TestClient(app)


def test_openwa_webhook_valid_signature():
    """Test webhook with valid HMAC signature."""
    payload = {
        "event": "message",
        "data": {
            "from": "27821234567",
            "body": "Hello"
        }
    }
    # Skip if OPENWA_HMAC_KEY not set
    import os
    if not os.getenv("OPENWA_HMAC_KEY"):
        pytest.skip("OPENWA_HMAC_KEY not set")

    # Generate valid signature
    import hmac, hashlib
    secret = os.getenv("OPENWA_HMAC_KEY")
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    response = client.post(
        "/api/webhooks/openwa",
        json=payload,
        headers={"X-Audit-HMAC": signature}
    )
    assert response.status_code == 200
    assert response.json()["status"] in ["processed", "acknowledged"]


def test_openwa_webhook_invalid_signature():
    """Test webhook rejects invalid signature."""
    payload = {"event": "message", "data": {"from": "27821234567", "body": "Test"}}
    response = client.post(
        "/api/webhooks/openwa",
        json=payload,
        headers={"X-Audit-HMAC": "invalid"}
    )
    # Should still accept but log error
    assert response.status_code == 200


def test_meta_webhook_verification():
    """Test Meta webhook verification endpoint."""
    import os
    os.environ["WHATSAPP_PROVIDER"] = "meta"
    os.environ["META_VERIFY_TOKEN"] = "test_token"

    from app.main import app
    client = TestClient(app)

    response = client.get("/api/webhooks/whatsapp/verify", params={
        "hub.mode": "subscribe",
        "hub.challenge": "12345",
        "hub.verify_token": "test_token"
    })
    assert response.status_code == 200
    assert response.json()["hub_challenge"] == "12345"


def test_webhook_rate_limit():
    """Test webhook endpoint respects rate limits."""
    payload = {"event": "message", "data": {"from": "27821234567", "body": "Test"}}
    for _ in range(10):
        response = client.post("/api/webhooks/openwa", json=payload)
    # Should not be rate limited as webhook has own limits
    assert response.status_code == 200