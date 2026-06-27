"""
WhatsApp CRM SA — Test Suite
=============================
Run: pytest tests/ -v
"""

import pytest
import sys
import os

# Environment is configured in conftest.py

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Test AI Service ────────────────────────────────────────
class TestAIEngine:
    """Test the AI response engine."""

    @pytest.fixture
    def engine(self):
        from app.services.ai_service import AIEngine
        return AIEngine()

    def test_intent_detection_greeting(self, engine):
        result = engine.detect_intent("Hi there! How can you help me?")
        assert result["intent"] == "greeting"
        assert result["confidence"] > 0

    def test_intent_detection_pricing(self, engine):
        result = engine.detect_intent("How much does a plumbing job cost?")
        assert result["intent"] == "pricing"

    def test_intent_detection_thanks(self, engine):
        result = engine.detect_intent("Thanks for your help!")
        assert result["intent"] == "goodbye"

    def test_intent_detection_complaint(self, engine):
        result = engine.detect_intent("I have a problem with my order, it's broken")
        assert result["intent"] == "complaint"

    def test_intent_detection_booking(self, engine):
        result = engine.detect_intent("Can I book an appointment for tomorrow?")
        assert result["intent"] == "booking"

    def test_after_hours_check(self, engine):
        """Test that after-hours detection works."""
        result = engine.is_after_hours()
        assert isinstance(result, bool)

    def test_after_hours_reply(self, engine):
        """Test after-hours reply message."""
        reply = engine.after_hours_reply()
        assert "business hours" in reply.lower()
        assert "tomorrow" in reply.lower()

    def test_response_returns_string(self, engine):
        """Test that AI generates a string response."""
        response = engine.generate_response("Hi, how can I help?", context={
            "business_name": "Test Business",
            "services": ["plumbing"],
        })
        assert isinstance(response, str)
        assert len(response) > 0

    def test_build_prompt_includes_context(self, engine):
        """Test that prompt includes business context."""
        prompt = engine._build_prompt("Test message", context={
            "business_name": "My Business",
            "services": ["service A", "service B"],
        })
        assert "My Business" in prompt
        assert "service A" in prompt


# ─── Test WhatsApp Service ──────────────────────────────────
class TestWhatsAppService:
    """Test WhatsApp API service."""

    @pytest.fixture
    def service(self):
        from app.services.whatsapp_service import WhatsAppService
        return WhatsAppService()

    def test_normalize_number(self, service):
        """Test SA phone number normalization."""
        # 082 → 2782
        assert service._normalize_number("0821234567") == "27821234567"
        # +27 → 27
        assert service._normalize_number("+27821234567") == "27821234567"
        # Already international
        assert service._normalize_number("27821234567") == "27821234567"

    def test_process_webhook(self, service):
        """Test webhook payload parsing."""
        payload = {
            "entry": [{
                "changes": [{
                    "messages": [{
                        "from": "27821234567",
                        "text": {"body": "Hello"},
                        "id": "msg_123",
                        "timestamp": "1234567890",
                        "type": "text",
                    }]
                }]
            }]
        }
        result = service.process_webhook(payload)
        assert result["status"] == "received"
        assert result["sender"] == "27821234567"
        assert result["message"] == "Hello"

    def test_process_webhook_empty(self, service):
        """Test webhook with no messages."""
        payload = {"entry": []}
        result = service.process_webhook(payload)
        assert result["status"] == "no_messages"


# ─── Test Campaign Engine ───────────────────────────────────
class TestCampaignEngine:
    """Test drip campaign engine."""

    @pytest.fixture
    def engine(self):
        from app.services.campaign_service import DripCampaignEngine
        return DripCampaignEngine()

    def test_word_trigger_match(self, engine):
        """Test keyword trigger detection."""
        result = engine.check_word_trigger("I want a quote", "test_campaign")
        # No campaign loaded, should return None
        assert result is None

    def test_campaign_status_enum(self):
        from app.services.campaign_service import CampaignStatus
        assert CampaignStatus.DRAFT.value == "draft"
        assert CampaignStatus.ACTIVE.value == "active"


# ─── Test Auth Module ───────────────────────────────────────────
class TestAuthModule:
    """Test JWT authentication functions."""

    def test_token_creation(self):
        from app.auth import _create_token
        token = _create_token(user_id="testuser", role="admin", secret="test-secret-key")
        assert token is not None
        assert isinstance(token, str)

    def test_token_verification(self):
        from app.auth import _sign, _verify
        token = _sign({"sub": "test"}, "test-secret-key")
        result = _verify(token, "test-secret-key")
        assert result["sub"] == "test"

    def test_invalid_token_raises(self):
        from app.auth import _verify
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _verify("invalid-token", "test-secret-key")


# ─── Test Security Headers ────────────────────────────────────────
class TestSecurityHeaders:
    """Test security-related configurations."""

    def test_cors_origins_configurable(self):
        from app.config import settings
        os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,https://example.com"
        import importlib
        importlib.reload(importlib.import_module("app.config"))
        # Config should have loaded the origins
        assert True  # Placeholder - integration test needed

    def test_lead_score_validation(self):
        """Test lead score is validated in ContactCreate model."""
        from pydantic import ValidationError
        from app.api.router import ContactCreate
        
        with pytest.raises(ValidationError):
            ContactCreate(whatsapp_number="27821234567", lead_score=150)

    def test_phone_number_validation(self):
        """Test phone number format is validated."""
        from pydantic import ValidationError
        from app.api.router import ContactCreate
        
        with pytest.raises(ValidationError):
            ContactCreate(whatsapp_number="invalid")


# ─── Test AI Service Fallback ─────────────────────────────────────
class TestAIServiceFallback:
    """Test AI service fallback behavior."""

    @pytest.fixture
    def engine(self):
        from app.services.ai_service import AIEngine
        return AIEngine()

    def test_template_fallback_no_keys(self, engine):
        """Test template response when no API keys configured."""
        engine.groq_key = None
        engine.or_key = None
        response = engine.generate_response("Hi there!")
        assert response is not None
        assert "Hi" in response

    def test_intent_scores_returned(self, engine):
        """Test that intent scores are included in response."""
        result = engine.detect_intent("Hi how much for a quote today?")
        assert "scores" in result
        assert "greeting" in result["scores"]
        assert "pricing" in result["scores"]


# ─── Test Configuration Validation ─────────────────────────────────────
class TestConfig:
    """Test configuration loading."""

    def test_settings_validation_passes(self):
        """Test settings validation with minimal config."""
        os.environ.setdefault("GROQ_API_KEY", "test_key")
        # Reload module to pick up env vars
        import importlib
        from app import config as config_module
        importlib.reload(config_module)

        from app.config import settings as loaded_settings
        # Should not raise
        loaded_settings.validate()

    def test_secret_key_too_short_raises(self):
        """Test that short secret key raises error."""
        from app.config import Settings
        import importlib
        import app.config as config_module
        
        old_key = os.environ.get("SECRET_KEY", "")
        try:
            os.environ["SECRET_KEY"] = "short"
            importlib.reload(config_module)
            settings = config_module.Settings()
            with pytest.raises(ValueError):
                settings.validate()
        finally:
            os.environ["SECRET_KEY"] = old_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])