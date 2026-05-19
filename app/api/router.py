"""
WhatsApp CRM SA — FastAPI Application Routes
=============================================
REST API endpoints for the WhatsApp CRM.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query, UploadFile, File
from typing import Optional, List
from datetime import datetime, timedelta
import json
import os

from app.models import Business, Contact, Conversation, Message, Campaign, Tag, MessageTemplate
from app.services.whatsapp_service import WhatsAppService, WhatsAppServiceError
from app.services.ai_service import AIEngine
from app.services.campaign_service import DripCampaignEngine

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


# ─── Contacts Endpoints ──────────────────────────────────────

@contacts_router.get("/", response_model=List[dict])
async def list_contacts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    lead_status: Optional[str] = None,
    tag: Optional[str] = None
):
    """List contacts with filtering and pagination."""
    offset = (page - 1) * limit
    query = {}

    if search:
        query["or"] = [
            {"first_name": {"ilike": f"%{search}%"}},
            {"last_name": {"ilike": f"%{search}%"}},
            {"whatsapp_number": {"ilike": f"%{search}%"}},
        ]
    if lead_status:
        query["lead_status"] = lead_status

    # In a real app, this would query Supabase
    # For now, return a schema example
    return {
        "data": [],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": 0,
            "total_pages": 0,
        }
    }


@contacts_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_contact(contact_data: dict):
    """Create a new contact."""
    # Validate required fields
    whatsapp_number = contact_data.get("whatsapp_number", "")
    if not whatsapp_number:
        raise HTTPException(400, "WhatsApp number is required")

    # Normalize number
    whatsapp_number = whatsapp_number.lstrip("+")
    if whatsapp_number.startswith("0") and len(whatsapp_number) == 10:
        whatsapp_number = "27" + whatsapp_number[1:]

    contact = {
        "id": str(os.urandom(16).hex()),
        "whatsapp_number": whatsapp_number,
        "first_name": contact_data.get("first_name", ""),
        "last_name": contact_data.get("last_name", ""),
        "display_name": contact_data.get("display_name", ""),
        "email": contact_data.get("email", ""),
        "lead_status": contact_data.get("lead_status", "new"),
        "lead_score": contact_data.get("lead_score", 0),
        "lead_source": contact_data.get("lead_source", "whatsapp"),
        "tags": contact_data.get("tags", []),
        "province": contact_data.get("province", ""),
        "city": contact_data.get("city", ""),
        "created_at": datetime.utcnow().isoformat(),
    }

    return {"success": True, "data": contact}


@contacts_router.get("/{contact_id}")
async def get_contact(contact_id: str):
    """Get a single contact by ID."""
    return {"id": contact_id, "whatsapp_number": "", "display_name": ""}


@contacts_router.put("/{contact_id}")
async def update_contact(contact_id: str, updates: dict):
    """Update a contact."""
    return {"success": True, "id": contact_id, "updated": updates}


@contacts_router.delete("/{contact_id}")
async def delete_contact(contact_id: str):
    """Delete a contact."""
    return {"success": True, "deleted": contact_id}


@contacts_router.post("/import")
async def import_contacts(file: UploadFile = File(...)):
    """Import contacts from CSV file."""
    contents = await file.read()
    lines = contents.decode("utf-8").strip().split("\n")

    if not lines:
        raise HTTPException(400, "Empty file")

    # Parse CSV header
    headers = [h.strip().lower() for h in lines[0].split(",")]
    contacts = []

    for line in lines[1:]:
        values = line.split(",")
        contact = {}
        for i, header in enumerate(headers):
            if i < len(values):
                contact[header] = values[i].strip()
        contacts.append(contact)

    return {"success": True, "imported": len(contacts), "contacts": contacts}


# ─── Conversations Endpoints ──────────────────────────────────

@conversations_router.get("/", response_model=List[dict])
async def list_conversations(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50)
):
    """List conversations with filters."""
    return {
        "data": [],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": 0,
            "total_pages": 0,
        }
    }


@conversations_router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation details with messages."""
    return {
        "id": conversation_id,
        "status": "open",
        "messages": [],
        "contact": {},
        "assigned_to": None,
    }


@conversations_router.put("/{conversation_id}/status")
async def update_conversation_status(conversation_id: str, status: str):
    """Update conversation status."""
    valid_statuses = ["open", "pending", "resolved", "closed"]
    if status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")
    return {"success": True, "id": conversation_id, "status": status}


@conversations_router.put("/{conversation_id}/assign")
async def assign_conversation(conversation_id: str, agent_id: str):
    """Assign conversation to an agent."""
    return {"success": True, "id": conversation_id, "assigned_to": agent_id}


@conversations_router.post("/{conversation_id}/notes")
async def add_conversation_note(conversation_id: str, note: dict):
    """Add a note to a conversation."""
    return {"success": True, "note_id": str(os.urandom(8).hex())}


# ─── Messages Endpoints ──────────────────────────────────────

@messages_router.post("/send")
async def send_reply(conversation_id: str, message: dict):
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

    return {"success": True, "whatsapp_response": result}


@messages_router.post("/quick-reply")
async def send_quick_reply(conversation_id: str, data: dict):
    """Send a predefined quick reply."""
    quick_replies = {
        "greeting": "👋 Hello! Welcome to our business. How can I help you today?",
        "thanks": "You're welcome! Feel free to reach out anytime you need help. 😊",
        "pricing": "I'd be happy to help with pricing! Could you tell me what service you're interested in so I can give you an accurate quote?",
        "hours": "Our business hours are Mon–Fri, 8:00 AM – 6:00 PM SAST. We'll respond as soon as possible!",
        "location": "We're based in Johannesburg, Gauteng. We offer services across South Africa!",
        "follow_up": "Just following up on our conversation. Are you still interested in our services? 😊",
        "goodbye": "Thank you for chatting with us! Have a wonderful day! 👋",
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

@campaigns_router.get("/", response_model=List[dict])
async def list_campaigns(status: Optional[str] = None):
    """List campaigns."""
    return {"data": []}


@campaigns_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_campaign(campaign_data: dict):
    """Create a new drip campaign."""
    campaign = {
        "id": str(os.urandom(16).hex()),
        "name": campaign_data.get("name", ""),
        "campaign_type": campaign_data.get("campaign_type", "drip"),
        "trigger_event": campaign_data.get("trigger_event", "new_lead"),
        "trigger_delay_hours": campaign_data.get("trigger_delay_hours", 0),
        "messages_sequence": campaign_data.get("messages_sequence", []),
        "target_audience": campaign_data.get("target_audience", "all"),
        "status": "draft",
        "sent_count": 0,
        "delivered_count": 0,
        "replied_count": 0,
        "active_subscribers": 0,
        "created_at": datetime.utcnow().isoformat(),
    }

    return {"success": True, "data": campaign}


@campaigns_router.post("/{campaign_id}/activate")
async def activate_campaign(campaign_id: str):
    """Activate a campaign."""
    return {"success": True, "campaign_id": campaign_id, "status": "active"}


@campaigns_router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    """Pause a campaign."""
    return {"success": True, "campaign_id": campaign_id, "status": "paused"}


@campaigns_router.post("/{campaign_id}/add-subscriber")
async def add_subscriber(campaign_id: str, contact_id: str,
                        delay_hours: int = Query(0, ge=0)):
    """Add a contact as a campaign subscriber."""
    result = campaign_engine.add_subscriber(campaign_id, contact_id, delay_hours)

    if not result.get("success"):
        raise HTTPException(500, result.get("error", "Unknown error"))

    return result


@campaigns_router.post("/{campaign_id}/unsubscribe")
async def unsubscribe(campaign_id: str, contact_id: str):
    """Unsubscribe a contact from a campaign."""
    result = campaign_engine.unsubscribe(campaign_id, contact_id)
    return result


@campaigns_router.post("/broadcast")
async def send_broadcast(message: str, tag_ids: List[str] = Query(None),
                         industry_filter: Optional[str] = None):
    """Send a broadcast message to a targeted audience."""
    result = campaign_engine.send_broadcast(message, tag_ids, industry_filter)
    return result


# ─── Dashboard Endpoints ─────────────────────────────────────

@dashboard_router.get("/summary")
async def dashboard_summary():
    """Get dashboard summary statistics."""
    return {
        "total_conversations": 0,
        "active_conversations": 0,
        "ai_handled": 0,
        "messages_today": 0,
        "new_leads_today": 0,
        "converted_leads": 0,
        "ai_requests_today": {
            "groq": ai_engine.request_counts["groq"],
            "openrouter": ai_engine.request_counts["openrouter"],
        },
        "campaigns_active": 0,
        "campaign_subscribers": 0,
    }


@dashboard_router.get("/conversations/active")
async def active_conversations(limit: int = Query(25)):
    """Get active conversations for the agent dashboard."""
    return {"data": []}


@dashboard_router.get("/leads/pipeline")
async def lead_pipeline():
    """Get lead pipeline funnel data."""
    statuses = ["new", "contacted", "qualified", "converted", "inactive"]
    pipeline = {status: {"count": 0, "contacts": []} for status in statuses}
    return {"pipeline": pipeline}


# ─── Webhook Endpoints ───────────────────────────────────────

@webhook_router.post("/whatsapp")
async def whatsapp_webhook(payload: dict):
    """Receive and process WhatsApp webhook events."""
    # Verify webhook signature (Meta)
    result = whatsapp.process_webhook(payload)

    if result.get("status") == "received":
        sender = result.get("sender", "")
        message = result.get("message", "")
        message_type = result.get("message_type", "text")

        # Look up or create contact
        contact = {"whatsapp_number": sender, "display_name": ""}

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


# ─── Tags Endpoints ──────────────────────────────────────────

@contacts_router.get("/tags")
async def list_tags(search: Optional[str] = None):
    """List available tags for filtering contacts."""
    return {"data": []}


@contacts_router.post("/tags")
async def create_tag(name: str, color: str = "#3B82F6"):
    """Create a new tag."""
    return {"success": True, "id": str(os.urandom(8).hex()), "name": name, "color": color}