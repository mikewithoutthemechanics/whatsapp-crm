"""
WhatsApp CRM SA — WhatsApp Chat Import Service
===============================================
Pulls chats, contacts, and message history from WhatsApp providers
(OpenWA, Meta, Twilio) and imports them into the CRM database.

Supports:
  - Full chat + message import
  - Contact-only import
  - Incremental / delta imports (only new messages since last import)
  - Deduplication by WhatsApp number (E.164)
  - Dry-run mode (preview without writing)
  - Background / scheduled imports
  - TheoBrand-aware multi-tenant routing
"""

import os
import sys
import time
import json
import logging
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from enum import Enum

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings


logger = logging.getLogger(__name__)


# ─── Enums / Constants ──────────────────────────────────────────

class ImportStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportType(str, Enum):
    FULL = "full"
    CONTACTS_ONLY = "contacts_only"
    DELTA = "delta"
    CHAT_HISTORY = "chat_history"


class ProviderType(str, Enum):
    OPENWA = "openwa"
    META = "meta"
    TWILIO = "twilio"


# ─── Service ────────────────────────────────────────────────────

class WhatsAppChatImportService:
    """
    Import WhatsApp data into the CRM.

    Usage::

        svc = WhatsAppChatImportService(business_id=biz_id, db=db, whatsapp=wsp)
        result = svc.run_import(source_id=src_id, import_type="full")
        print(result.summary)
    """

    def __init__(
        self,
        business_id: Optional[str] = None,
        brand_id: Optional[str] = None,
        db=None,
        whatsapp=None,
    ):
        self.business_id = business_id
        self.brand_id = brand_id
        self.db = db
        self.whatsapp = whatsapp

    # ── Public entry points ─────────────────────────────────────

    def start_import_job(
        self,
        source_id: Optional[str] = None,
        import_type: str = ImportType.FULL.value,
        chat_limit: Optional[int] = None,
        message_limit: Optional[int] = None,
        dry_run: bool = False,
        auto_reply_enabled: bool = True,
    ) -> Dict[str, Any]:
        """
        Create an ImportJob record and return it.  Call run_import_job() with the
        returned job_id to execute it.
        """
        if not self.business_id:
            raise ValueError("business_id is required")

        now = datetime.utcnow().isoformat()
        snapshot = {
            "business_id": self.business_id,
            "brand_id": self.brand_id,
            "source_id": source_id,
            "import_type": import_type,
            "chat_limit": chat_limit or settings.AUTO_IMPORT_CHAT_LIMIT,
            "message_limit": message_limit or settings.AUTO_IMPORT_MSG_LIMIT,
            "dry_run": dry_run,
            "auto_reply_enabled": auto_reply_enabled,
            "created_at": now,
        }

        job_data = {
            "business_id": self.business_id,
            "source_id": source_id,
            "job_type": import_type,
            "status": ImportStatus.QUEUED.value,
            "settings_snapshot": snapshot,
        }

        if self.db:
            try:
                q = self.db.table("import_jobs").insert(job_data).execute()
                data = getattr(q, "data", None) or getattr(q, "_response", None)
                if data and hasattr(data, "__iter__") and not isinstance(data, dict):
                    data = list(data)[0]
                job = data if isinstance(data, dict) else {"id": "pending"}
                job_id = job.get("id")
            except Exception as exc:
                logger.error("Failed to create import job: %s", exc)
                return job_data
        else:
            job_id = f"job_{hashlib.sha256(now.encode()).hexdigest()[:12]}"
            job_data["id"] = job_id

        return {
            "job_id": job_id,
            "status": ImportStatus.QUEUED.value,
            "settings": snapshot,
        }

    def run_import_job(self, job_id: str) -> Dict[str, Any]:
        """
        Execute a previously queued import job.  Returns a summary dict.
        """
        if not self.db:
            return {"error": "Database not available"}

        try:
            q = self.db.table("import_jobs").select("*").eq("id", job_id).single().execute()
            data = getattr(q, "data", None) or getattr(q, "_response", None)
            if hasattr(data, "data") and isinstance(data.data, dict):
                data = data.data
            job = data if isinstance(data, dict) else None
            if not job:
                return {"error": f"Job {job_id} not found"}
        except Exception as exc:
            return {"error": str(exc)}

        import_type = job.get("job_type", ImportType.FULL.value)
        snapshot = job.get("settings_snapshot", {})
        dry_run = snapshot.get("dry_run", settings.AUTO_IMPORT_DRY_RUN)
        chat_limit = snapshot.get("chat_limit", settings.AUTO_IMPORT_CHAT_LIMIT)
        message_limit = snapshot.get("message_limit", settings.AUTO_IMPORT_MSG_LIMIT)

        # Mark running
        self.db.table("import_jobs").update({
            "status": ImportStatus.RUNNING.value,
            "started_at": datetime.utcnow().isoformat(),
        }).eq("id", job_id).execute()

        try:
            if import_type == ImportType.CONTACTS_ONLY.value:
                result = self._import_contacts_only(dry_run=dry_run)
            elif import_type == ImportType.DELTA.value:
                result = self._import_delta(
                    chat_limit=chat_limit,
                    message_limit=message_limit,
                    dry_run=dry_run,
                )
            elif import_type == ImportType.CHAT_HISTORY.value:
                result = self._import_chat_history(
                    chat_limit=chat_limit,
                    message_limit=message_limit,
                    dry_run=dry_run,
                )
            else:
                result = self._import_full(
                    chat_limit=chat_limit,
                    message_limit=message_limit,
                    dry_run=dry_run,
                )

            finished_at = datetime.utcnow().isoformat()
            self.db.table("import_jobs").update({
                "status": ImportStatus.COMPLETED.value,
                "finished_at": finished_at,
                "contacts_found": result.get("contacts_found", 0),
                "contacts_created": result.get("contacts_created", 0),
                "contacts_updated": result.get("contacts_updated", 0),
                "messages_imported": result.get("messages_imported", 0),
                "conversations_created": result.get("conversations_created", 0),
                "skipped_duplicates": result.get("skipped_duplicates", 0),
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", []),
                "summary": result.get("summary", ""),
            }).eq("id", job_id).execute()

            result["job_id"] = job_id
            result["status"] = ImportStatus.COMPLETED.value
            return result

        except Exception as exc:
            logger.error("Import job %s failed: %s", job_id, exc)
            self.db.table("import_jobs").update({
                "status": ImportStatus.FAILED.value,
                "finished_at": datetime.utcnow().isoformat(),
                "errors": [{"error": str(exc)}],
            }).eq("id", job_id).execute()
            return {"error": str(exc), "job_id": job_id, "status": "failed"}

    # ── Import strategies ───────────────────────────────────────

    def _import_full(self, chat_limit: int = 50, message_limit: int = 30,
                     dry_run: bool = False) -> Dict[str, Any]:
        """Import contacts + chat history + conversations."""
        result: Dict[str, Any] = {
            "contacts_found": 0, "contacts_created": 0,
            "contacts_updated": 0, "messages_imported": 0,
            "conversations_created": 0, "skipped_duplicates": 0,
            "errors": [], "warnings": [], "summary": "",
        }

        contacts = self._fetch_contacts()
        result["contacts_found"] = len(contacts)

        source_id = self._default_source_id()
        job_id = ""

        for contact in contacts:
            try:
                saved = self._upsert_contact(contact, dry_run=dry_run)
                if saved.get("created"):
                    result["contacts_created"] += 1
                else:
                    result["contacts_updated"] += 1

                chat_history = self._fetch_chat_history(
                    contact.get("whatsapp_number") or contact.get("external_id", ""),
                    limit=message_limit,
                )
                if chat_history:
                    c_result = self._save_conversation_and_messages(
                        contact=contact,
                        saved_contact=saved,
                        messages=chat_history,
                        source_id=source_id,
                        dry_run=dry_run,
                    )
                    result["messages_imported"] += c_result.get("messages_saved", 0)
                    if c_result.get("conversation_created"):
                        result["conversations_created"] += 1

            except Exception as exc:
                result["errors"].append({
                    "contact": contact.get("whatsapp_number"),
                    "error": str(exc),
                })

        result["summary"] = (
            f"Full import: {result['contacts_found']} contacts found, "
            f"{result['contacts_created']} created, {result['contacts_updated']} updated, "
            f"{result['conversations_created']} conversations, "
            f"{result['messages_imported']} messages imported, "
            f"{result['skipped_duplicates']} duplicates skipped, "
            f"{len(result['errors'])} errors."
        )
        return result

    def _import_contacts_only(self, dry_run: bool = False) -> Dict[str, Any]:
        """Import contacts only — no messages."""
        contacts = self._fetch_contacts()
        result: Dict[str, Any] = {
            "contacts_found": len(contacts), "contacts_created": 0,
            "contacts_updated": 0, "messages_imported": 0,
            "conversations_created": 0, "skipped_duplicates": 0,
            "errors": [], "warnings": [], "summary": "Contact-only import.",
        }

        for contact in contacts:
            try:
                saved = self._upsert_contact(contact, dry_run=dry_run)
                if saved.get("created"):
                    result["contacts_created"] += 1
                else:
                    result["contacts_updated"] += 1
            except Exception as exc:
                result["errors"].append({"contact": contact.get("whatsapp_number"), "error": str(exc)})

        result["summary"] = (
            f"Contact import: {result['contacts_found']} found, "
            f"{result['contacts_created']} created, {result['contacts_updated']} updated, "
            f"{len(result['errors'])} errors."
        )
        return result

    def _import_delta(self, chat_limit: int = 50, message_limit: int = 30,
                      dry_run: bool = False) -> Dict[str, Any]:
        """Import only new / updated chats since last import."""
        source_id = self._default_source_id()
        last_import = self._get_last_import_timestamp(source_id)
        logger.info("Delta import: fetching chats since %s", last_import)

        chats = self._fetch_chats(limit=chat_limit)
        result: Dict[str, Any] = {
            "contacts_found": 0, "contacts_created": 0,
            "contacts_updated": 0, "messages_imported": 0,
            "conversations_created": 0, "skipped_duplicates": 0,
            "errors": [], "warnings": [], "summary": "",
        }

        for chat in chats:
            try:
                ts = self._chat_timestamp(chat)
                if last_import and ts and ts <= last_import:
                    continue

                number = self._extract_number(chat)
                if not number:
                    continue

                contact_data = self._enrich_contact(number, chat)
                result["contacts_found"] += 1
                saved = self._upsert_contact(contact_data, dry_run=dry_run)
                if saved.get("created"):
                    result["contacts_created"] += 1
                else:
                    result["contacts_updated"] += 1

                history = self._fetch_chat_history(number, limit=message_limit)
                if history and not dry_run:
                    c = self._save_conversation_and_messages(
                        contact=contact_data, saved_contact=saved,
                        messages=history, source_id=source_id, dry_run=False,
                    )
                    result["messages_imported"] += c.get("messages_saved", 0)
                    if c.get("conversation_created"):
                        result["conversations_created"] += 1

            except Exception as exc:
                result["errors"].append({"chat": str(chat)[:80], "error": str(exc)})

        result["summary"] = (
            f"Delta import: {result['contacts_found']} new chats, "
            f"{result['contacts_created']} contacts created, "
            f"{result['messages_imported']} messages imported, "
            f"{len(result['errors'])} errors."
        )
        return result

    def _import_chat_history(self, chat_limit: int = 50, message_limit: int = 30,
                             dry_run: bool = False) -> Dict[str, Any]:
        """Backfill full message history for existing contacts."""
        chats = self._fetch_chats(limit=chat_limit)
        result: Dict[str, Any] = {
            "contacts_found": len(chats), "contacts_created": 0,
            "contacts_updated": 0, "messages_imported": 0,
            "conversations_created": 0, "skipped_duplicates": 0,
            "errors": [], "warnings": [], "summary": "",
        }

        for chat in chats:
            try:
                number = self._extract_number(chat)
                if not number:
                    continue
                contact_data = self._enrich_contact(number, chat)
                saved = self._upsert_contact(contact_data, dry_run=dry_run)
                if saved.get("created"):
                    result["contacts_created"] += 1
                else:
                    result["contacts_updated"] += 1

                history = self._fetch_chat_history(number, limit=message_limit)
                if history:
                    c = self._save_conversation_and_messages(
                        contact=contact_data, saved_contact=saved,
                        messages=history, source_id=self._default_source_id(),
                        dry_run=dry_run,
                    )
                    result["messages_imported"] += c.get("messages_saved", 0)
                    if c.get("conversation_created"):
                        result["conversations_created"] += 1

            except Exception as exc:
                result["errors"].append({"chat": str(chat)[:80], "error": str(exc)})

        result["summary"] = (
            f"History backfill: {result['contacts_found']} chats, "
            f"{result['messages_imported']} messages, "
            f"{result['conversations_created']} conversations, "
            f"{len(result['errors'])} errors."
        )
        return result

    # ── Fetch from WhatsApp providers ────────────────────────────

    def _fetch_contacts(self) -> List[Dict[str, Any]]:
        if not self.whatsapp:
            return []
        provider = (settings.WHATSAPP_PROVIDER or "openwa").lower()
        try:
            if provider == "openwa":
                return self.whatsapp.get_contacts(limit=100)
            elif provider == "meta":
                return self._fetch_meta_contacts()
            elif provider == "twilio":
                return self._fetch_twilio_contacts()
        except Exception as exc:
            logger.warning("Contact fetch failed (%s): %s", provider, exc)
        return []

    def _fetch_chats(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        if not self.whatsapp:
            return []
        provider = (settings.WHATSAPP_PROVIDER or "openwa").lower()
        try:
            if provider == "openwa":
                return self.whatsapp.get_chats(limit=limit, offset=offset)
            elif provider == "meta":
                return self._fetch_meta_chats(limit=limit)
        except Exception as exc:
            logger.warning("Chat fetch failed: %s", exc)
        return []

    def _fetch_chat_history(self, number: str,
                             limit: int = 30) -> List[Dict[str, Any]]:
        if not self.whatsapp or not number:
            return []
        provider = (settings.WHATSAPP_PROVIDER or "openwa").lower()
        try:
            if provider == "openwa":
                return self.whatsapp.get_chat_messages(number, limit=limit)
        except Exception as exc:
            logger.warning("History fetch failed for %s: %s", number, exc)
        return []

    def _fetch_meta_contacts(self) -> List[Dict]:
        """Fetch contacts from Meta Graph API (best-effort)."""
        if not settings.META_PHONE_NUMBER_ID or not settings.META_ACCESS_TOKEN:
            return []
        url = (
            f"https://graph.facebook.com/v18.0/{settings.META_PHONE_NUMBER_ID}"
            "/contacts?fields=name,phone"
        )
        try:
            r = requests.get(url, headers={"Authorization": f"Bearer {settings.META_ACCESS_TOKEN}"},
                             timeout=15)
            if r.status_code != 200:
                return []
            data = r.json()
            return data.get("data", [])
        except Exception as exc:
            logger.warning("Meta contacts fetch failed: %s", exc)
            return []

    def _fetch_meta_chats(self, limit: float = 50) -> List[Dict]:
        return []

    def _fetch_twilio_contacts(self) -> List[Dict]:
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            records = client.messages.list(limit=100)
            seen: Dict[str, Dict] = {}
            for rec in records:
                num = self._strip_sender(rec.from_ or rec.to)
                if num not in seen:
                    seen[num] = {"whatsapp_number": num, "display_name": num}
            return list(seen.values())
        except Exception as exc:
            logger.warning("Twilio contacts fetch failed: %s", exc)
            return []

    @staticmethod
    def _strip_sender(raw: str) -> str:
        return raw.replace("whatsapp:", "").lstrip("+")

    # ── Helpers ─────────────────────────────────────────────────

    @property
    def _wsp(self):
        if not self.whatsapp:
            from app.services.whatsapp_service import WhatsAppService
            return WhatsAppService()
        return self.whatsapp

    def _default_source_id(self) -> Optional[str]:
        if not self.db:
            return None
        try:
            q = self.db.table("import_sources").select("id").eq(
                "business_id", self.business_id
            ).eq("source_type", "whatsapp").limit(1).execute()
            data = getattr(q, "data", None) or getattr(q, "_response", None)
            if hasattr(data, "data"):
                data = data.data
            rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            return rows[0]["id"] if rows else None
        except Exception:
            return None

    def _get_last_import_timestamp(self, source_id: Optional[str]) -> Optional[datetime]:
        if not self.db or not source_id:
            return None
        try:
            q = self.db.table("import_jobs").select("finished_at").eq(
                "source_id", source_id
            ).eq("status", "completed").order("finished_at", desc=True).limit(1).execute()
            data = getattr(q, "data", None) or getattr(q, "_response", None)
            if hasattr(data, "data"):
                data = data.data
            rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            if not rows or not rows[0].get("finished_at"):
                return None
            return datetime.fromisoformat(rows[0]["finished_at"].replace("Z", "+00:00"))
        except Exception:
            return None

    def _extract_number(self, chat: Dict) -> Optional[str]:
        for key in ("id", "chatId", "jid", "remoteJid", "phone_number"):
            val = chat.get(key, "")
            if val:
                cleaned = val.replace("@c.us", "").replace("whatsapp:", "").lstrip("+")
                if cleaned.startswith("0") and len(cleaned) == 10:
                    cleaned = "27" + cleaned[1:]
                if cleaned.isdigit() and len(cleaned) >= 10:
                    return cleaned
        return None

    def _enrich_contact(self, number: str, chat: Dict) -> Dict[str, Any]:
        name = chat.get("name") or chat.get("pushName") or chat.get("contactName") or number
        parts = name.split(" ", 1)
        return {
            "whatsapp_number": number,
            "first_name": parts[0] if parts else name,
            "last_name": parts[1] if len(parts) > 1 else "",
            "display_name": name,
            "lead_status": "new",
            "lead_score": 0,
            "lead_source": "whatsapp",
        }

    def _chat_timestamp(self, chat: Dict) -> Optional[datetime]:
        for key in ("last_message_time", "timestamp", "updatedAt", "updated_at"):
            raw = chat.get(key)
            if not raw:
                continue
            try:
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except ValueError:
                continue
        return None

    def _upsert_contact(self, contact: Dict, dry_run: bool = False) -> Dict:
        """
        Insert or update a contact.  Returns {"created": bool, "data": dict}.
        """
        number = contact.get("whatsapp_number", "")
        if not number:
            return {"created": False, "data": contact}

        if not self.db:
            return {"created": True, "data": contact}

        try:
            q = self.db.table("contacts").select("*").eq(
                "whatsapp_number", number
            ).limit(1).execute()
            data = getattr(q, "data", None) or getattr(q, "_response", None)
            if hasattr(data, "data"):
                data = data.data
            rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            existing = rows[0] if rows and rows[0] else None

            payload = {
                "whatsapp_number": number,
                "first_name": contact.get("first_name", ""),
                "last_name": contact.get("last_name", ""),
                "display_name": contact.get("display_name", ""),
                "email": contact.get("email", ""),
                "lead_status": contact.get("lead_status", "new"),
                "lead_score": contact.get("lead_score", 0),
                "lead_source": contact.get("lead_source", "whatsapp"),
                "province": contact.get("province", ""),
                "city": contact.get("city", ""),
                "updated_at": datetime.utcnow().isoformat(),
            }
            if self.business_id:
                payload["business_id"] = self.business_id

            if existing:
                if dry_run:
                    return {"created": False, "data": existing}
                upd = self.db.table("contacts").update(payload).eq(
                    "id", existing["id"]
                ).execute()
                return {"created": False, "data": payload}

            payload["id"] = str(hashlib.sha256(number.encode()).hexdigest()[:16])
            payload["created_at"] = datetime.utcnow().isoformat()
            if dry_run:
                return {"created": True, "data": payload}

            ins = self.db.table("contacts").insert(payload).execute()
            return {"created": True, "data": payload}

        except Exception as exc:
            logger.error("Contact upsert failed for %s: %s", number, exc)
            raise

    def _save_conversation_and_messages(
        self,
        contact: Dict,
        saved_contact: Dict,
        messages: List[Dict],
        source_id: Optional[str],
        dry_run: bool = False,
    ) -> Dict:
        """
        Persist conversation + messages for a contact.
        Returns a summary dict.
        """
        result = {"conversation_created": False, "messages_saved": 0}
        if not messages:
            return result

        contact_id = saved_contact.get("id") if isinstance(saved_contact, dict) else None
        if not contact_id:
            return result

        if not self.db or dry_run:
            result["messages_saved"] = len(messages)
            return result

        try:
            conv_q = self.db.table("conversations").select("id").eq(
                "contact_id", contact_id
            ).limit(1).execute()
            conv_data = getattr(conv_q, "data", None) or getattr(conv_q, "_response", None)
            if hasattr(conv_data, "data"):
                conv_data = conv_data.data
            conv_rows = conv_data if isinstance(conv_data, list) else [conv_data] if isinstance(conv_data, dict) else []
            conversation = conv_rows[0] if conv_rows and conv_rows[0] else None

            if not conversation:
                conv_id = str(hashlib.sha256(
                    f"{self.business_id}:{contact_id}".encode()
                ).hexdigest()[:16])
                conv_payload = {
                    "id": conv_id,
                    "business_id": self.business_id,
                    "contact_id": contact_id,
                    "channel": "whatsapp",
                    "status": "open",
                    "created_at": datetime.utcnow().isoformat(),
                    "last_message_at": datetime.utcnow().isoformat(),
                }
                if source_id:
                    conv_payload["source_id"] = source_id
                self.db.table("conversations").insert(conv_payload).execute()
                result["conversation_created"] = True
                conversation = {"id": conv_id}
            else:
                last_at = messages[-1].get("timestamp", datetime.utcnow().isoformat())
                self.db.table("conversations").update({
                    "last_message_at": last_at,
                }).eq("id", conversation["id"]).execute()

            # Save messages (deduplicate by external id / id)
            saved = 0
            existing_ids: set = set()
            try:
                existing_q = self.db.table("messages").select(
                    "whatsapp_message_id,id"
                ).eq("conversation_id", conversation["id"]).execute()
                ex_data = getattr(existing_q, "data", None) or getattr(existing_q, "_response", None)
                if hasattr(ex_data, "data"):
                    ex_data = ex_data.data
                ex_rows = ex_data if isinstance(ex_data, list) else [ex_data] if isinstance(ex_data, dict) else []
                existing_ids = {r.get("whatsapp_message_id", r.get("id", "")) for r in ex_rows if r}
            except Exception:
                pass

            for msg in messages:
                ext_id = msg.get("id") or msg.get("message_id") or msg.get("msgId")
                if not ext_id or ext_id in existing_ids:
                    continue

                content = msg.get("body") or msg.get("text") or msg.get("content") or ""
                if not content and msg.get("type") != "text":
                    content = json.dumps(msg.get("media", {}))

                msg_payload = {
                    "id": str(hashlib.sha256(
                        f"{conversation['id']}:{ext_id}".encode()
                    ).hexdigest()[:16]),
                    "conversation_id": conversation["id"],
                    "contact_id": contact_id,
                    "sent_by": "customer",
                    "message_type": msg.get("type", "text"),
                    "content": content,
                    "whatsapp_message_id": ext_id,
                    "is_read": False,
                    "created_at": msg.get("timestamp", datetime.utcnow().isoformat()),
                }
                try:
                    self.db.table("messages").insert(msg_payload).execute()
                    existing_ids.add(ext_id)
                    saved += 1
                except Exception as exc:
                    logger.debug("Message insert skipped: %s", exc)

            result["messages_saved"] = saved

            # Update ImportedChat summary row
            if source_id and saved > 0:
                try:
                    self.db.table("imported_chats").upsert({
                        "business_id": self.business_id,
                        "source_id": source_id,
                        "contact_id": contact_id,
                        "external_chat_id": str(contact.get("whatsapp_number")),
                        "external_contact_id": str(contact.get("whatsapp_number")),
                        "last_message_at": datetime.utcnow().isoformat(),
                        "last_message_preview": messages[-1].get("body", "")[:200],
                        "unread_count": 0,
                        "message_count": saved,
                        "raw_meta": {"last_import": datetime.utcnow().isoformat()},
                    }, on_conflict="business_id,source_id,contact_id").execute()
                except Exception:
                    pass

            return result

        except Exception as exc:
            logger.error("Failed to save conversation for %s: %s",
                         contact.get("whatsapp_number"), exc)
            return result


# ─── Convenience loader from DB config ──────────────────────────

def load_import_sources(db, business_id: str) -> List[Dict]:
    """Return all active import sources for a business."""
    try:
        q = db.table("import_sources").select("*").eq(
            "business_id", business_id
        ).eq("is_active", True).execute()
        data = getattr(q, "data", None) or getattr(q, "_response", None)
        if hasattr(data, "data"):
            data = data.data
        rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        return [r for r in rows if r]
    except Exception:
        return []
