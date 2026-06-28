"""
Nurture Drip Sequence — Educational content over 7 days
========================================================
Builds trust with leads by sending valuable content.
Runs on APScheduler. Can also be run standalone.

Usage:
    python scripts/marketing/nurture_drip.py
"""

import sys
import os
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal, init_db
from app.models import Campaign, Contact, CampaignSubscriber
from app.services.campaign_service import DripCampaignEngine
from app.services.contact_service import get_or_create_business

# ─── Nurture content (7-day drip, SA context) ────────────────
NURTURE_MESSAGES = [
    {
        "delay_hours": 0,
        "message": (
            "Hey {first_name}! 📚\n\n"
            "Here's a quick tip for your business:\n\n"
            "💡 Did you know? 78% of SA consumers prefer WhatsApp "
            "for business communication.\n\n"
            "That's why we built this CRM — to help you reach "
            "your customers where they already are."
        ),
    },
    {
        "delay_hours": 48,
        "message": (
            "Hi {first_name}! 🚀\n\n"
            "Here's what our customers say:\n\n"
            "\"We increased sales by 34% in the first month!\"\n"
            "— Karabo, Johannesburg\n\n"
            "Want similar results? Reply START to get started."
        ),
    },
    {
        "delay_hours": 120,
        "message": (
            "Hey {first_name}! 📊\n\n"
            "Quick stat: SMMEs that use WhatsApp automation\n"
            "save 12+ hours per week on customer communication.\n\n"
            "That's time you could spend growing your business."
        ),
    },
    {
        "delay_hours": 168,
        "message": (
            "Hi {first_name}! 🎯\n\n"
            "Here's a free resource:\n\n"
            "📱 WhatsApp Business Checklist:\n"
            "✅ Professional profile\n"
            "✅ Quick replies\n"
            "✅ Labels for organisation\n"
            "✅ Broadcast lists\n\n"
            "Need help setting up? Reply HELP."
        ),
    },
    {
        "delay_hours": 240,
        "message": (
            "Hey {first_name}! 💰\n\n"
            "Special offer for you:\n\n"
            "Get 20% off your first 3 months.\n"
            "Code: NURTURE20\n\n"
            "Valid for 5 days. Don't miss out!"
        ),
    },
    {
        "delay_hours": 336,
        "message": (
            "Hi {first_name}! 🌟\n\n"
            "Last chance! Your 20% discount expires tomorrow.\n\n"
            "Code: NURTURE20\n\n"
            "Reply YES to claim it now."
        ),
    },
]


def create_nurture_campaign(db) -> Campaign:
    """Create or get the nurture drip campaign."""
    existing = db.query(Campaign).filter(
        Campaign.name == "Nurture Drip",
        Campaign.trigger_event == "lead_qualified",
    ).first()

    if existing:
        print(f"  Nurture campaign already exists: {existing.id}")
        return existing

    business = get_or_create_business(db)

    campaign = Campaign(
        business_id=business.id,
        name="Nurture Drip",
        campaign_type="drip",
        trigger_event="lead_qualified",
        trigger_delay_hours=0,
        messages_sequence=NURTURE_MESSAGES,
        target_audience="qualified_leads",
        status="active",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    print(f"  Created nurture campaign: {campaign.id}")
    return campaign


def enroll_qualified_leads(db, campaign: Campaign):
    """Enroll contacts with lead_status='qualified' or 'contacted'."""
    engine = DripCampaignEngine(db)

    leads = db.query(Contact).filter(
        Contact.lead_status.in_(["qualified", "contacted"])
    ).all()

    enrolled = 0
    for lead in leads:
        existing_sub = db.query(CampaignSubscriber).filter(
            CampaignSubscriber.campaign_id == campaign.id,
            CampaignSubscriber.contact_id == lead.id,
            CampaignSubscriber.status.in_(["active", "completed"]),
        ).first()

        if not existing_sub:
            result = engine.add_subscriber(str(campaign.id), str(lead.id), initial_delay_hours=0)
            if result.get("success"):
                enrolled += 1
                print(f"    Enrolled: {lead.first_name} {lead.last_name}")

    return enrolled


def main():
    """Main entry point."""
    print("Nurture Drip Setup")
    print("=" * 40)

    init_db()
    db = SessionLocal()

    try:
        print("\n1. Creating nurture campaign...")
        campaign = create_nurture_campaign(db)

        print("\n2. Enrolling qualified leads...")
        enrolled = enroll_qualified_leads(db, campaign)
        print(f"   Enrolled {enrolled} leads")

        print("\n3. Campaign stats:")
        engine = DripCampaignEngine(db)
        stats = engine.get_campaign_stats(str(campaign.id))
        for key, value in stats.items():
            print(f"   {key}: {value}")

        print("\nDone! Nurture sequence is active.")
        print("Messages sent via APScheduler every 5 minutes.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
