"""
WhatsApp CRM SA — Drip Campaign Engine
=======================================
Manages automated drip campaigns and broadcasts for SA SMMEs.
"""

import time
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import Enum

import requests
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings


class CampaignStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class DripCampaignEngine:
    """Manages automated drip campaigns for WhatsApp CRM."""

    def __init__(self):
        self.db = None  # Will be set by main app

    def load_campaign(self, campaign_id: str) -> Optional[Dict]:
        """Load campaign from database."""
        if not self.db:
            return None

        query = self.db.table("campaigns").select("*").eq("id", campaign_id).single()
        return query.data if query.data else None

    def get_active_campaigns(self) -> List[Dict]:
        """Get all active campaigns."""
        if not self.db:
            return []

        query = self.db.table("campaigns").select("*").eq("status", "active")
        return query.data or []

    def get_due_subscribers(self) -> List[Dict]:
        """Get all subscribers due for their next campaign message."""
        if not self.db:
            return []

        now = datetime.utcnow().isoformat()
        query = self.db.table("campaign_subscribers").select(
            "*, contacts!inner(whatsapp_number)"
        ).lt("next_send_at", now).eq("status", "active")

        return query.data or []

    def process_due_messages(self) -> Dict:
        """Process all due campaign messages. Called by cron."""
        subscribers = self.get_due_subscribers()
        results = {"sent": 0, "failed": 0, "skipped": 0}

        for sub in subscribers:
            campaign = self.load_campaign(sub.get("campaign_id"))
            if not campaign:
                results["skipped"] += 1
                continue

            # Get current step
            step_index = sub.get("current_step", 0)
            messages_seq = campaign.get("messages_sequence", [])

            if step_index >= len(messages_seq):
                # Campaign complete
                self.db.table("campaign_subscribers").update(
                    {"status": "completed"}
                ).eq("id", sub.get("id"))
                results["skipped"] += 1
                continue

            step = messages_seq[step_index]
            template_id = step.get("template_id")

            # Load template
            template = self.load_template(template_id)
            if not template:
                results["failed"] += 1
                continue

            # Get contact
            contact_number = sub.get("contacts", {}).get("whatsapp_number", "")
            if not contact_number:
                results["skipped"] += 1
                continue

            # Send message
            try:
                self._send_template_message(contact_number, template, sub)
                results["sent"] += 1

                # Update subscriber
                next_step = step_index + 1
                next_delay = (
                    messages_seq[next_step].get("delay_hours", 0)
                    if next_step < len(messages_seq)
                    else 0
                )
                next_send = (
                    datetime.utcnow() + timedelta(hours=next_delay)
                ).isoformat()

                self.db.table("campaign_subscribers").update({
                    "current_step": next_step,
                    "next_send_at": next_send,
                }).eq("id", sub.get("id"))

            except Exception as e:
                print(f"Campaign message failed: {e}")
                results["failed"] += 1

        return results

    def load_template(self, template_id: str) -> Optional[Dict]:
        """Load a message template from database."""
        if not self.db:
            return None

        query = self.db.table("message_templates").select("*").eq("id", template_id).single()
        return query.data

    def _send_template_message(self, to_number: str, template: Dict, subscriber: Dict):
        """Send a template message via WhatsApp API."""
        try:
            from app.services.whatsapp_service import WhatsAppService
            ws = WhatsAppService()
            body = template.get("body", "")
            ws.send_text(to_number, body)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error("Failed to send campaign message to %s: %s", to_number, e)
            raise

    def add_subscriber(self, campaign_id: str, contact_id: str,
                       initial_delay_hours: int = 0) -> Dict:
        """Add a contact to a campaign."""
        if not self.db:
            return {"success": False, "error": "Database not initialized"}

        send_at = (datetime.utcnow() + timedelta(hours=initial_delay_hours)).isoformat()

        try:
            self.db.table("campaign_subscribers").insert({
                "campaign_id": campaign_id,
                "contact_id": contact_id,
                "current_step": 0,
                "next_send_at": send_at,
                "status": "active",
            }).execute()

            # Increment campaign subscriber count
            self.db.table("campaigns").update(
                {"active_subscribers": self.db.rpc("increment_subscriber_count", {
                    "campaign_id": campaign_id
                })}
            ).eq("id", campaign_id)

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def unsubscribe(self, campaign_id: str, contact_id: str) -> Dict:
        """Remove a contact from a campaign."""
        if not self.db:
            return {"success": False, "error": "Database not initialized"}

        try:
            self.db.table("campaign_subscribers").update(
                {"status": "unsubscribed"}
            ).eq("campaign_id", campaign_id).eq("contact_id", contact_id).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_broadcast(self, message: str, tag_ids: List[str] = None,
                       industry_filter: str = None, province_filter: str = None) -> Dict:
        """Send a broadcast message to a targeted audience."""
        if not self.db:
            return {"success": False, "error": "Database not initialized"}

        # Build query
        query = self.db.table("contacts").select("whatsapp_number")

        if tag_ids:
            # Get contacts with matching tags
            tag_contacts = self.db.table("contact_tags").select("contact_id").in_(
                "tag_id", tag_ids
            )
            if tag_contacts.data:
                contact_ids = [c["contact_id"] for c in tag_contacts.data]
                query = query.in_("id", contact_ids)

        if industry_filter:
            # Get contacts from businesses in this industry
            query = query.eq("industry", industry_filter)

        if province_filter:
            query = query.eq("province", province_filter)

        resp = query.execute()
        contacts = resp.data or []
        sent = 0
        failed = 0

        from app.services.whatsapp_service import WhatsAppService
        ws = WhatsAppService()

        for contact in contacts:
            try:
                number = contact.get("whatsapp_number", "")
                if number:
                    ws.send_text(number, message)
                    sent += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
            time.sleep(0.5)  # Rate limiting

        return {"success": True, "sent": sent, "failed": failed}

    def check_word_trigger(self, message_body: str, campaign_id: str) -> Optional[Dict]:
        """Check if a message contains a campaign trigger word."""
        if not self.db:
            return None

        campaign = self.load_campaign(campaign_id)
        if not campaign:
            return None

        trigger_words = campaign.get("trigger_words", [])
        for word in trigger_words:
            if word.lower() in message_body.lower():
                return {"triggered": True, "campaign_id": campaign_id, "keyword": word}

        return None