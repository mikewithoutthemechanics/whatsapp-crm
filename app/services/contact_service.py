"""
WhatsApp CRM SA — Contact Service
==================================
Business logic for contact CRUD, CSV import, deduplication, and tagging.
"""

import re
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models import Contact, Tag, ContactTag, Business


def normalize_sa_phone(phone: str) -> str:
    """Normalize South African phone number to international format.
    
    Examples:
        0821234567 -> 27821234567
        +27821234567 -> 27821234567
        27821234567 -> 27821234567
    """
    cleaned = re.sub(r"[^\d]", "", phone)
    
    # Handle SA numbers starting with 0
    if cleaned.startswith("0") and len(cleaned) == 10:
        cleaned = "27" + cleaned[1:]
    
    # Ensure it starts with country code
    if not cleaned.startswith("27") and len(cleaned) == 9:
        cleaned = "27" + cleaned
    
    return cleaned


def get_or_create_business(db: Session, business_name: str = "Default Business") -> Business:
    """Get or create the default business account."""
    business = db.query(Business).first()
    if not business:
        business = Business(
            name=business_name,
            phone="0000000000",
            province="Gauteng",
            city="Johannesburg",
        )
        db.add(business)
        db.commit()
        db.refresh(business)
    return business


def create_contact(
    db: Session,
    whatsapp_number: str,
    first_name: str = "",
    last_name: str = "",
    display_name: str = "",
    email: str = "",
    lead_status: str = "new",
    lead_score: int = 0,
    lead_source: str = "whatsapp",
    province: str = "",
    city: str = "",
    tags: List[str] = None,
    business_id: uuid.UUID = None,
) -> Contact:
    """Create a new contact with deduplication by phone number."""
    
    # Normalize phone number
    normalized_phone = normalize_sa_phone(whatsapp_number)
    
    # Get or create business
    if not business_id:
        business = get_or_create_business(db)
        business_id = business.id
    
    # Check for existing contact
    existing = db.query(Contact).filter(
        Contact.whatsapp_number == normalized_phone,
        Contact.business_id == business_id,
    ).first()
    
    if existing:
        # Update existing contact
        if first_name:
            existing.first_name = first_name
        if last_name:
            existing.last_name = last_name
        if display_name:
            existing.display_name = display_name
        if email:
            existing.email = email
        if lead_source:
            existing.lead_source = lead_source
        if province:
            existing.province = province
        if city:
            existing.city = city
        if lead_score > existing.lead_score:
            existing.lead_score = lead_score
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new contact
    contact = Contact(
        business_id=business_id,
        whatsapp_number=normalized_phone,
        first_name=first_name,
        last_name=last_name,
        display_name=display_name or f"{first_name} {last_name}".strip(),
        email=email,
        lead_status=lead_status,
        lead_score=lead_score,
        lead_source=lead_source,
        province=province,
        city=city,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    
    # Add tags if provided
    if tags:
        for tag_name in tags:
            add_tag_to_contact(db, contact.id, tag_name, business_id)
    
    return contact


def get_contact(db: Session, contact_id: str) -> Optional[Contact]:
    """Get a contact by ID."""
    try:
        contact_uuid = uuid.UUID(contact_id) if isinstance(contact_id, str) else contact_id
    except (ValueError, AttributeError):
        return None
    return db.query(Contact).filter(Contact.id == contact_uuid).first()


def get_contact_by_phone(db: Session, phone: str, business_id: uuid.UUID = None) -> Optional[Contact]:
    """Get a contact by phone number."""
    normalized = normalize_sa_phone(phone)
    query = db.query(Contact).filter(Contact.whatsapp_number == normalized)
    if business_id:
        query = query.filter(Contact.business_id == business_id)
    return query.first()


def update_contact(db: Session, contact_id: str, updates: Dict) -> Optional[Contact]:
    """Update a contact."""
    try:
        contact_uuid = uuid.UUID(contact_id) if isinstance(contact_id, str) else contact_id
    except (ValueError, AttributeError):
        return None
    contact = db.query(Contact).filter(Contact.id == contact_uuid).first()
    if not contact:
        return None
    
    for key, value in updates.items():
        if hasattr(contact, key) and key not in ("id", "created_at", "updated_at"):
            setattr(contact, key, value)
    
    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact_id: str) -> bool:
    """Delete a contact and its associated records."""
    try:
        contact_uuid = uuid.UUID(contact_id) if isinstance(contact_id, str) else contact_id
    except (ValueError, AttributeError):
        return False
    contact = db.query(Contact).filter(Contact.id == contact_uuid).first()
    if not contact:
        return False
    
    # Delete contact tags
    db.query(ContactTag).filter(ContactTag.contact_id == contact_uuid).delete()
    
    # Delete contact
    db.delete(contact)
    db.commit()
    return True


def list_contacts(
    db: Session,
    business_id: uuid.UUID = None,
    search: str = None,
    lead_status: str = None,
    tag: str = None,
    page: int = 1,
    limit: int = 20,
) -> Tuple[List[Contact], int]:
    """List contacts with filtering and pagination. Returns (contacts, total)."""
    
    query = db.query(Contact)
    
    if business_id:
        query = query.filter(Contact.business_id == business_id)
    
    if search:
        safe_search = re.sub(r"[%_\\]", "", search)[:100]
        query = query.filter(
            or_(
                Contact.first_name.ilike(f"%{safe_search}%"),
                Contact.last_name.ilike(f"%{safe_search}%"),
                Contact.whatsapp_number.ilike(f"%{safe_search}%"),
                Contact.display_name.ilike(f"%{safe_search}%"),
                Contact.email.ilike(f"%{safe_search}%"),
            )
        )
    
    if lead_status:
        query = query.filter(Contact.lead_status == lead_status)
    
    if tag:
        # Join through ContactTag to filter by tag name
        query = query.join(ContactTag).join(Tag).filter(Tag.name == tag)
    
    total = query.count()
    offset = (page - 1) * limit
    contacts = query.order_by(Contact.created_at.desc()).offset(offset).limit(limit).all()
    
    return contacts, total


def import_contacts_from_csv(
    db: Session,
    contacts_data: List[Dict],
    business_id: uuid.UUID = None,
) -> Dict:
    """Import contacts from parsed CSV data. Returns summary."""
    
    if not business_id:
        business = get_or_create_business(db)
        business_id = business.id
    
    results = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }
    
    for i, row in enumerate(contacts_data):
        try:
            phone = row.get("whatsapp_number") or row.get("phone") or row.get("mobile", "")
            if not phone:
                results["errors"].append({"row": i + 1, "error": "Missing phone number"})
                results["skipped"] += 1
                continue
            
            contact = create_contact(
                db=db,
                whatsapp_number=phone,
                first_name=row.get("first_name", row.get("name", "")),
                last_name=row.get("last_name", ""),
                display_name=row.get("display_name", ""),
                email=row.get("email", ""),
                lead_source=row.get("lead_source", "csv_import"),
                province=row.get("province", ""),
                city=row.get("city", ""),
                tags=[t.strip() for t in row.get("tags", "").split(",") if t.strip()] if row.get("tags") else [],
                business_id=business_id,
            )
            
            # Check if this was a new or existing contact
            if contact.created_at.date() == datetime.utcnow().date():
                results["created"] += 1
            else:
                results["updated"] += 1
                
        except Exception as e:
            results["errors"].append({"row": i + 1, "error": str(e)})
            results["skipped"] += 1
    
    return results


# ─── Tag Management ──────────────────────────────────────────

def create_tag(
    db: Session,
    name: str,
    color: str = "#3B82F6",
    business_id: uuid.UUID = None,
) -> Tag:
    """Create a new tag."""
    if not business_id:
        business = get_or_create_business(db)
        business_id = business.id
    
    tag = Tag(
        business_id=business_id,
        name=name,
        color=color,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def get_or_create_tag(
    db: Session,
    name: str,
    color: str = "#3B82F6",
    business_id: uuid.UUID = None,
) -> Tag:
    """Get an existing tag or create it."""
    if not business_id:
        business = get_or_create_business(db)
        business_id = business.id
    
    tag = db.query(Tag).filter(
        Tag.name == name,
        Tag.business_id == business_id,
    ).first()
    
    if not tag:
        tag = create_tag(db, name, color, business_id)
    
    return tag


def add_tag_to_contact(
    db: Session,
    contact_id: uuid.UUID,
    tag_name: str,
    business_id: uuid.UUID = None,
    color: str = "#3B82F6",
) -> bool:
    """Add a tag to a contact."""
    tag = get_or_create_tag(db, tag_name, color, business_id)
    
    existing = db.query(ContactTag).filter(
        ContactTag.contact_id == contact_id,
        ContactTag.tag_id == tag.id,
    ).first()
    
    if existing:
        return False
    
    contact_tag = ContactTag(contact_id=contact_id, tag_id=tag.id)
    db.add(contact_tag)
    
    # Increment usage count
    tag.usage_count = (tag.usage_count or 0) + 1
    
    db.commit()
    return True


def list_tags(db: Session, business_id: uuid.UUID = None) -> List[Tag]:
    """List all tags for a business."""
    query = db.query(Tag)
    if business_id:
        query = query.filter(Tag.business_id == business_id)
    return query.order_by(Tag.name).all()


def get_contact_tags(db: Session, contact_id) -> List[Tag]:
    """Get all tags for a contact."""
    try:
        contact_uuid = uuid.UUID(str(contact_id)) if not isinstance(contact_id, uuid.UUID) else contact_id
    except (ValueError, AttributeError):
        return []
    return (
        db.query(Tag)
        .join(ContactTag)
        .filter(ContactTag.contact_id == contact_uuid)
        .all()
    )
