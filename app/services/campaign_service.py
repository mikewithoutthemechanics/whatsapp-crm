"""
WhatsApp CRM SA — Drip Campaign Engine
=======================================
Manages automated drip campaigns and broadcasts for SA SMMEs.
Uses SQLAlchemy instead of Supabase client.
"""

import time
import json
import os
import sys
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from sqlalchemy.orm import Session
from sqlalchemy import and_

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models import Campaign, CampaignSubscriber, Contact, MessageTemplate, Message
from app.config import settings

logger = logging.getLogger(__name__)


class CampaignStatus:
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class DripCampaignEngine:
    """Manages automated drip campaigns for WhatsApp CRM using SQLAlchemy."""

    def __init__(self, db: Session = None):
        self.db = db

    def set_db(self, db: Session):
        """Set the database session."""
        self.db = db

    def get_active_campaigns(self) -> List[Campaign]:
        """Get all active campaigns."""
        if not self.db:
            return []
        return self.db.query(Campaign).filter(
            Campaign.status == CampaignStatus.ACTIVE
        ).all()

    def get_due_subscribers(self) -> List[Dict]:
        """Get all subscribers due for their next campaign message."""
        if not self.db:
            return []

        now = datetime.utcnow()
        subscribers = (
            self.db.query(CampaignSubscriber, Contact, Campaign)
            .join(Contact, CampaignSubscriber.contact_id == Contact.id)
            .join(Campaign, CampaignSubscriber.campaign_id == Campaign.id)
            .filter(
                CampaignSubscriber.status == "active",
                CampaignSubscriber.next_send_at <= now,
            )
            .all()
        )

        return [
            {
                "subscriber_id": str(sub.id),
                "campaign_id": str(campaign.id),
                "contact_id": str(contact.id),
                "whatsapp_number": contact.whatsapp_number,
                "current_step": sub.current_step,
                "messages_sequence": campaign.messages_sequence or [],
                "campaign_name": campaign.name,
            }
            for sub, contact, campaign in subscribers
        ]

    def process_due_messages(self) -> Dict:
        """Process all due campaign messages. Called by cron."""
        if not self.db:
            return {"sent": 0, "failed": 0, "skipped": 0}

        subscribers = self.get_due_subscribers()
        results = {"sent": 0, "failed": 0, "skipped": 0}

        for sub in subscribers:
            step_index = sub["current_step"]
            messages_seq = sub["messages_sequence"]

            if step_index >= len(messages_seq):
                # Campaign complete
                subscriber = self.db.query(CampaignSubscriber).filter(
                    CampaignSubscriber.id == uuid.UUID(sub["subscriber_id"])
                ).first()
                if subscriber:
                    subscriber.status = "completed"
                    self.db.commit()
                results["skipped"] += 1
                continue

            step = messages_seq[step_index]
            message_text = step.get("message", "")

            if not message_text:
                results["skipped"] += 1
                continue

            # Send message
            try:
                self._send_message(sub["whatsapp_number"], message_text, sub["campaign_name"])
                results["sent"] += 1

                # Update subscriber to next step
                subscriber = self.db.query(CampaignSubscriber).filter(
                    CampaignSubscriber.id == uuid.UUID(sub["subscriber_id"])
                ).first()
                if subscriber:
                    next_step = step_index + 1
                    next_delay = (
                        messages_seq[next_step].get("delay_hours", 0)
                        if next_step < len(messages_seq)
                        else 0
                    )
                    subscriber.current_step = next_step
                    subscriber.next_send_at = datetime.utcnow() + timedelta(hours=next_delay)

                    # Update campaign stats
                    campaign = self.db.query(Campaign).filter(
                        Campaign.id == uuid.UUID(sub["campaign_id"])
                    ).first()
                    if campaign:
                        campaign.sent_count = (campaign.sent_count or 0) + 1

                    self.db.commit()

            except Exception as e:
                logger.error("Campaign message failed for %s: %s", sub["whatsapp_number"], e)
                results["failed"] += 1

        return results

    def _send_message(self, to_number: str, message: str, campaign_name: str = ""):
        """Send a message via WhatsApp service."""
        try:
            from app.services.whatsapp_service import WhatsAppService
            ws = WhatsAppService()
            ws.send_text(to_number, message)
        except Exception as e:
            logger.error("Failed to send WhatsApp message to %s: %s", to_number, e)
            raise

    def add_subscriber(self, campaign_id: str, contact_id: str,
                       initial_delay_hours: int = 0) -> Dict:
        """Add a contact to a campaign."""
        if not self.db:
            return {"success": False, "error": "Database not initialized"}

        try:
            camp_uuid = uuid.UUID(campaign_id) if isinstance(campaign_id, str) else campaign_id
            cont_uuid = uuid.UUID(contact_id) if isinstance(contact_id, str) else contact_id

            # Check if already subscribed
            existing = self.db.query(CampaignSubscriber).filter(
                CampaignSubscriber.campaign_id == camp_uuid,
                CampaignSubscriber.contact_id == cont_uuid,
                CampaignSubscriber.status == "active",
            ).first()

            if existing:
                return {"success": False, "error": "Contact already subscribed"}

            subscriber = CampaignSubscriber(
                campaign_id=camp_uuid,
                contact_id=cont_uuid,
                current_step=0,
                next_send_at=datetime.utcnow() + timedelta(hours=initial_delay_hours),
                status="active",
            )
            self.db.add(subscriber)

            # Increment campaign subscriber count
            campaign = self.db.query(Campaign).filter(Campaign.id == camp_uuid).first()
            if campaign:
                campaign.active_subscribers = (campaign.active_subscribers or 0) + 1

            self.db.commit()
            return {"success": True}
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def unsubscribe(self, campaign_id: str, contact_id: str) -> Dict:
        """Remove a contact from a campaign."""
        if not self.db:
            return {"success": False, "error": "Database not initialized"}

        try:
            camp_uuid = uuid.UUID(campaign_id) if isinstance(campaign_id, str) else campaign_id
            cont_uuid = uuid.UUID(contact_id) if isinstance(contact_id, str) else contact_id

            subscriber = self.db.query(CampaignSubscriber).filter(
                CampaignSubscriber.campaign_id == camp_uuid,
                CampaignSubscriber.contact_id == cont_uuid,
            ).first()

            if subscriber:
                subscriber.status = "unsubscribed"
                self.db.commit()

            return {"success": True}
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def send_broadcast(self, message: str, tag_ids: List[str] = None,
                       province_filter: str = None) -> Dict:
        """Send a broadcast message to a targeted audience."""
        if not self.db:
            return {"success": False, "error": "Database not initialized"}

        query = self.db.query(Contact)

        if province_filter:
            query = query.filter(Contact.province == province_filter)

        if tag_ids:
            from app.models import ContactTag
            tag_uuids = [uuid.UUID(t) for t in tag_ids]
            matching_contact_ids = (
                self.db.query(ContactTag.contact_id)
                .filter(ContactTag.tag_id.in_(tag_uuids))
                .distinct()
                .all()
            )
            contact_ids = [r[0] for r in matching_contact_ids]
            query = query.filter(Contact.id.in_(contact_ids))

        contacts = query.all()
        sent = 0
        failed = 0

        for contact in contacts:
            if not contact.whatsapp_number:
                failed += 1
                continue
            try:
                self._send_message(contact.whatsapp_number, message)
                sent += 1
            except Exception:
                failed += 1
            time.sleep(0.5)  # Rate limiting

        return {"success": True, "sent": sent, "failed": failed}

    def auto_enroll_new_leads(self, contact_id: str) -> Dict:
        """Auto-enroll a new lead in the welcome campaign."""
        if not self.db:
            return {"success": False, "error": "Database not initialized"}

        # Find the welcome campaign
        welcome_campaign = self.db.query(Campaign).filter(
            Campaign.status == CampaignStatus.ACTIVE,
            Campaign.trigger_event == "new_lead",
        ).first()

        if not welcome_campaign:
            return {"success": False, "error": "No active welcome campaign found"}

        return self.add_subscriber(str(welcome_campaign.id), contact_id, initial_delay_hours=0)

    def get_campaign_stats(self, campaign_id: str) -> Dict:
        """Get statistics for a campaign."""
        if not self.db:
            return {}

        try:
            camp_uuid = uuid.UUID(campaign_id) if isinstance(campaign_id, str) else campaign_id

            campaign = self.db.query(Campaign).filter(Campaign.id == camp_uuid).first()
            if not campaign:
                return {"error": "Campaign not found"}

            total_subscribers = self.db.query(CampaignSubscriber).filter(
                CampaignSubscriber.campaign_id == camp_uuid
            ).count()

            active_subscribers = self.db.query(CampaignSubscriber).filter(
                CampaignSubscriber.campaign_id == camp_uuid,
                CampaignSubscriber.status == "active",
            ).count()

            completed = self.db.query(CampaignSubscriber).filter(
                CampaignSubscriber.campaign_id == camp_uuid,
                CampaignSubscriber.status == "completed",
            ).count()

            return {
                "campaign_id": campaign_id,
                "name": campaign.name,
                "status": campaign.status,
                "total_subscribers": total_subscribers,
                "active_subscribers": active_subscribers,
                "completed": completed,
                "sent_count": campaign.sent_count or 0,
                "delivered_count": campaign.delivered_count or 0,
                "replied_count": campaign.replied_count or 0,
            }
        except Exception as e:
            return {"error": str(e)}
