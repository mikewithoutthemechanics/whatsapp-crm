"""
WhatsApp CRM SA — Lead Service
================================
Lead capture, auto-scoring, and pipeline management.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Contact, ContactTag, Tag
from app.services.contact_service import (
    create_contact,
    normalize_sa_phone,
    get_or_create_business,
    add_tag_to_contact,
)


# ─── Lead Scoring Rules ──────────────────────────────────────

LEAD_SCORE_RULES = {
    "form_submission": 10,
    "whatsapp_message": 5,
    "link_clicked": 10,
    "demo_requested": 25,
    "pricing_inquiry": 15,
    "purchase": 50,
    "replied_to_message": 5,
    "opened_message": 2,
    "website_visit": 3,
    "referral": 20,
}

LEAD_STATUS_THRESHOLDS = {
    "new": (0, 10),
    "contacted": (11, 30),
    "qualified": (31, 60),
    "converted": (61, 100),
    "inactive": (0, 0),  # Special case
}


def calculate_lead_score(db: Session, contact_id: str, action: str) -> int:
    """Calculate and update lead score based on action."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return 0
    
    # Add points for the action
    points = LEAD_SCORE_RULES.get(action, 0)
    new_score = min(100, (contact.lead_score or 0) + points)
    
    contact.lead_score = new_score
    
    # Auto-update lead status based on score
    if new_score >= 61:
        contact.lead_status = "converted"
    elif new_score >= 31:
        contact.lead_status = "qualified"
    elif new_score >= 11:
        contact.lead_status = "contacted"
    elif new_score > 0:
        contact.lead_status = "new"
    
    db.commit()
    return new_score


def capture_lead(
    db: Session,
    whatsapp_number: str,
    first_name: str = "",
    last_name: str = "",
    email: str = "",
    message: str = "",
    source: str = "website",
    utm_source: str = "",
    utm_medium: str = "",
    utm_campaign: str = "",
    province: str = "",
    city: str = "",
    business_name: str = "Default Business",
) -> Dict:
    """Capture a new lead from various sources (forms, ads, landing pages)."""
    
    # Get or create business
    business = get_or_create_business(db, business_name)
    
    # Create or update contact
    contact = create_contact(
        db=db,
        whatsapp_number=whatsapp_number,
        first_name=first_name,
        last_name=last_name,
        display_name=f"{first_name} {last_name}".strip() if first_name else "",
        email=email,
        lead_status="new",
        lead_score=LEAD_SCORE_RULES.get("form_submission", 10),
        lead_source=source,
        province=province,
        city=city,
        business_id=business.id,
    )
    
    # Add source tag
    source_tag = f"source:{source}"
    add_tag_to_contact(db, contact.id, source_tag, business.id)
    
    # Add UTM tags if provided
    if utm_source:
        add_tag_to_contact(db, contact.id, f"utm:{utm_source}", business.id)
    if utm_campaign:
        add_tag_to_contact(db, contact.id, f"campaign:{utm_campaign}", business.id)
    
    # If this is a returning contact, update their status
    if contact.lead_status == "inactive":
        contact.lead_status = "new"
        db.commit()
    
    return {
        "success": True,
        "contact_id": str(contact.id),
        "lead_score": contact.lead_score,
        "lead_status": contact.lead_status,
        "is_new": contact.created_at.date() == datetime.utcnow().date(),
    }


def get_lead_pipeline(db: Session, business_id: str = None) -> Dict:
    """Get lead pipeline funnel data."""
    
    query = db.query(
        Contact.lead_status,
        func.count(Contact.id).label("count"),
    )
    
    if business_id:
        query = query.filter(Contact.business_id == business_id)
    
    pipeline = query.group_by(Contact.lead_status).all()
    
    # Build pipeline data
    statuses = ["new", "contacted", "qualified", "converted", "inactive"]
    pipeline_data = {}
    
    for status in statuses:
        count = 0
        for row in pipeline:
            if row.lead_status == status:
                count = row.count
                break
        pipeline_data[status] = {"count": count, "contacts": []}
    
    # Get sample contacts for each status
    for status in statuses:
        contacts = (
            db.query(Contact)
            .filter(Contact.lead_status == status)
            .order_by(Contact.lead_score.desc())
            .limit(5)
            .all()
        )
        pipeline_data[status]["contacts"] = [
            {
                "id": str(c.id),
                "name": c.display_name or f"{c.first_name} {c.last_name}".strip(),
                "phone": c.whatsapp_number,
                "score": c.lead_score,
                "source": c.lead_source,
            }
            for c in contacts
        ]
    
    return pipeline_data


def get_inactive_contacts(
    db: Session,
    days: int = 14,
    business_id: str = None,
) -> List[Contact]:
    """Get contacts that haven't been active in the specified number of days."""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Contact).filter(
        Contact.updated_at < cutoff_date,
        Contact.lead_status.notin_(["inactive", "converted"]),
    )
    
    if business_id:
        query = query.filter(Contact.business_id == business_id)
    
    return query.all()


def mark_inactive_contacts(db: Session, days: int = 14) -> int:
    """Mark contacts as inactive if no activity in specified days."""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    result = db.query(Contact).filter(
        Contact.updated_at < cutoff_date,
        Contact.lead_status.notin_(["inactive", "converted"]),
    ).update(
        {"lead_status": "inactive"},
        synchronize_session="fetch",
    )
    
    db.commit()
    return result


def get_lead_stats(db: Session, business_id: str = None) -> Dict:
    """Get lead statistics."""
    
    query = db.query(Contact)
    
    if business_id:
        query = query.filter(Contact.business_id == business_id)
    
    total = query.count()
    today = datetime.utcnow().date()
    
    new_today = query.filter(
        Contact.created_at >= datetime.combine(today, datetime.min.time())
    ).count()
    
    avg_score = db.query(func.avg(Contact.lead_score)).scalar() or 0
    
    # Source breakdown
    sources = (
        db.query(
            Contact.lead_source,
            func.count(Contact.id).label("count"),
        )
        .group_by(Contact.lead_source)
        .all()
    )
    
    return {
        "total_leads": total,
        "new_leads_today": new_today,
        "average_score": round(float(avg_score), 1),
        "sources": {row.lead_source or "unknown": row.count for row in sources},
    }
