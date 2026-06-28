"""
Conversion Campaign — Time-bound offers to close deals
=======================================================
Sends urgency-based messages to convert leads into customers.
Limited-time offers with countdown messaging.

Usage:
    python scripts/marketing/conversion_campaign.py
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

# ─── Conversion messages (urgency + social proof) ──────────────
CONVERSION_MESSAGES = [
    {
        "delay_hours": 0,
        "message": (
            "Hey {first_name}! 🔥\n\n"
            "We noticed you're interested in our services.\n\n"
            "For the next 48 hours, we're offering:\n"
            "💰 30% OFF all plans\n"
            "🎁 Free setup (worth R500)\n"
            "📞 Free 30-min consultation\n\n"
            "Reply DEAL to claim your offer."
        ),
    },
    {
        "delay_hours": 24,
        "message": (
            "Hi {first_name}! ⏰\n\n"
            "Your 30% discount expires in 24 hours!\n\n"
            "Over 200 SA businesses already switched this month.\n"
            "Don't get left behind.\n\n"
            "Reply NOW to lock in your discount."
        ),
    },
    {
        "delay_hours": 36,
        "message": (
            "Hey {first_name}! ⚡\n\n"
            "FINAL HOURS: 30% off ends tonight!\n\n"
            "Here's what you get:\n"
            "✅ Unlimited WhatsApp messages\n"
            "✅ AI-powered auto-replies\n"
            "✅ Contact management\n"
            "✅ Campaign tools\n\n"
            "All for R297/month (normally R447).\n\n"
            "Reply YES to start."
        ),
    },
    {
        "delay_hours": 48,
        "message": (
            "Hi {first_name}! 🎯\n\n"
            "Last chance! Your discount just expired.\n\n"
            "But since you showed interest, I've secured\n"
            "a special 24-hour extension just for you.\n\n"
            "Reply EXTEND to claim."
        ),
    },
]


def create_conversion_campaign(db) -> Campaign:
    """Create or get the conversion campaign."""
    existing = db.query(Campaign).filter(
        Campaign.name == "Conversion Blitz",
        Campaign.trigger_event == "lead_qualified",
    ).first()

    if existing:
        print(f"  Conversion campaign already exists: {existing.id}")
        return existing

    business = get_or_create_business(db)

    campaign = Campaign(
        business_id=business.id,
        name="Conversion Blitz",
        campaign_type="drip",
        trigger_event="lead_qualified",
        trigger_delay_hours=0,
        messages_sequence=CONVERSION_MESSAGES,
        target_audience="qualified_leads",
        status="draft",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    print(f"  Created conversion campaign: {campaign.id}")
    return campaign


def enroll_conversion_leads(db, campaign: Campaign):
    """Enroll contacts with lead_status='qualified' (score 31-60)."""
    engine = DripCampaignEngine(db)

    leads = db.query(Contact).filter(
        Contact.lead_status == "qualified",
        Contact.lead_score >= 31,
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
                print(f"    Enrolled: {lead.first_name} {lead.last_name} (score: {lead.lead_score})")

    return enrolled


def activate_campaign(db, campaign: Campaign):
    """Activate the conversion campaign."""
    campaign.status = "active"
    db.commit()
    print(f"  Campaign activated!")


def main():
    """Main entry point."""
    print("Conversion Campaign Setup")
    print("=" * 40)

    init_db()
    db = SessionLocal()

    try:
        print("\n1. Creating conversion campaign...")
        campaign = create_conversion_campaign(db)

        print("\n2. Enrolling qualified leads...")
        enrolled = enroll_conversion_leads(db, campaign)
        print(f"   Enrolled {enrolled} leads")

        print("\n3. Activating campaign...")
        activate_campaign(db, campaign)

        print("\n4. Campaign stats:")
        engine = DripCampaignEngine(db)
        stats = engine.get_campaign_stats(str(campaign.id))
        for key, value in stats.items():
            print(f"   {key}: {value}")

        print("\nDone! Conversion campaign is active.")
        print("Urgency messages will be sent automatically.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
