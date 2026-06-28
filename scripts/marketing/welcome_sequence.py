"""
Welcome Sequence — Auto-enroll new leads
=========================================
Immediately welcomes new leads via WhatsApp.
Runs on the APScheduler (every 5 min checks for new leads).
Also callable standalone to seed the campaign.

Usage:
    python scripts/marketing/welcome_sequence.py
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

# ─── Welcome messages (ZAR, SA English) ─────────────────────
WELCOME_MESSAGES = [
    {
        "delay_hours": 0,
        "message": (
            "Hey {first_name}! 👋\n\n"
            "Welcome to {business_name}. We're excited to have you!\n\n"
            "Reply HELP if you need anything."
        ),
    },
    {
        "delay_hours": 2,
        "message": (
            "Quick question {first_name} — what are you looking for?\n\n"
            "1️⃣ Products & pricing\n"
            "2️⃣ Services\n"
            "3️⃣ General info\n\n"
            "Just reply with the number."
        ),
    },
    {
        "delay_hours": 24,
        "message": (
            "Hi {first_name}! 🌟\n\n"
            "Here's a 10% welcome discount for you:\n"
            "Code: WELCOME10\n\n"
            "Valid for 7 days. Use it on your first order!"
        ),
    },
    {
        "delay_hours": 72,
        "message": (
            "Hey {first_name}, just checking in! 😊\n\n"
            "Have you had a chance to check out our offers?\n\n"
            "Reply YES to chat with our team, or tap any link below:"
        ),
    },
]

BUSINESS_NAME = "Our Business"  # Override from config in production


def create_welcome_campaign(db) -> Campaign:
    """Create or get the welcome drip campaign."""
    existing = db.query(Campaign).filter(
        Campaign.name == "Welcome Sequence",
        Campaign.trigger_event == "new_lead",
    ).first()

    if existing:
        print(f"  Welcome campaign already exists: {existing.id}")
        return existing

    from app.services.contact_service import get_or_create_business
    business = get_or_create_business(db)

    campaign = Campaign(
        business_id=business.id,
        name="Welcome Sequence",
        campaign_type="drip",
        trigger_event="new_lead",
        trigger_delay_hours=0,
        messages_sequence=WELCOME_MESSAGES,
        target_audience="new_leads",
        status="active",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    print(f"  Created welcome campaign: {campaign.id}")
    return campaign


def enroll_new_leads(db, campaign: Campaign):
    """Find new leads not yet in the welcome campaign and enroll them."""
    engine = DripCampaignEngine(db)

    # Get contacts with lead_status = "new" and no active subscription
    new_leads = db.query(Contact).filter(Contact.lead_status == "new").all()
    enrolled = 0

    for lead in new_leads:
        existing_sub = db.query(CampaignSubscriber).filter(
            CampaignSubscriber.campaign_id == campaign.id,
            CampaignSubscriber.contact_id == lead.id,
            CampaignSubscriber.status.in_(["active", "completed"]),
        ).first()

        if not existing_sub:
            result = engine.add_subscriber(str(campaign.id), str(lead.id), initial_delay_hours=0)
            if result.get("success"):
                enrolled += 1
                print(f"    Enrolled: {lead.first_name} {lead.last_name} ({lead.whatsapp_number})")

    return enrolled


def seed_test_contacts(db, campaign: Campaign):
    """Add test contacts for demo purposes."""
    engine = DripCampaignEngine(db)
    business = get_or_create_business(db)
    test_contacts = [
        {"first_name": "Thabo", "last_name": "Test", "phone": "0821000001"},
        {"first_name": "Lerato", "last_name": "Test", "phone": "0821000002"},
        {"first_name": "Sipho", "last_name": "Test", "phone": "0821000003"},
    ]
    enrolled = 0
    for tc in test_contacts:
        phone = f"27{tc['phone'][1:]}"
        existing = db.query(Contact).filter(Contact.whatsapp_number == phone).first()
        if not existing:
            contact = Contact(
                business_id=business.id,
                whatsapp_number=phone,
                first_name=tc["first_name"],
                last_name=tc["last_name"],
                lead_status="new",
                lead_score=0,
                lead_source="test",
            )
            db.add(contact)
            db.commit()
            db.refresh(contact)
        else:
            contact = existing

        result = engine.add_subscriber(str(campaign.id), str(contact.id), initial_delay_hours=0)
        if result.get("success"):
            enrolled += 1
            print(f"    Enrolled test contact: {tc['first_name']}")

    return enrolled


def main():
    """Main entry point."""
    print("Welcome Sequence Setup")
    print("=" * 40)

    init_db()
    db = SessionLocal()

    try:
        print("\n1. Creating welcome campaign...")
        campaign = create_welcome_campaign(db)

        print("\n2. Enrolling existing new leads...")
        enrolled = enroll_new_leads(db, campaign)
        print(f"   Enrolled {enrolled} existing leads")

        print("\n3. Seeding test contacts...")
        test_enrolled = seed_test_contacts(db, campaign)
        print(f"   Enrolled {test_enrolled} test contacts")

        print("\n4. Campaign status:")
        stats = engine_get_stats(db, campaign.id)
        for key, value in stats.items():
            print(f"   {key}: {value}")

        print("\nDone! Welcome sequence is active.")
        print("Messages will be sent via APScheduler every 5 minutes.")

    finally:
        db.close()


def engine_get_stats(db, campaign_id):
    """Quick stats helper."""
    engine = DripCampaignEngine(db)
    return engine.get_campaign_stats(str(campaign_id))


if __name__ == "__main__":
    main()
