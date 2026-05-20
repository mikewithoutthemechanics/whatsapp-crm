"""
WhatsApp CRM SA — WhatsApp API Service
=======================================
Handles all WhatsApp interactions via three providers:
  • openwa  — Open Source WhatsApp API Gateway (rmyndharis/OpenWA)
  • meta    — Meta Business API
  • twilio  — Twilio WhatsApp

OpenWA is the RECOMMENDED default for SA SMMEs — free, self-hosted,
no Meta approval needed, no per-message fees.
"""

import time
import json
import hmac
import hashlib
import logging
import base64
from typing import Optional, Dict, Any

import requests

from app.config import settings

logger = logging.getLogger(__name__)


# ─── Exceptions ──────────────────────────────────────────────

class WhatsAppServiceError(Exception):
    """Raised when any WhatsApp operation fails."""
    pass


# ─── Provider factory ────────────────────────────────────────

def _make_service():
    """Return the WhatsApp service for the configured provider."""
    provider = settings.WHATSAPP_PROVIDER.lower()
    if provider == "openwa":
        return OpenWAService()
    elif provider == "meta":
        return MetaWhatsAppService()
    elif provider == "twilio":
        return TwilioWhatsAppService()
    else:
        raise WhatsAppServiceError(
            f"Unknown WhatsApp provider '{provider}'. "
            f"Choose: openwa | meta | twilio"
        )


# ─── Base (shared helpers) ───────────────────────────────────

class _BaseService:
    """Shared helpers used by all provider implementations."""

    @staticmethod
    def _normalize_number(to_number: str) -> str:
        """
        Normalise SA phone numbers to international E.164 format.

        Examples:
            082 123 4567  →  27821234567
            21234567       →  27821234567
            +27821234567   →  27821234567
        """
        cleaned = to_number.strip().lstrip("+")
        # Remove spaces, dashes, parentheses
        import re
        cleaned = re.sub(r"[\s\-\(\)]", "", cleaned)
        if cleaned.startswith("0"):
            cleaned = "27" + cleaned[1:]
        elif not cleaned.startswith("27"):
            cleaned = "27"
        return cleaned

    @staticmethod
    def _format_openwa_id(number: str) -> str:
        """Format for OpenWA REST API: <number>@c.us (without the 27 country code prefix)."""
        n = number.lstrip("+")
        # Drop the leading '27' country code for openwa number@c.us format
        if n.startswith("27"):
            n = n[2:]
        return f"{n}@c.us"

    @staticmethod
    def _parse_openwa_id(wa_id: str) -> str:
        """Convert openwa chat ID (e.g. 27821234567@c.us or 821234567@c.us) to E.164."""
        return wa_id.replace("@c.us", "")

    @staticmethod
    def _text_content(message: str) -> dict:
        return {"type": "text", "text": {"body": message}}


# ─── OpenWA provider ─────────────────────────────────────────

class OpenWAService(_BaseService):
    """
    OpenWA REST API integration.

    OpenWA (rmyndharis/OpenWA) exposes a self-hosted WhatsApp gateway
    on http://localhost:2785 with:
      POST  /api/message         → send text / media
      POST  /api/message/media   → send image/doc
      DELETE /api/message/<id>   → delete
      POST  /api/chat/read       → mark read
      POST  /api/status          → change presence
      GET   /api/chats           → list conversations
      GET   /api/chats/<id>/messages  → get messages
      GET   /api/contacts        → list contacts

    Audit HMAC (X-Audit-HMAC) header is sent alongside every request
    so OpenWA can verify authenticity.
    """

    API_BASE: str = "/api"   # set from settings

    def __init__(self):
        self.base_url = settings.OPENWA_API_URL.rstrip("/")
        self.api_key   = settings.OPENWA_API_KEY
        self.session   = settings.OPENWA_SESSION_ID          # named session in OpenWA
        self.hmac_key  = settings.OPENWA_HMAC_KEY or ""
        self._timeout  = settings.OPENWA_TIMEOUT or 30
        self._session  = requests.Session()
        self._session.headers.update({
            "x-api-key":      self.api_key,
            "Content-Type":   "application/json",
            "Accept":         "application/json",
        })
        self._last_sent: Optional[str] = None

    # ── helpers ───────────────────────────────────────────────

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _audit_hmac(self, payload: dict) -> str:
        if not self.hmac_key:
            return ""
        body = json.dumps(payload or {}, sort_keys=True)
        return hmac.new(
            self.hmac_key.encode(), body.encode(), hashlib.sha256
        ).hexdigest()

    def _post(self, path: str, payload: dict) -> dict:
        headers = {}
        if self.hmac_key:
            headers["X-Audit-HMAC"] = self._audit_hmac(payload)
        try:
            resp = self._session.post(
                self._url(path),
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("OpenWA POST %s → %s", path, resp.status_code)
            return data
        except requests.HTTPError as e:
            logger.error("OpenWA %s HTTP error: %s — %s", path, e, getattr(e.response, "text", ""))
            raise WhatsAppServiceError(f"OpenWA {path} failed ({e.response.status_code}): {e.response.text}")
        except requests.RequestException as e:
            logger.error("OpenWA %s request error: %s", path, e)
            raise WhatsAppServiceError(f"OpenWA {path} network error: {e}")

    # ── public API ─────────────────────────────────────────────

    def send_text(self, to_number: str, message: str) -> Dict[str, Any]:
        to = self._normalize_number(to_number)
        chat_id = self._format_openwa_id(to)
        # OpenWA sends to <number>@c.us when session is a personal number
        payload = {
            "session":  self.session,
            "chatId":   chat_id,
            "content":  message,
            "type":     "text",
        }
        result = self._post("/api/message", payload)
        self._last_sent = to
        return {
            "success":    True,
            "provider":   "openwa",
            "to":         to,
            "message_id": result.get("id", ""),
            "response":   result,
        }

    def send_message(
        self,
        to_number: str,
        content:   Dict[str, Any],
    ) -> Dict[str, Any]:
        msg_type = content.get("type", "text")
        to       = self._normalize_number(to_number)
        chat_id  = self._format_openwa_id(to)

        if msg_type == "text":
            return self.send_text(to_number, content["text"]["body"])

        if msg_type == "image":
            media_url = content["image"].get("link", "") if isinstance(content.get("image"), dict) else content.get("image", "")
            payload = {
                "session": self.session,
                "chatId":  chat_id,
                "type":    "image",
                "content": media_url,
            }
            result = self._post("/api/message/media", payload)
            return {"success": True, "provider": "openwa", "file_id": result.get("id", ""), "response": result}

        if msg_type == "document":
            media_url = content["document"].get("link", "") if isinstance(content.get("document"), dict) else ""
            payload = {
                "session": self.session,
                "chatId":  chat_id,
                "type":    "document",
                "content": media_url,
            }
            result = self._post("/api/message/media", payload)
            return {"success": True, "provider": "openwa", "file_id": result.get("id", ""), "response": result}

        raise WhatsAppServiceError(
            f"OpenWA message type '{msg_type}' not yet implemented in this version."
        )

    # ── receive / webhook ──────────────────────────────────────

    def process_webhook(self, payload: Dict) -> Dict:
        """
        Convert OpenWA webhook payload into the CRM's standard format.

        OpenWA sends:
          { "event": "message", "data": { "from": "...@c.us", "chat_id": "...@c.us",
                                           "body": "...", "type": "text" } }
        """
        event = payload.get("event", "")

        if event == "message":
            data = payload.get("data", {})
            sender_raw = data.get("from", data.get("chat_id", ""))
            sender = self._parse_openwa_id(sender_raw)
            message_type = data.get("type", "text")

            attachments = data.get("media", {})

            return {
                "status":        "received",
                "sender":        sender,
                "sender_name":   data.get("pushName", ""),
                "message":       data.get("body", ""),
                "message_id":    data.get("id", ""),
                "message_type":  message_type,
                "timestamp":     data.get("timestamp", ""),
                "group":         payload.get("group", False),
                "attachments":   attachments,
                "raw_event":     payload,
                "provider":      "openwa",
            }

        if event in ("status_update", "state"):
            return {
                "status":   "status_update",
                "state":    payload.get("data", {}).get("state", ""),
                "provider": "openwa",
            }

        if event == "chat_opened":
            return {
                "status":   "chat_opened",
                "chat_id":  self._parse_openwa_id(payload.get("data", {}).get("chat_id", "")),
                "provider": "openwa",
            }

        return {"status": "ignored", "event": event, "provider": "openwa"}

    # ── chat & contact helpers ──────────────────────────────────

    def get_chats(self, limit: int = 50, offset: int = 0) -> list:
        """Fetch list of conversations from OpenWA."""
        payload = {"session": self.session, "limit": limit, "offset": offset}
        result = self._post("/api/chats", payload)
        return result.get("chats", [])

    def get_chat_messages(
        self, chat_id: str, limit: int = 30, offset: int = 0
    ) -> list:
        """Fetch messages for a specific chat."""
        payload = {
            "session":  self.session,
            "chatId":   self._format_openwa_id(chat_id),
            "limit":    limit,
            "offset":   offset,
        }
        result = self._post(f"/api/chats/{self._format_openwa_id(chat_id)}/messages", payload)
        return result.get("messages", [])

    def get_contacts(self, limit: int = 100, offset: int = 0) -> list:
        """Fetch contacts from OpenWA."""
        payload = {"session": self.session, "limit": limit, "offset": offset}
        result = self._post("/api/contacts", payload)
        return result.get("contacts", [])

    def mark_read(self, chat_id: str, message_ids: Optional[list] = None) -> Dict:
        """Mark messages as read."""
        payload = {
            "session":  self.session,
            "chatId":   self._format_openwa_id(chat_id),
            "read":     True,
        }
        if message_ids:
            payload["messageIds"] = message_ids
        result = self._post("/api/chat/read", payload)
        return {"success": True, "provider": "openwa", "response": result}

    def set_presence(self, presence: str) -> Dict:
        """
        Set WhatsApp presence.

        Args:
            presence: available | unavailable | composing | recording
        """
        valid = {"available", "unavailable", "composing", "recording"}
        if presence not in valid:
            raise WhatsAppServiceError(
                f"Invalid presence '{presence}'. Must be one of: {valid}"
            )
        payload = {"session": self.session, "presence": presence}
        result = self._post("/api/status", payload)
        return {"success": True, "provider": "openwa", "presence": presence}

    def health(self) -> Dict[str, Any]:
        """Check if the OpenWA gateway is reachable."""
        try:
            resp = self._session.get(f"{self.base_url}/health", timeout=5)
            return {
                "healthy":    resp.status_code == 200,
                "status":     resp.status_code,
                "provider":   "openwa",
                "gateway_url": self.base_url,
                "session":    self.session,
            }
        except requests.RequestException as e:
            return {"healthy": False, "provider": "openwa", "error": str(e)}


# ─── Meta Business API provider ───────────────────────────────

class MetaWhatsAppService(_BaseService):
    """Send/receive via Meta WhatsApp Business Cloud API."""

    def __init__(self):
        self.base_url       = f"https://graph.facebook.com/v18.0"
        self.phone_number_id = settings.META_PHONE_NUMBER_ID
        self.access_token    = settings.META_ACCESS_TOKEN
        self._request_session = requests.Session()
        self._request_session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type":  "application/json",
        })

    def _send_meta(self, to_number: str, content: Dict) -> Dict:
        url    = f"{self.base_url}/{self.phone_number_id}/messages"
        to_clean = self._normalize_number(to_number)
        payload = {
            "messaging_product": "whatsapp",
            "to": to_clean,
            "type": content.get("type", "text"),
        }
        if content.get("type") == "text":
            payload["text"] = {"body": content["text"]["body"]}
        elif content.get("type") == "template":
            payload["template"] = content["template"]
        elif content.get("type") == "image":
            payload["image"] = {"link": content["image"]["link"]}
        try:
            resp = self._request_session.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            return {"success": True, "provider": "meta", "response": resp.json()}
        except requests.RequestException as exc:
            return {"success": False, "error": str(exc)}

    def send_text(self, to_number: str, message: str) -> Dict:
        return self._send_meta(to_number, self._text_content(message))

    def send_message(self, to_number: str, content: Dict) -> Dict:
        return self._send_meta(to_number, content)

    def verify_webhook(self, mode: str, token: str, verify_token: str) -> tuple:
        if mode == "subscribe" and token == verify_token:
            return True, 200
        return False, 403

    def process_webhook(self, payload: Dict) -> Dict:
        try:
            entry   = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            messages = changes.get("messages", [])
            if not messages:
                return {"status": "ignored"}
            for msg in messages:
                return {
                    "status":       "received",
                    "sender":       msg.get("from", ""),
                    "message":      msg.get("text", {}).get("body", ""),
                    "message_id":   msg.get("id", ""),
                    "message_type": msg.get("type", "text"),
                    "timestamp":    msg.get("timestamp", ""),
                    "provider":     "meta",
                }
            return {"status": "no_messages"}
        except (KeyError, IndexError) as exc:
            return {"status": "error", "error": str(exc)}


# ─── Twilio provider ──────────────────────────────────────────

class TwilioWhatsAppService(_BaseService):
    """Send/receive via Twilio WhatsApp Business API."""

    def __init__(self):
        try:
            from twilio.rest import Client as TwilioClient   # imported lazily
            self._Client = TwilioClient
        except ImportError:
            self._Client = None

        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token  = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_WHATSAPP_FROM

    def _client(self):
        if not self._Client:
            raise WhatsAppServiceError(
                "twilio package not installed. Add 'twilio>=8' to requirements.txt"
            )
        return self._Client(self.account_sid, self.auth_token)

    def send_text(self, to_number: str, message: str) -> Dict:
        client = self._client()
        to_clean = self._normalize_number(to_number)
        try:
            msg = client.messages.create(
                body=message,
                from_=self.from_number,
                to=f"whatsapp:{to_clean}",
            )
            return {"success": True, "provider": "twilio", "sid": msg.sid}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def send_message(self, to_number: str, content: Dict) -> Dict:
        if content.get("type") != "text":
            raise WhatsAppServiceError("Twilio text-only in this version")
        return self.send_text(to_number, content["text"]["body"])

    def process_webhook(self, payload: Dict) -> Dict:
        from_number = payload.get("From",          "")
        body        = payload.get("Body",          "")
        msg_sid     = payload.get("MessageSid",     "")
        msg_type    = payload.get("NumMedia", "0")
        media_items = []
        for i in range(int(msg_type)):
            media_items.append({
                "url":  payload.get(f"MediaUrl{i}",   ""),
                "mime": payload.get(f"MediaContentType{i}", ""),
            })
        sender = self._normalize_number(from_number.replace("whatsapp:", ""))
        return {
            "status":      "received",
            "sender":      sender,
            "message":     body,
            "message_sid": msg_sid,
            "message_type": "media" if media_items else "text",
            "attachments": media_items,
            "provider":    "twilio",
        }


# ─── Public singleton ─────────────────────────────────────────

class WhatsAppService(_BaseService):
    """
    Facade.  Call this, *not* the provider classes directly.

    Usage::

        from app.services.whatsapp_service import WhatsAppService
        wsp = WhatsAppService()
        wsp.send_text("0821234567", "Hi from OpenWA!")
    """

    def __init__(self):
        super().__init__()
        self._impl = _make_service()

    def __getattr__(self, name):
        """Proxy every attribute / method call to the concrete provider."""
        return getattr(self._impl, name)
