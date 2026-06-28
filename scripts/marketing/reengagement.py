"""
Re-engagement / Winback Automation
====================================
Re-activates inactive contacts (no activity in 30+ days).
Sends a sequence of increasingly compelling offers.

Usage:
    python scripts/marketing/reengagement.py
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

# ─── Winback messages (escalating offers) ────────────────────
REENGAGEMENT_MESSAGES = [
    {
        "delay_hours": 0,
        "message": (
            "Hey {first_name}! 👋\n\n"
            "We miss you! It's been a while since we heard from you.\n\n"
            "Is everything okay? We're here to help.\n\n"
            "Reply HI to reconnect."
        ),
    },
    {
        "delay_hours": 72,
        "message": (
            "Hi {first_name}! 🌟\n\n"
            "Just checking in — we haven't seen you in a while.\n\n"
            "Here's a little something to welcome you back:\n"
            "🎁 15% OFF your next purchase\n"
            "Code: WELCOMEBACK15\n\n"
            "Valid for 7 days."
        ),
    },
    {
        "delay_hours": 168,
        "message": (
            "Hey {first_name}! 💝\n\n"
            "We'd love to know what we could do better.\n\n"
            "Quick survey (30 seconds):\n"
            "1️⃣ Too expensive\n"
            "2️⃣ Didn't meet my needs\n"
            "3️⃣ Found a competitor\n"
            "4️⃣ Just busy right now\n\n"
            "Reply with a number. Your feedback helps us improve!"
        ),
    },
    {
        "delay_hours": 336,
        "message": (
            "Hi {first_name}! 🎁\n\n"
            "FINAL OFFER: We really want you back.\n\n"
            "Here's what we'll do:\n"
            "💰 25% OFF for 3 months\n"
            "📞 Free 1-hour strategy session\n"
            "🚀 Priority support\n\n"
            "This offer expires in 48 hours.\n\n"
            "Reply CLAIM to get started."
        ),
    },
]


def create_reengagement_campaign(db) -> Campaign:
    """Create or get the re-engagement campaign."""
    existing = db.query(Campaign).filter(
        Campaign.name == "Winback",
        Campaign.trigger_event == "inactivity",
    ).first()

    if existing:
        print(f"  Re-engagement campaign already exists: {existing.id}")
        return existing

    business = get_or_create_business(db)

    campaign = Campaign(
        business_id=business.id,
        name="Winback",
        campaign_type="drip",
        trigger_event="inactivity",
        trigger_delay_hours=0,
        messages_sequence=REENGAGEMENT_MESSAGES,
        target_audience="inactive",
        status="active",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    print(f"  Created winback campaign: {campaign.id}")
    return campaign


def find_inactive_contacts(db, days_inactive: int = 30):
    """Find contacts with no recent activity."""
    cutoff = datetime.utcnow() - timedelta(days=days_inactive)

    inactive = (
        db.query(Contact)
        .filter(
            Contact.lead_status.in_(["new", "contacted", "converted"]),
            Contact.updated_at < cutoff,
        )
        .all()
    )

    return inactive


def enroll_inactive_leads(db, campaign: Campaign, days_inactive: int = 30):
    """Enroll inactive contacts in the winback campaign."""
    engine = DripCampaignEngine(db)

    inactive = find_inactive_contacts(db, days_inactive)
    enrolled = 0

    for lead in inactive:
        existing_sub = db.query(CampaignSubscriber).filter(
            CampaignSubscriber.campaign_id == campaign.id,
            CampaignSubscriber.contact_id == lead.id,
            CampaignSubscriber.status.in_(["active", "completed"]),
        ).first()

        if not existing_sub:
            # Stagger the sends (1 hour apart to avoid spam)
            stagger_hours = enrolled
            result = engine.add_subscriber(
                str(campaign.id), str(lead.id), initial_delay_hours=stagger_hours
            )
            if result.get("success"):
                enrolled += 1
                print(f"    Enrolled: {lead.first_name} {lead.last_name} (inactive since {lead.updated_at})")

    return enrolled


def main():
    """Main entry point."""
    print("Re-engagement / Winback Setup")
    print("=" * 40)

    init_db()
    db = SessionLocal()

    try:
        print("\n1. Creating winback campaign...")
        campaign = create_reengagement_campaign(db)

        print("\n2. Finding inactive contacts (30+ days)...")
        inactive = find_inactive_contacts(db, days_inactive=30)
        print(f"   Found {len(inactive)} inactive contacts")

        print("\n3. Enrolling inactive contacts...")
        enrolled = enroll_inactive_leads(db, campaign, days_inactive=30)
        print(f"   Enrolled {enrolled} contacts")

        print("\n4. Campaign stats:")
        engine = DripCampaignEngine(db)
        stats = engine.get_campaign_stats(str(campaign.id))
        for key, value in stats.items():
            print(f"   {key}: {value}")

        print("\nDone! Winback campaign is active.")
        print("Re-engagement messages sent via APScheduler.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
