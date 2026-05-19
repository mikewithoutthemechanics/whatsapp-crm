#!/usr/bin/env python3
"""
SA WhatsApp CRM — Database Migration Scripts
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def init_db():
    """Initialize SQLite database with all tables."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import Base

    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "whatsapp_crm.db")
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    print(f"✅ Database initialized at: {db_path}")
    print("   Tables created:")

    for table in Base.metadata.sorted_tables:
        print(f"     - {table.name}")

    session.close()
    return True


def seed_demo_data():
    """Seed database with demo data for testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import Business, Contact, Tag, MessageTemplate

    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "whatsapp_crm.db")
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Demo business
    business = Business(
        name="Demo Plumbing SA",
        industry="plumbing",
        phone="+27821234567",
        province="Gauteng",
        city="Johannesburg",
        timezone="Africa/Johannesburg",
    )
    session.add(business)
    session.flush()
    business_id = business.id

    # Tags
    tags = [
        Tag(name="plumbing", color="#3B82F6", business_id=business_id),
        Tag(name="urgent", color="#EF4444", business_id=business_id),
        Tag(name="repeat-customer", color="#10B981", business_id=business_id),
        Tag(name="quote-pending", color="#F59E0B", business_id=business_id),
    ]
    session.add_all(tags)
    session.flush()

    # Contacts
    contacts = [
        Contact(
            business_id=business_id,
            first_name="Thabo",
            last_name="Mokoena",
            whatsapp_number="27821234567",
            display_name="Thabo M.",
            lead_status="new",
            lead_source="whatsapp",
            province="Gauteng",
            city="Johannesburg",
        ),
        Contact(
            business_id=business_id,
            first_name="Sarah",
            last_name="Peters",
            whatsapp_number="27821234568",
            display_name="Sarah P.",
            lead_status="contacted",
            lead_source="whatsapp",
            province="Western Cape",
            city="Cape Town",
        ),
        Contact(
            business_id=business_id,
            first_name="John",
            last_name="Doe",
            whatsapp_number="27821234569",
            display_name="John D.",
            lead_status="qualified",
            lead_source="referral",
            province="KwaZulu-Natal",
            city="Durban",
        ),
    ]
    session.add_all(contacts)

    # Message templates
    templates = [
        MessageTemplate(
            business_id=business_id,
            name="greeting",
            category="utility",
            body="Hi {{1}} 👋! Thanks for reaching out to Demo Plumbing. How can we help you today?",
            variables=["customer_name"],
            is_approved=True,
        ),
        MessageTemplate(
            business_id=business_id,
            name="pricing_inquiry",
            category="utility",
            body="Thanks for your interest in our plumbing services! 🔧\n\nTo give you an accurate quote, could you please tell us:\n1. What type of work is needed?\n2. What's your location?\n3. Is it urgent?",
            variables=["service_type"],
            is_approved=True,
        ),
        MessageTemplate(
            business_id=business_id,
            name="follow_up",
            category="marketing",
            body="Hi {{1}} 👋 Just following up on our earlier conversation. Are you still looking for plumbing services?",
            variables=["customer_name"],
            is_approved=False,
        ),
    ]
    session.add_all(templates)

    session.commit()
    session.close()

    print(f"\n✅ Demo data seeded:")
    print("   - 1 business (Demo Plumbing SA)")
    print("   - 4 tags (plumbing, urgent, repeat-customer, quote-pending)")
    print("   - 3 contacts (Thabo, Sarah, John)")
    print("   - 3 message templates (greeting, pricing, follow-up)")

    return True


if __name__ == "__main__":
    print("=" * 55)
    print("  WhatsApp CRM SA — Database Setup")
    print("=" * 55)

    print("\n1. Initializing database...")
    init_db()

    print("\n2. Seeding demo data...")
    seed_demo_data()

    print("\n✅ All done! Start the server with:")
    print("   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")