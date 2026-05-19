"""
WhatsApp CRM SA — WhatsApp API Service
=======================================
Handles all WhatsApp Business API interactions.
Supports Meta Business API and Twilio.
"""

import time
import json
import hmac
import hashlib
import logging
from typing import Optional, Dict, Any

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class WhatsAppServiceError(Exception):
    pass


class WhatsAppService:
    """Handles all WhatsApp Business API operations."""

    def __init__(self):
        self.provider = settings.WHATSAPP_PROVIDER

        if self.provider == "meta":
            self.base_url = "https://graph.facebook.com/v18.0"
            self.phone_number_id = settings.META_PHONE_NUMBER_ID
            self.access_token = settings.META_ACCESS_TOKEN
        elif self.provider == "twilio":
            self.base_url = "https://api.twilio.com/2010-04-01"
            self.account_sid = settings.TWILIO_ACCOUNT_SID
            self.auth_token = settings.TWILIO_AUTH_TOKEN
            self.from_number = settings.TWILIO_WHATSAPP_FROM

        self._rate_limit_remaining = 1000
        self._rate_limit_reset = time.time()

    def _check_rate_limit(self):
        now = time.time()
        if now > self._rate_limit_reset:
            self._rate_limit_remaining = 1000
            self._rate_limit_reset = now + 60
        if self._rate_limit_remaining <= 0:
            wait = self._rate_limit_reset - now
            logger.warning("Rate limited. Waiting %.1fs", wait)
            time.sleep(max(wait, 1))
            self._rate_limit_remaining = 1000
            self._rate_limit_reset = time.time() + 60
        self._rate_limit_remaining -= 1

    def send_text(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send a plain text message."""
        payload = {"type": "text", "text": {"body": message}}
        return self.send_message(to_number, payload)

    def send_message(self, to_number: str, content: Dict) -> Dict[str, Any]:
        """Send a message via the configured WhatsApp provider."""
        self._check_rate_limit()

        if self.provider == "meta":
            return self._send_meta(to_number, content)
        elif self.provider == "twilio":
            return self._send_twilio(to_number, content)
        else:
            raise WhatsAppServiceError(f"Unknown provider: {self.provider}")

    def _normalize_number(self, to_number: str) -> str:
        """Normalize SA phone numbers to international format."""
        cleaned = to_number.strip().lstrip("+")
        if cleaned.startswith("0") and not cleaned.startswith("00"):
            cleaned = "27" + cleaned[1:]
        elif not cleaned.startswith("27"):
            cleaned = "27" + cleaned.lstrip("0")
        return cleaned

    def _send_meta(self, to_number: str, content: Dict) -> Dict[str, Any]:
        """Send via Meta Business API."""
        url = "{}/{}".format(self.base_url, self.phone_number_id) + "/messages"
        headers = {
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json",
        }

        to_clean = self._normalize_number(to_number)
        payload = {
            "messaging_product": "whatsapp",
            "to": to_clean,
            "type": content.get("type", "text"),
        }

        msg_type = content.get("type", "text")
        if msg_type == "text":
            payload["text"] = {"body": content["text"]["body"]}
        elif msg_type == "template":
            payload["template"] = content["template"]
        elif msg_type == "interactive":
            payload["interactive"] = content["interactive"]
        elif msg_type == "image":
            payload["image"] = content["image"]

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            logger.info("Meta message sent to %s, status: %s", to_clean, resp.status_code)
            return {"success": True, "provider": "meta", "response": resp.json()}
        except requests.RequestException as e:
            logger.error("Meta send failed: %s", e)
            return {"success": False, "error": str(e)}

    def _send_twilio(self, to_number: str, content: Dict) -> Dict[str, Any]:
        """Send via Twilio WhatsApp API."""
        from twilio.rest import Client

        client = Client(self.account_sid, self.auth_token)
        to_clean = self._normalize_number(to_number)

        try:
            if content.get("type", "text") == "text":
                message = client.messages.create(
                    body=content["text"]["body"],
                    from_=self.from_number,
                    to="whatsapp:" + to_clean,
                )
                return {"success": True, "provider": "twilio", "sid": message.sid}
            else:
                raise WhatsAppServiceError("Twilio only supports text messages in this version")
        except Exception as e:
            logger.error("Twilio send failed: %s", e)
            return {"success": False, "error": str(e)}

    def verify_webhook(self, mode: str, token: str, verify_token: str) -> tuple:
        """Verify WhatsApp webhook (Meta)."""
        if mode == "subscribe" and token == verify_token:
            return True, 200
        return False, 403

    def process_webhook(self, payload: Dict) -> Dict:
        """Process an incoming WhatsApp webhook event."""
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            messages = changes.get("messages", [])

            if not messages:
                return {"status": "ignored"}

            for msg in messages:
                sender = msg.get("from", "")
                message = msg.get("text", {}).get("body", "")
                message_id = msg.get("id", "")
                timestamp = msg.get("timestamp", "")
                message_type = msg.get("type", "text")

                return {
                    "status": "received",
                    "sender": sender,
                    "message": message,
                    "message_id": message_id,
                    "message_type": message_type,
                    "timestamp": timestamp,
                }

            return {"status": "no_messages"}

        except (KeyError, IndexError) as e:
            logger.error("Webhook parse error: %s", e)
            return {"status": "error", "error": str(e)}