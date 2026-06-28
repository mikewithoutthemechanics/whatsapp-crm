"""
WhatsApp CRM SA — FastAPI Application Routes
============================================
REST API endpoints for the WhatsApp CRM.
Wired to real SQLAlchemy database queries.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query, UploadFile, File
import re
import csv
import io
from typing import Optional, List
from datetime import datetime, timedelta
import json
import os

from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import (
    Business, Contact, Conversation, Message, Campaign,
    Tag, ContactTag, CampaignSubscriber, MessageTemplate,
)
from app.services.whatsapp_service import WhatsAppService, WhatsAppServiceError
from app.services.ai_service import AIEngine
from app.services.campaign_service import DripCampaignEngine
from app.services.contact_service import (
    create_contact as svc_create_contact,
    get_contact as svc_get_contact,
    update_contact as svc_update_contact,
    delete_contact as svc_delete_contact,
    list_contacts as svc_list_contacts,
    import_contacts_from_csv,
    normalize_sa_phone,
    get_or_create_business,
    create_tag as svc_create_tag,
    list_tags as svc_list_tags,
    add_tag_to_contact,
)
from app.services.lead_service import (
    capture_lead,
    get_lead_pipeline,
    get_lead_stats,
)
from app.config import settings

# Initialize services
whatsapp = WhatsAppService()
ai_engine = AIEngine()
campaign_engine = DripCampaignEngine()

# Router instances
contacts_router = APIRouter(prefix="/api/contacts", tags=["contacts"])
conversations_router = APIRouter(prefix="/api/conversations", tags=["conversations"])
messages_router = APIRouter(prefix="/api/messages", tags=["messages"])
campaigns_router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])
ai_router = APIRouter(prefix="/api/ai", tags=["ai"])
dashboard_router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
webhook_router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
leads_router = APIRouter(prefix="/api/leads", tags=["leads"])


# ─── Pydantic Validation Models ────────────────────────────────────────

class ContactCreate(BaseModel):
    whatsapp_number: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    display_name: Optional[str] = ""
    email: Optional[str] = ""
    lead_status: str = "new"
    lead_score: int = 0
    lead_source: str = "whatsapp"
    tags: List[str] = []
    province: Optional[str] = ""
    city: Optional[str] = ""

    @field_validator("whatsapp_number")
    @classmethod
    def validate_whatsapp_number(cls, v):
        cleaned = re.sub(r"[^\d]", "", v)
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError("Invalid WhatsApp number format")
        return cleaned

    @field_validator("lead_score")
    @classmethod
    def validate_lead_score(cls, v):
        if v < 0 or v > 100:
            raise ValueError("Lead score must be between 0 and 100")
        return v


class LeadCapture(BaseModel):
    whatsapp_number: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    email: Optional[str] = ""
    message: Optional[str] = ""
    source: str = "website"
    utm_source: Optional[str] = ""
    utm_medium: Optional[str] = ""
    utm_campaign: Optional[str] = ""
    province: Optional[str] = ""
    city: Optional[str] = ""

    @field_validator("whatsapp_number")
    @classmethod
    def validate_whatsapp_number(cls, v):
        cleaned = re.sub(r"[^\d]", "", v)
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError("Invalid WhatsApp number format")
        return cleaned


class MessageSend(BaseModel):
    to: str
    content: str
    type: str = "text"

    @field_validator("to")
    @classmethod
    def validate_to_number(cls, v):
        cleaned = re.sub(r"[^\d]", "", v)
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError("Invalid phone number format")
        return cleaned


class QuickReply(BaseModel):
    reply_key: str
    to: str


def _sanitize_search_query(query: str) -> str:
    """Sanitize search query to prevent injection attacks."""
    sanitized = re.sub(r"[%_\\]", "", query)
    return sanitized[:100]


# ─── Contacts Endpoints ──────────────────────────────────────

@contacts_router.get("/")
async def list_contacts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    lead_status: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List contacts with filtering and pagination."""
    contacts, total = svc_list_contacts(
        db=db,
        search=search,
        lead_status=lead_status,
        tag=tag,
        page=page,
        limit=limit,
    )
    
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    
    return {
        "data": [
            {
                "id": str(c.id),
                "whatsapp_number": c.whatsapp_number,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "display_name": c.display_name,
                "email": c.email,
                "lead_status": c.lead_status,
                "lead_score": c.lead_score,
                "lead_source": c.lead_source,
                "province": c.province,
                "city": c.city,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in contacts
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
        },
    }


@contacts_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_contact(contact_data: ContactCreate, db: Session = Depends(get_db)):
    """Create a new contact."""
    contact = svc_create_contact(
        db=db,
        whatsapp_number=contact_data.whatsapp_number,
        first_name=contact_data.first_name,
        last_name=contact_data.last_name,
        display_name=contact_data.display_name,
        email=contact_data.email,
        lead_status=contact_data.lead_status,
        lead_score=contact_data.lead_score,
        lead_source=contact_data.lead_source,
        province=contact_data.province,
        city=contact_data.city,
        tags=contact_data.tags,
    )
    
    return {
        "success": True,
        "data": {
            "id": str(contact.id),
            "whatsapp_number": contact.whatsapp_number,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "display_name": contact.display_name,
            "email": contact.email,
            "lead_status": contact.lead_status,
            "lead_score": contact.lead_score,
            "lead_source": contact.lead_source,
            "created_at": contact.created_at.isoformat() if contact.created_at else None,
        },
    }


# ─── Tags Endpoints (must be before /{contact_id} to avoid route conflict) ──

@contacts_router.get("/tags")
async def list_tags(search: Optional[str] = None, db: Session = Depends(get_db)):
    """List available tags for filtering contacts."""
    tags = svc_list_tags(db)
    
    if search:
        tags = [t for t in tags if search.lower() in t.name.lower()]
    
    return {
        "data": [
            {
                "id": str(t.id),
                "name": t.name,
                "color": t.color,
                "usage_count": t.usage_count or 0,
            }
            for t in tags
        ],
    }


@contacts_router.post("/tags")
async def create_tag(name: str, color: str = "#3B82F6", db: Session = Depends(get_db)):
    """Create a new tag."""
    tag = svc_create_tag(db, name, color)
    return {"success": True, "id": str(tag.id), "name": tag.name, "color": tag.color}


@contacts_router.get("/{contact_id}")
async def get_contact(contact_id: str, db: Session = Depends(get_db)):
    """Get a single contact by ID."""
    contact = svc_get_contact(db, contact_id)
    if not contact:
        raise HTTPException(404, "Contact not found")
    
    return {
        "id": str(contact.id),
        "whatsapp_number": contact.whatsapp_number,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "display_name": contact.display_name,
        "email": contact.email,
        "lead_status": contact.lead_status,
        "lead_score": contact.lead_score,
        "lead_source": contact.lead_source,
        "province": contact.province,
        "city": contact.city,
        "preferred_language": contact.preferred_language,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
        "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
    }


@contacts_router.put("/{contact_id}")
async def update_contact(contact_id: str, updates: dict, db: Session = Depends(get_db)):
    """Update a contact."""
    contact = svc_update_contact(db, contact_id, updates)
    if not contact:
        raise HTTPException(404, "Contact not found")
    
    return {
        "success": True,
        "id": str(contact.id),
        "updated": {
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "display_name": contact.display_name,
            "email": contact.email,
            "lead_status": contact.lead_status,
            "lead_score": contact.lead_score,
        },
    }


@contacts_router.delete("/{contact_id}")
async def delete_contact(contact_id: str, db: Session = Depends(get_db)):
    """Delete a contact."""
    success = svc_delete_contact(db, contact_id)
    if not success:
        raise HTTPException(404, "Contact not found")
    
    return {"success": True, "deleted": contact_id}


@contacts_router.post("/import")
async def import_contacts(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import contacts from CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "File must be a CSV")
    
    contents = await file.read()
    text = contents.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    
    contacts_data = list(reader)
    if not contacts_data:
        raise HTTPException(400, "No contacts found in CSV")
    
    results = import_contacts_from_csv(db, contacts_data)
    
    return {
        "success": True,
        "imported": results["created"] + results["updated"],
        "created": results["created"],
        "updated": results["updated"],
        "skipped": results["skipped"],
        "errors": results["errors"],
    }


# ─── Conversations Endpoints ──────────────────────────────────

@conversations_router.get("/")
async def list_conversations(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """List conversations with filters."""
    query = db.query(Conversation)
    
    if status:
        query = query.filter(Conversation.status == status)
    if priority:
        query = query.filter(Conversation.priority == priority)
    
    total = query.count()
    offset = (page - 1) * limit
    conversations = query.order_by(Conversation.last_message_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "data": [
            {
                "id": str(c.id),
                "contact_id": str(c.contact_id),
                "status": c.status,
                "priority": c.priority,
                "category": c.category,
                "channel": c.channel,
                "ai_handled": c.ai_handled,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in conversations
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0,
        },
    }


@conversations_router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Get conversation details with messages."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    
    return {
        "id": str(conversation.id),
        "contact_id": str(conversation.contact_id),
        "status": conversation.status,
        "priority": conversation.priority,
        "category": conversation.category,
        "channel": conversation.channel,
        "ai_handled": conversation.ai_handled,
        "messages": [
            {
                "id": str(m.id),
                "sent_by": m.sent_by,
                "message_type": m.message_type,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
    }


@conversations_router.put("/{conversation_id}/status")
async def update_conversation_status(conversation_id: str, status: str, db: Session = Depends(get_db)):
    """Update conversation status."""
    valid_statuses = ["open", "pending", "resolved", "closed"]
    if status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")
    
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    
    conversation.status = status
    db.commit()
    
    return {"success": True, "id": conversation_id, "status": status}


@conversations_router.put("/{conversation_id}/assign")
async def assign_conversation(conversation_id: str, agent_id: str, db: Session = Depends(get_db)):
    """Assign conversation to an agent."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    
    from app.models import TeamMember
    agent = db.query(TeamMember).filter(TeamMember.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    conversation.assigned_to = agent_id
    db.commit()
    
    return {"success": True, "id": conversation_id, "assigned_to": agent_id}


@conversations_router.post("/{conversation_id}/notes")
async def add_conversation_note(conversation_id: str, note: dict, db: Session = Depends(get_db)):
    """Add a note to a conversation."""
    from app.models import ConversationNote, TeamMember
    
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    
    # Get or create a default agent
    agent = db.query(TeamMember).first()
    if not agent:
        agent = TeamMember(name="System", role="admin")
        db.add(agent)
        db.commit()
        db.refresh(agent)
    
    note_record = ConversationNote(
        conversation_id=conversation_id,
        author_id=agent.id,
        content=note.get("content", ""),
        is_internal=note.get("is_internal", True),
    )
    db.add(note_record)
    db.commit()
    
    return {"success": True, "note_id": str(note_record.id)}


# ─── Messages Endpoints ──────────────────────────────────────

@messages_router.post("/send")
async def send_reply(conversation_id: str, message: dict, db: Session = Depends(get_db)):
    """Send a reply to a conversation via WhatsApp."""
    to_number = message.get("to", "")
    content = message.get("content", "")
    message_type = message.get("type", "text")

    if not to_number or not content:
        raise HTTPException(400, "to and content are required")

    if message_type == "text":
        result = whatsapp.send_text(to_number, content)
    else:
        result = whatsapp.send_message(to_number, {"type": message_type, **message})

    if not result.get("success"):
        raise HTTPException(500, f"Send failed: {result.get('error')}")

    # Persist the message
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        msg = Message(
            conversation_id=conversation_id,
            sent_by="agent",
            message_type=message_type,
            content=content,
            whatsapp_message_id=result.get("message_id"),
        )
        db.add(msg)
        conversation.last_message_at = datetime.utcnow()
        db.commit()

    return {"success": True, "whatsapp_response": result}


@messages_router.post("/quick-reply")
async def send_quick_reply(conversation_id: str, data: dict, db: Session = Depends(get_db)):
    """Send a predefined quick reply."""
    quick_replies = {
        "greeting": "Hello! Welcome to our business. How can I help you today?",
        "thanks": "You're welcome! Feel free to reach out anytime you need help.",
        "pricing": "I'd be happy to help with pricing! Could you tell me what service you're interested in so I can give you an accurate quote?",
        "hours": "Our business hours are Mon-Fri, 8:00 AM - 6:00 PM SAST. We'll respond as soon as possible!",
        "location": "We're based in Johannesburg, Gauteng. We offer services across South Africa!",
        "follow_up": "Just following up on our conversation. Are you still interested in our services?",
        "goodbye": "Thank you for chatting with us! Have a wonderful day!",
    }

    reply_key = data.get("reply_key", "greeting")
    to_number = data.get("to", "")

    if reply_key not in quick_replies:
        raise HTTPException(400, f"Unknown reply key: {reply_key}")

    result = whatsapp.send_text(to_number, quick_replies[reply_key])

    if not result.get("success"):
        raise HTTPException(500, f"Send failed: {result.get('error')}")

    return {"success": True, "reply": quick_replies[reply_key]}


# ─── AI Endpoints ─────────────────────────────────────────────

@ai_router.post("/generate-reply")
async def ai_generate_reply(message: str, context: Optional[dict] = None):
    """Generate an AI-powered reply to a customer message."""
    ctx = context or {}
    reply = ai_engine.generate_response(message, ctx)
    intent = ai_engine.detect_intent(message)

    return {
        "reply": reply,
        "intent": intent,
        "after_hours": ai_engine.is_after_hours(),
    }


@ai_router.post("/detect-intent")
async def ai_detect_intent(message: str):
    """Detect the intent of a customer message."""
    intent = ai_engine.detect_intent(message)
    return {"intent": intent}


@ai_router.get("/stats")
async def ai_stats():
    """Get AI usage statistics."""
    return {
        "provider": ai_engine.provider,
        "request_counts": ai_engine.request_counts,
    }


# ─── Campaigns Endpoints ─────────────────────────────────────

@campaigns_router.get("/")
async def list_campaigns(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List campaigns."""
    query = db.query(Campaign)
    if status:
        query = query.filter(Campaign.status == status)
    
    campaigns = query.order_by(Campaign.created_at.desc()).all()
    
    return {
        "data": [
            {
                "id": str(c.id),
                "name": c.name,
                "campaign_type": c.campaign_type,
                "trigger_event": c.trigger_event,
                "status": c.status,
                "sent_count": c.sent_count,
                "delivered_count": c.delivered_count,
                "replied_count": c.replied_count,
                "active_subscribers": c.active_subscribers,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in campaigns
        ],
    }


@campaigns_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_campaign(campaign_data: dict, db: Session = Depends(get_db)):
    """Create a new drip campaign."""
    business = get_or_create_business(db)
    campaign = Campaign(
        business_id=business.id,
        name=campaign_data.get("name", ""),
        campaign_type=campaign_data.get("campaign_type", "drip"),
        trigger_event=campaign_data.get("trigger_event", "new_lead"),
        trigger_delay_hours=campaign_data.get("trigger_delay_hours", 0),
        messages_sequence=campaign_data.get("messages_sequence", []),
        target_audience=campaign_data.get("target_audience", "all"),
        status="draft",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    return {
        "success": True,
        "data": {
            "id": str(campaign.id),
            "name": campaign.name,
            "campaign_type": campaign.campaign_type,
            "trigger_event": campaign.trigger_event,
            "status": campaign.status,
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        },
    }


@campaigns_router.post("/{campaign_id}/activate")
async def activate_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """Activate a campaign."""
    try:
        camp_uuid = __import__("uuid").UUID(campaign_id)
    except (ValueError, AttributeError):
        raise HTTPException(400, "Invalid campaign ID")
    campaign = db.query(Campaign).filter(Campaign.id == camp_uuid).first()
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    
    campaign.status = "active"
    db.commit()
    
    return {"success": True, "campaign_id": campaign_id, "status": "active"}


@campaigns_router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """Pause a campaign."""
    try:
        camp_uuid = __import__("uuid").UUID(campaign_id)
    except (ValueError, AttributeError):
        raise HTTPException(400, "Invalid campaign ID")
    campaign = db.query(Campaign).filter(Campaign.id == camp_uuid).first()
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    
    campaign.status = "paused"
    db.commit()
    
    return {"success": True, "campaign_id": campaign_id, "status": "paused"}


@campaigns_router.post("/{campaign_id}/add-subscriber")
async def add_subscriber(campaign_id: str, contact_id: str,
                        delay_hours: int = Query(0, ge=0),
                        db: Session = Depends(get_db)):
    """Add a contact as a campaign subscriber."""
    import uuid as _uuid
    from datetime import datetime, timedelta
    
    try:
        camp_uuid = _uuid.UUID(campaign_id)
        cont_uuid = _uuid.UUID(contact_id)
    except (ValueError, AttributeError):
        raise HTTPException(400, "Invalid ID format")
    
    campaign = db.query(Campaign).filter(Campaign.id == camp_uuid).first()
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    
    contact = db.query(Contact).filter(Contact.id == cont_uuid).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    
    # Check if already subscribed
    existing = db.query(CampaignSubscriber).filter(
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
        next_send_at=datetime.utcnow() + timedelta(hours=delay_hours),
        status="active",
    )
    db.add(subscriber)
    
    campaign.active_subscribers = (campaign.active_subscribers or 0) + 1
    db.commit()
    
    return {"success": True}


@campaigns_router.post("/{campaign_id}/unsubscribe")
async def unsubscribe(campaign_id: str, contact_id: str, db: Session = Depends(get_db)):
    """Unsubscribe a contact from a campaign."""
    import uuid as _uuid
    try:
        camp_uuid = _uuid.UUID(campaign_id)
        cont_uuid = _uuid.UUID(contact_id)
    except (ValueError, AttributeError):
        raise HTTPException(400, "Invalid ID format")
    
    subscriber = db.query(CampaignSubscriber).filter(
        CampaignSubscriber.campaign_id == camp_uuid,
        CampaignSubscriber.contact_id == cont_uuid,
    ).first()
    
    if not subscriber:
        raise HTTPException(404, "Subscription not found")
    
    subscriber.status = "unsubscribed"
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if campaign and campaign.active_subscribers > 0:
        campaign.active_subscribers -= 1
    db.commit()
    
    return {"success": True}


@campaigns_router.post("/broadcast")
async def send_broadcast(message: str, tag_ids: List[str] = Query(None),
                         industry_filter: Optional[str] = None,
                         db: Session = Depends(get_db)):
    """Send a broadcast message to a targeted audience."""
    query = db.query(Contact)
    
    if tag_ids:
        query = query.join(ContactTag).filter(ContactTag.tag_id.in_(tag_ids))
    
    if industry_filter:
        query = query.filter(Contact.lead_source == industry_filter)
    
    contacts = query.all()
    sent = 0
    failed = 0
    
    for contact in contacts:
        try:
            if contact.whatsapp_number:
                result = whatsapp.send_text(contact.whatsapp_number, message)
                if result.get("success"):
                    sent += 1
                else:
                    failed += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    
    return {"success": True, "sent": sent, "failed": failed, "total": len(contacts)}


# ─── Dashboard Endpoints ─────────────────────────────────────

@dashboard_router.get("/summary")
async def dashboard_summary(db: Session = Depends(get_db)):
    """Get dashboard summary statistics."""
    today = datetime.utcnow().date()
    
    total_conversations = db.query(Conversation).count()
    active_conversations = db.query(Conversation).filter(
        Conversation.status.in_(["open", "pending"])
    ).count()
    
    ai_handled = db.query(Conversation).filter(Conversation.ai_handled == True).count()
    
    messages_today = db.query(Message).filter(
        Message.created_at >= datetime.combine(today, datetime.min.time())
    ).count()
    
    new_leads_today = db.query(Contact).filter(
        Contact.created_at >= datetime.combine(today, datetime.min.time())
    ).count()
    
    converted_leads = db.query(Contact).filter(
        Contact.lead_status == "converted"
    ).count()
    
    active_campaigns = db.query(Campaign).filter(Campaign.status == "active").count()
    campaign_subscribers = db.query(CampaignSubscriber).filter(
        CampaignSubscriber.status == "active"
    ).count()
    
    return {
        "total_contacts": db.query(Contact).count(),
        "total_conversations": total_conversations,
        "active_conversations": active_conversations,
        "ai_handled": ai_handled,
        "messages_today": messages_today,
        "new_leads_today": new_leads_today,
        "converted_leads": converted_leads,
        "ai_requests_today": {
            "groq": ai_engine.request_counts["groq"],
            "openrouter": ai_engine.request_counts["openrouter"],
        },
        "campaigns_active": active_campaigns,
        "campaign_subscribers": campaign_subscribers,
    }


@dashboard_router.get("/conversations/active")
async def active_conversations(
    limit: int = Query(25),
    db: Session = Depends(get_db),
):
    """Get active conversations for the agent dashboard."""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.status.in_(["open", "pending"]))
        .order_by(Conversation.last_message_at.desc())
        .limit(limit)
        .all()
    )
    
    return {
        "data": [
            {
                "id": str(c.id),
                "contact_id": str(c.contact_id),
                "status": c.status,
                "priority": c.priority,
                "category": c.category,
                "ai_handled": c.ai_handled,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
            }
            for c in conversations
        ],
    }


@dashboard_router.get("/leads/pipeline")
async def lead_pipeline(db: Session = Depends(get_db)):
    """Get lead pipeline funnel data."""
    pipeline = get_lead_pipeline(db)
    return {"pipeline": pipeline}


# ─── Webhook Endpoints ───────────────────────────────────────

@webhook_router.post("/whatsapp")
async def whatsapp_webhook(payload: dict, db: Session = Depends(get_db)):
    """Receive and process WhatsApp webhook events."""
    result = whatsapp.process_webhook(payload)

    if result.get("status") == "received":
        sender = result.get("sender", "")
        message = result.get("message", "")
        message_type = result.get("message_type", "text")

        # Look up or create contact
        from app.services.contact_service import get_contact_by_phone
        contact = get_contact_by_phone(db, sender)
        
        if not contact:
            contact = svc_create_contact(
                db=db,
                whatsapp_number=sender,
                lead_source="whatsapp",
                lead_status="new",
            )

        # Create or update conversation
        conversation = db.query(Conversation).filter(
            Conversation.contact_id == contact.id,
            Conversation.status.in_(["open", "pending"]),
        ).first()
        
        if not conversation:
            conversation = Conversation(
                business_id=contact.business_id,
                contact_id=contact.id,
                status="open",
                channel="whatsapp",
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)

        # Store incoming message
        msg = Message(
            conversation_id=conversation.id,
            contact_id=contact.id,
            sent_by="customer",
            message_type=message_type,
            content=message,
        )
        db.add(msg)
        conversation.last_message_at = datetime.utcnow()
        db.commit()

        # If it's a greeting or new conversation, auto-reply
        intent = ai_engine.detect_intent(message)

        if intent["intent"] == "greeting" and settings.AUTO_REPLY_ENABLED:
            if not ai_engine.is_after_hours():
                reply = ai_engine.generate_response(message, {
                    "business_name": "Your Business",
                })
                whatsapp.send_text(sender, reply)

        return {"status": "processed", "webhook": result}

    return {"status": "acknowledged", "webhook": result}


@webhook_router.get("/whatsapp/verify")
async def verify_webhook(mode: str = Query(""), token: str = Query(""),
                         verify_token: str = Query(settings.SECRET_KEY)):
    """Verify WhatsApp webhook for Meta."""
    valid, code = whatsapp.verify_webhook(mode, token, verify_token)
    if valid:
        return {"status": "verified", "hub_challenge": token}
    raise HTTPException(code, "Verification failed")


# ─── Lead Capture Endpoints ──────────────────────────────────

@leads_router.post("/capture")
async def capture_new_lead(lead_data: LeadCapture, db: Session = Depends(get_db)):
    """Capture a new lead from forms, ads, or landing pages."""
    result = capture_lead(
        db=db,
        whatsapp_number=lead_data.whatsapp_number,
        first_name=lead_data.first_name,
        last_name=lead_data.last_name,
        email=lead_data.email,
        message=lead_data.message,
        source=lead_data.source,
        utm_source=lead_data.utm_source,
        utm_medium=lead_data.utm_medium,
        utm_campaign=lead_data.utm_campaign,
        province=lead_data.province,
        city=lead_data.city,
    )
    
    return result


@leads_router.get("/stats")
async def lead_stats(db: Session = Depends(get_db)):
    """Get lead statistics."""
    stats = get_lead_stats(db)
    return stats
