"""
Tests for AI service.
"""
import pytest
from unittest.mock import patch, MagicMock
import os

from app.services.ai_service import AIEngine


class TestAIEngine:
    """Test cases for AIEngine class."""

    def setup_method(self):
        """Setup test environment."""
        os.environ["GROQ_API_KEY"] = "test_groq_key"
        os.environ["OPENROUTER_API_KEY"] = "test_or_key"
        os.environ["AI_PROVIDER"] = "auto"
        os.environ["BUSINESS_HOURS_START"] = "8"
        os.environ["BUSINESS_HOURS_END"] = "18"
        os.environ["AUTO_REPLY_ENABLED"] = "true"
        os.environ["MESSAGE_DELAY_MIN"] = "1"
        os.environ["AUTO_REPLY_TYPING_DELAY"] = "2"

    def test_detect_intent_greeting(self):
        """Test intent detection for greetings."""
        engine = AIEngine()
        intent = engine.detect_intent("Hello there!")
        assert intent["intent"] == "greeting"
        assert intent["confidence"] > 0

    def test_detect_intent_pricing(self):
        """Test intent detection for pricing queries."""
        engine = AIEngine()
        intent = engine.detect_intent("How much does it cost?")
        assert intent["intent"] == "pricing"
        assert intent["confidence"] > 0

    def test_detect_intent_availability(self):
        """Test intent detection for availability."""
        engine = AIEngine()
        intent = engine.detect_intent("Is this available?")
        assert intent["intent"] == "availability"

    def test_detect_intent_complaint(self):
        """Test intent detection for complaints."""
        engine = AIEngine()
        intent = engine.detect_intent("This is broken!")
        assert intent["intent"] == "complaint"

    def test_is_after_hours_business_hours(self):
        """Test after hours detection during business hours."""
        engine = AIEngine()
        # Mock current time to be during business hours
        with patch("app.services.ai_service.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 12
            assert engine.is_after_hours() is False

    def test_is_after_hours_outside_hours(self):
        """Test after hours detection outside business hours."""
        engine = AIEngine()
        with patch("app.services.ai_service.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 20
            assert engine.is_after_hours() is True

    @patch("app.services.ai_service.httpx.Client")
    def test_generate_response_groq_success(self, mock_client):
        """Test successful Groq API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        engine = AIEngine()
        response = engine.generate_response("Hello", {"business_name": "Test Co"})
        assert response == "Test response"
        assert engine.request_counts["groq"] == 1

    @patch("app.services.ai_service.httpx.Client")
    def test_generate_response_groq_fallback(self, mock_client):
        """Test fallback to OpenRouter when Groq fails."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        # Second call succeeds on OpenRouter
        mock_or_response = MagicMock()
        mock_or_response.status_code = 200
        mock_or_response.json.return_value = {
            "choices": [{"message": {"content": "Fallback response"}}]
        }

        # Need to mock both calls
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_response
            return mock_or_response

        mock_client.return_value.__enter__.return_value.post.side_effect = side_effect

        engine = AIEngine()
        response = engine.generate_response("Hello", {"business_name": "Test Co"})
        assert response == "Fallback response"
        assert engine.request_counts["openrouter"] == 1

    def test_template_response_fallback(self):
        """Test template fallback when both APIs fail."""
        engine = AIEngine()
        engine.groq_key = ""
        engine.or_key = ""
        response = engine.generate_response("Hello there!")
        assert "help" in response.lower() or "hi" in response.lower()

    def test_after_hours_reply(self):
        """Test after hours auto-reply message."""
        engine = AIEngine()
        reply = engine.after_hours_reply()
        assert "business hours" in reply.lower()
        assert "tomorrow" in reply.lower()

    def test_system_prompt_content(self):
        """Test system prompt contains SA-specific guidelines."""
        engine = AIEngine()
        prompt = engine._system_prompt()
        assert "South African" in prompt
        assert "WhatsApp CRM" in prompt