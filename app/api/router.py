"""
WhatsApp CRM SA — FastAPI Application Routes
============================================
REST API endpoints for the WhatsApp CRM.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query, UploadFile, File
from typing import Optional, List
from datetime import datetime, timedelta
import json
import os
import logging

from app.models import (
    Business, Contact, Conversation, Message, Campaign, Tag, MessageTemplate,
    ImportSource, ImportJob, ImportedChat,
    TheoBrand, BusinessUnit, BusinessLocation,
)
from app.services.whatsapp_service import WhatsAppService, WhatsAppServiceError
from app.services.ai_service import AIEngine
from app.services.campaign_service import DripCampaignEngine
from app.services.import_service import WhatsAppChatImportService, ImportType, ImportStatus
from app.services.business_platform import BusinessPlatformService

logger = logging.getLogger(__name__)

# DB lazy accessor — main.py sets app.main.db so this avoids circular imports
def _db():
    try:
        from app.main import db as _d
        return _d
    except Exception:
        return None


# Initialize services (WhatsApp needs no DB at init)
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
import_router = APIRouter(prefix="/api/import", tags=["import"])
business_router = APIRouter(prefix="/api/business", tags=["business"])


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
    whatsapp_number = contact_data.get("whatsapp_number", "")
    if not whatsapp_number:
        raise HTTPException(400, "WhatsApp number is required")

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
    result = whatsapp.process_webhook(payload)

    if result.get("status") == "received":
        sender = result.get("sender", "")
        message = result.get("message", "")
        message_type = result.get("message_type", "text")

        contact = {"whatsapp_number": sender, "display_name": ""}

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


# ─── Import Endpoints ────────────────────────────────────────

@import_router.get("/sources")
async def list_import_sources():
    """List configured WhatsApp chat import sources."""
    db = _db()
    if not db:
        return {"data": []}
    try:
        q = db.table("import_sources").select("*").execute()
        data = getattr(q, "data", None) or getattr(q, "_response", None)
        if hasattr(data, "data"):
            data = data.data
        rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        return {"data": [r for r in rows if r]}
    except Exception as exc:
        return {"data": [], "error": str(exc)}


@import_router.post("/sources")
async def create_import_source(source_data: dict):
    """Create a new WhatsApp import source."""
    required = ["name", "source_type"]
    for r in required:
        if r not in source_data:
            raise HTTPException(400, f"Missing required field: {r}")

    business_id = source_data.get("business_id", "default")
    payload = {
        "id": str(os.urandom(16).hex()),
        "business_id": business_id,
        "name": source_data["name"],
        "source_type": source_data["source_type"],
        "provider": source_data.get("provider", settings.WHATSAPP_PROVIDER),
        "config": source_data.get("config", {}),
        "is_active": source_data.get("is_active", True),
        "created_at": datetime.utcnow().isoformat(),
    }

    db = _db()
    if db:
        try:
            db.table("import_sources").insert(payload).execute()
        except Exception as exc:
            logger.warning("import_source insert warning: %s", exc)

    return {"success": True, "data": payload}


@import_router.get("/jobs")
async def list_import_jobs(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List past import jobs with pagination."""
    db = _db()
    if not db:
        return {"data": [], "pagination": {"page": page, "limit": limit, "total": 0}}
    try:
        q = db.table("import_jobs").select("*")
        if status:
            q = q.eq("status", status)
        if job_type:
            q = q.eq("job_type", job_type)
        q = q.order("created_at", desc=True)
        offset = (page - 1) * limit
        q = q.range(offset, offset + limit - 1)
        resp = q.execute()
        data = getattr(resp, "data", None) or getattr(resp, "_response", None)
        if hasattr(data, "data"):
            data = data.data
        rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        return {
            "data": [r for r in rows if r],
            "pagination": {"page": page, "limit": limit, "total": len(rows)},
        }
    except Exception as exc:
        return {"data": [], "pagination": {"page": page, "limit": limit, "total": 0}, "error": str(exc)}


@import_router.get("/jobs/{job_id}")
async def get_import_job(job_id: str):
    """Get details for a specific import job."""
    db = _db()
    if not db:
        return {"job_id": job_id, "status": "unknown"}
    try:
        q = db.table("import_jobs").select("*").eq("id", job_id).single().execute()
        data = getattr(q, "data", None) or getattr(q, "_response", None)
        if hasattr(data, "data"):
            data = data.data
        return data if isinstance(data, dict) else {"job_id": job_id, "error": "not found"}
    except Exception as exc:
        return {"job_id": job_id, "error": str(exc)}


@import_router.post("/chats/run", status_code=status.HTTP_202_ACCEPTED)
async def run_chat_import(import_config: dict):
    """
    Trigger a WhatsApp chat + contacts import.

    Body::
    {
      "source_id": "optional-existing-source-id",
      "import_type": "full" | "contacts_only" | "delta" | "chat_history",
      "business_id": "optional-business-id",
      "chat_limit": 50,
      "message_limit": 30,
      "dry_run": false
    }
    """
    business_id = import_config.get("business_id", "default")
    import_type = import_config.get("import_type", "full")
    chat_limit = import_config.get("chat_limit")
    message_limit = import_config.get("message_limit")
    dry_run = import_config.get("dry_run", False)
    source_id = import_config.get("source_id")

    db = _db()
    svc = WhatsAppChatImportService(
        business_id=business_id, brand_id=import_config.get("brand_id"),
        db=db, whatsapp=whatsapp,
    )

    job_info = svc.start_import_job(
        source_id=source_id,
        import_type=import_type,
        chat_limit=chat_limit,
        message_limit=message_limit,
        dry_run=dry_run,
    )
    return {"status": "queued", **job_info}


@import_router.post("/chats/{job_id}/start")
async def start_import_job_endpoint(job_id: str):
    """Execute a queued import job."""
    db = _db()
    svc = WhatsAppChatImportService(db=db, whatsapp=whatsapp)
    result = svc.run_import_job(job_id)
    return result


@import_router.post("/contacts/import")
async def import_contacts_from_whatsapp(body: dict):
    """
    Fast-path: import contacts from current WhatsApp session.
    Body::
    {
      "business_id": "default",
      "provider": "openwa",
      "dry_run": false
    }
    """
    business_id = body.get("business_id", "default")
    dry_run = body.get("dry_run", False)

    source_payload = {
        "id": str(os.urandom(16).hex()),
        "business_id": business_id,
        "name": f"Auto-import {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        "source_type": "whatsapp",
        "provider": body.get("provider", settings.WHATSAPP_PROVIDER),
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }

    db = _db()
    if db:
        try:
            db.table("import_sources").insert(source_payload).execute()
        except Exception as exc:
            logger.warning("auto-source insert: %s", exc)

    svc = WhatsAppChatImportService(
        business_id=business_id, db=db, whatsapp=whatsapp,
    )
    result = svc.start_import_job(
        import_type=ImportType.CONTACTS_ONLY.value,
        dry_run=dry_run,
    )
    return {"status": "queued", "source": source_payload, "job": result}


@import_router.get("/history")
async def import_history(
    business_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Return imported chat history for the dashboard."""
    db = _db()
    if not db:
        return {"data": [], "pagination": {"page": 1, "limit": 20, "total": 0}}
    biz = business_id
    try:
        q = db.table("imported_chats").select("*").order("created_at", desc=True)
        if biz:
            q = q.eq("business_id", biz)
        q = q.execute()
        data = getattr(q, "data", None) or getattr(q, "_response", None)
        if hasattr(data, "data"):
            data = data.data
        rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        rows = [r for r in rows if r]
        total = len(rows)
        start = (page - 1) * limit
        return {
            "data": rows[start:start + limit],
            "pagination": {"page": page, "limit": limit, "total": total,
                           "pages": (total + limit - 1) // limit},
        }
    except Exception as exc:
        return {"data": [], "pagination": {"page": 1, "limit": 20, "total": 0}, "error": str(exc)}


# ─── Business (Theo Brand / Unit / Location) Endpoints ────────

@business_router.post("/brands", status_code=status.HTTP_201_CREATED)
async def create_brand(brand_data: dict):
    """Create a new TheoBrand business."""
    if "business_id" not in brand_data:
        brand_data["business_id"] = "default"
    bps = BusinessPlatformService(db=_db(), business_id=brand_data.get("business_id"))
    result = bps.create_brand(brand_data)
    if "error" in result and "partial" not in result:
        raise HTTPException(400, result["error"])
    return result


@business_router.get("/brands")
async def list_brands(
    business_id: Optional[str] = None,
    active_only: bool = True,
):
    """List TheoBrand business accounts."""
    bid = business_id
    bps = BusinessPlatformService(db=_db(), business_id=bid)
    return {"data": bps.list_brands(business_id=bid, active_only=active_only)}


@business_router.get("/brands/{brand_id}")
async def get_brand(brand_id: str):
    """Get a single TheoBrand with its units and locations."""
    bps = BusinessPlatformService(db=_db())
    brand = bps.get_brand(brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")
    units = bps.list_units(brand_id)
    locs = bps.list_locations(brand_id)
    brand["units"] = units
    brand["locations"] = locs
    return brand


@business_router.put("/brands/{brand_id}")
async def update_brand(brand_id: str, updates: dict):
    """Update a TheoBrand."""
    bps = BusinessPlatformService(db=_db())
    result = bps.update_brand(brand_id, updates)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@business_router.post("/brands/{brand_id}/units", status_code=status.HTTP_201_CREATED)
async def create_unit(brand_id: str, unit_data: dict):
    """Create a BusinessUnit under a TheoBrand."""
    unit_data["brand_id"] = brand_id
    unit_data["business_id"] = unit_data.get("business_id", "default")
    bps = BusinessPlatformService(db=_db(), business_id=unit_data["business_id"])
    result = bps.create_unit(unit_data)
    if "error" in result and "partial" not in result:
        raise HTTPException(400, result["error"])
    return result


@business_router.get("/brands/{brand_id}/units")
async def list_units(brand_id: str):
    """List BusinessUnits for a TheoBrand."""
    bps = BusinessPlatformService(db=_db())
    return {"data": bps.list_units(brand_id)}


@business_router.put("/units/{unit_id}")
async def update_unit(unit_id: str, updates: dict):
    """Update a BusinessUnit."""
    bps = BusinessPlatformService(db=_db())
    result = bps.update_unit(unit_id, updates)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@business_router.post("/brands/{brand_id}/locations", status_code=status.HTTP_201_CREATED)
async def create_location(brand_id: str, loc_data: dict):
    """Create a BusinessLocation under a TheoBrand."""
    loc_data["brand_id"] = brand_id
    loc_data["business_id"] = loc_data.get("business_id", "default")
    bps = BusinessPlatformService(db=_db(), business_id=loc_data["business_id"])
    result = bps.create_location(loc_data)
    if "error" in result and "partial" not in result:
        raise HTTPException(400, result["error"])
    return result


@business_router.get("/brands/{brand_id}/locations")
async def list_locations(brand_id: str, unit_id: Optional[str] = None):
    """List BusinessLocations for a TheoBrand."""
    bps = BusinessPlatformService(db=_db())
    return {"data": bps.list_locations(brand_id, unit_id=unit_id)}


@business_router.put("/locations/{location_id}")
async def update_location(location_id: str, updates: dict):
    """Update a BusinessLocation (e.g. connect a WhatsApp session)."""
    bps = BusinessPlatformService(db=_db())
    result = bps.update_location(location_id, updates)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@business_router.get("/platform/summary")
async def platform_summary(business_id: Optional[str] = None):
    """High-level Theo Business Platform summary."""
    bps = BusinessPlatformService(db=_db(), business_id=business_id)
    return bps.platform_summary()


@business_router.post("/locations/{location_id}/connect-whatsapp")
async def connect_location_whatsapp(location_id: str, body: dict):
    """
    Connect a WhatsApp session to a BusinessLocation.
    Body::
    {
      "session_id": "openwa-session-name",
      "phone_number": "27821234567",
      "provider": "openwa"
    }
    """
    bps = BusinessPlatformService(db=_db())
    result = bps.update_location(location_id, {
        "whatsapp_connected": True,
        "whatsapp_session_id": body.get("session_id", ""),
        "whatsapp_number": body.get("phone_number", ""),
    })
    if "error" in result:
        raise HTTPException(400, result["error"])
    return {"success": True, "location_id": location_id, **result["updated"]}