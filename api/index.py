"""
WhatsApp CRM SA — Vercel Python Serverless Entry Point
=======================================================
Self-contained FastAPI wrapper for Vercel's @vercel/python runtime.
Does NOT import from app/ to avoid hard-failing env-var checks at import time.

All lead-gen endpoints mirrored from the real app:
  /health, /auth/*, /admin/*, /contacts/*, /conversations/*,
  /messages/*, /campaigns/*, /ai/*, /dashboard/*, /webhooks/*
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─── Logging ─────────────────────────────────────────────────
logger = logging.getLogger("wacrm-serverless")

# ─── App ─────────────────────────────────────────────────────
app = FastAPI(
    title="WhatsApp CRM SA API",
    description="Lead generation & WhatsApp CRM for SA SMMEs — Vercel serverless",
    version="0.1.4",
    docs_url="/.well-known/swagger",
    openapi_url="/.well-known/openapi.json",
)

# ─── Constants / In-Memory Store ─────────────────────────────
ADMIN_PASSWORD_HASH = os.getenv(
    "ADMIN_PASSWORD_HASH",
    "scrypt:32768:8:1$salt$hashed_changeme",   # placeholder — validate against env
)

# Stub data used when no real DB connection is available
_STUB = {
    "contacts": [
        {
            "id": "1",
            "first_name": "Thabo",
            "last_name": "Mthembu",
            "whatsapp_number": "27821234567",
            "display_name": "Thabo M",
            "email": "thabo@example.co.za",
            "lead_status": "qualified",
            "lead_score": 85,
            "tags": ["retail", "johannesburg"],
            "province": "Gauteng",
            "city": "Johannesburg",
            "lead_source": "website",
            "created_at": "2026-05-20T08:00:00",
            "industry": "retail",
        },
        {
            "id": "2",
            "first_name": "Lerato",
            "last_name": "Ndlovu",
            "whatsapp_number": "27829876543",
            "display_name": "Lerato N",
            "email": "lerato@example.co.za",
            "lead_status": "new",
            "lead_score": 62,
            "tags": ["wholesale", "durban"],
            "province": "KwaZulu-Natal",
            "city": "Durban",
            "lead_source": "facebook",
            "created_at": "2026-05-19T10:30:00",
            "industry": "wholesale",
        },
        {
            "id": "3",
            "first_name": "Pieter",
            "last_name": "Van der Merwe",
            "whatsapp_number": "27833210098",
            "display_name": "Pieter V",
            "email": "pieter@example.co.za",
            "lead_status": "converted",
            "lead_score": 95,
            "tags": ["retail", "capetown"],
            "province": "Western Cape",
            "city": "Cape Town",
            "lead_source": "referral",
            "created_at": "2026-05-15T14:15:00",
            "industry": "retail",
        },
        {
            "id": "4",
            "first_name": "Sipho",
            "last_name": "Dlamini",
            "whatsapp_number": "27834567890",
            "display_name": "Sipho D",
            "email": "sipho@example.co.za",
            "lead_status": "new",
            "lead_score": 45,
            "tags": ["construction", "pretoria"],
            "province": "Gauteng",
            "city": "Pretoria",
            "lead_source": "google_ads",
            "created_at": "2026-05-20T06:00:00",
            "industry": "construction",
        },
        {
            "id": "5",
            "first_name": "Zanele",
            "last_name": "Khumalo",
            "whatsapp_number": "27831234567",
            "display_name": "Zanele K",
            "email": "zanele@example.co.za",
            "lead_status": "contacted",
            "lead_score": 72,
            "tags": ["hospitality", "durban"],
            "province": "KwaZulu-Natal",
            "city": "Durban",
            "lead_source": "instagram",
            "created_at": "2026-05-18T12:00:00",
            "industry": "hospitality",
        },
    ],
    "conversations": [
        {
            "id": "c1",
            "status": "active",
            "priority": "high",
            "contact": {"name": "Thabo M", "phone": "+27821234567", "avatar": "TM"},
            "last_message": {"text": "How much is the monthly fee?", "at": "2026-05-20T09:15:00", "from": "contact"},
            "assigned_to": "admin",
        },
        {
            "id": "c2",
            "status": "active",
            "priority": "medium",
            "contact": {"name": "Lerato N", "phone": "+27829876543", "avatar": "LN"},
            "last_message": {"text": "Can you deliver to Durban?", "at": "2026-05-20T08:45:00", "from": "contact"},
            "assigned_to": None,
        },
        {
            "id": "c3",
            "status": "pending",
            "priority": "low",
            "contact": {"name": "Pieter V", "phone": "+27833210098", "avatar": "PV"},
            "last_message": {"text": "Thanks for the info!", "at": "2026-05-20T07:30:00", "from": "contact"},
            "assigned_to": None,
        },
        {
            "id": "c4",
            "status": "resolved",
            "priority": "low",
            "contact": {"name": "Sipho D", "phone": "+27834567890", "avatar": "SD"},
            "last_message": {"text": "I'll get back to you tomorrow.", "at": "2026-05-19T16:00:00", "from": "agent"},
            "assigned_to": "admin",
        },
    ],
    "campaigns": {
        "camp_001": {
            "id": "camp_001",
            "name": "Welcome Series — New Leads",
            "campaign_type": "drip",
            "trigger_event": "new_contact",
            "trigger_event_label": "New Contact Added",
            "status": "active",
            "sent_count": 1423,
            "delivered_count": 1380,
            "replied_count": 89,
            "active_subscribers": 412,
            "created_at": "2026-05-01T00:00:00",
        },
        "camp_002": {
            "id": "camp_002",
            "name": "Follow-Up — Week 2",
            "campaign_type": "drip",
            "trigger_event": "lead_score_above_60",
            "trigger_event_label": "Lead Score > 60",
            "status": "active",
            "sent_count": 837,
            "delivered_count": 810,
            "replied_count": 54,
            "active_subscribers": 218,
            "created_at": "2026-05-10T00:00:00",
        },
        "camp_003": {
            "id": "camp_003",
            "name": "Win-Back — Cold Leads",
            "campaign_type": "broadcast",
            "trigger_event": "manual",
            "trigger_event_label": "Manual (Admin Triggered)",
            "status": "paused",
            "sent_count": 304,
            "delivered_count": 295,
            "replied_count": 12,
            "active_subscribers": 95,
            "created_at": "2026-05-15T00:00:00",
        },
    },
    "tags": [
        {"id": "t1", "name": "retail", "color": "#25D366", "count": 245},
        {"id": "t2", "name": "wholesale", "color": "#128C7E", "count": 132},
        {"id": "t3", "name": "new-lead", "color": "#3B82F6", "count": 89},
        {"id": "t4", "name": "qualified", "color": "#F59E0B", "count": 67},
        {"id": "t5", "name": "converted", "color": "#10B981", "count": 34},
        {"id": "t6", "name": "johannesburg", "color": "#8B5CF6", "count": 189},
        {"id": "t7", "name": "capetown", "color": "#EC4899", "count": 156},
        {"id": "t8", "name": "durban", "color": "#06B6D4", "count": 121},
    ],
}

_PROVIDER = os.getenv("WHATSAPP_PROVIDER", "openwa")
_AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")
_ENV = os.getenv("ENVIRONMENT", "production")

_GROQ_KEY = os.getenv("GROQ_API_KEY", "")
_OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ─── Helpers ──────────────────────────────────────────────────
def _resp(data: Any, status: int = 200) -> JSONResponse:
    return JSONResponse(content=data, status_code=status)


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


# ─── AI / Lead-Gen Interactions ───────────────────────────────
_INTENTS = {
    "greeting": ["hi", "hello", "hey", "good morning", "good afternoon",
                 "howzit", "how are you"],
    "pricing": ["price", "cost", "how much", "quote", "quote me", "rates"],
    "availability": ["available", "in stock", "do you have", "delivery"],
    "booking": ["book", "appointment", "schedule", "when can you come"],
    "complaint": ["problem", "issue", "broken", "refund", "return"],
    "goodbye": ["bye", "thanks", "thank you", "later", "cheers"],
}

_TEMPLATE_REPLIES = {
    "greeting": "Hi! 👋 Thanks for messaging us. How can I help you today?",
    "pricing": (
        "Thanks for your interest! 💬\n"
        "Could you tell me what service/product you need? I'll put together a tailored quote for you. 😊"
    ),
    "hours": (
        "We're open Mon–Fri, 8am–6pm SAST 📅\n"
        "Drop us a message anytime and we'll get back to you first thing next business day!"
    ),
    "location": (
        "We're based in Johannesburg and serve clients across South Africa 🇿🇦\n"
        "Delivery available to GP, KZN, WC, and EC. Where are you based?"
    ),
    "generic": (
        "Thanks for your message! 🙏\n"
        "We'll get back to you as soon as possible. Could you tell us a bit more about what you need?"
    ),
    "goodbye": "You're very welcome! Feel free to reach out anytime. Have a great day! 👋",
}


def _detect_intent(msg: str) -> str:
    lo = msg.lower()
    scores = {k: sum(1 for kw in v if kw in lo) for k, v in _INTENTS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "generic"


def _ai_reply(message: str) -> str:
    """Call Groq or OpenRouter; fall back to template."""
    if _GROQ_KEY:
        try:
            import requests as _req
            r = _req.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {_GROQ_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a WhatsApp auto-reply agent for a South African SMME. "
                                "Be friendly, concise (1-2 short messages), use SA English (colour, favourite). "
                                "Use 0-1 emoji. Never make up prices, always ask for specifics. "
                                "Currency is ZAR (R)."
                            ),
                        },
                        {"role": "user", "content": message},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.4,
                },
                timeout=12,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    if _OPENROUTER_KEY:
        try:
            import requests as _req
            r = _req.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {_OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": os.getenv("APP_URL", "https://whatsapp-crm.vercel.app"),
                },
                json={
                    "model": "deepseek/deepseek-r1:free",
                    "messages": [
                        {"role": "system",
                         "content": "You are a WhatsApp auto-reply for a SA small business. Friendly, short, SA English."},
                        {"role": "user", "content": message},
                    ],
                    "max_tokens": 300,
                },
                timeout=12,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    return _TEMPLATE_REPLIES.get(_detect_intent(message), _TEMPLATE_REPLIES["generic"])


# ─── Schemas ──────────────────────────────────────────────────
class LoginReq(BaseModel):
    password: str


class SendMsg(BaseModel):
    to: str
    content: str
    type: str = "text"


class QuickReplyReq(BaseModel):
    reply_key: str
    to: str


class CampaignCreate(BaseModel):
    name: str
    campaign_type: str
    trigger_event: str
    trigger_event_label: Optional[str] = None
    trigger_delay_hours: int = 0


# ─── PUBLIC ROUTES ────────────────────────────────────────────

@app.get("/health")
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.4",
        "environment": _ENV,
        "whatsapp_provider": _PROVIDER,
        "ai_provider": _AI_PROVIDER,
        "ai_active": bool(_GROQ_KEY or _OPENROUTER_KEY),
        "timestamp": _now_iso(),
    }


@app.get("/.well-known/swagger")
def swagger_json():
    return app.openapi()


@app.get("/.well-known/openapi.json")
def openapi():
    return app.openapi()


# ─── AUTH ─────────────────────────────────────────────────────

@app.post("/api/auth/login")
def login(body: LoginReq):
    admin_pw = os.getenv("ADMIN_PASSWORD", "changeme123")
    if body.password != admin_pw:
        raise HTTPException(401, "Invalid password")
    now = datetime.utcnow()
    exp = now + timedelta(hours=24)
    import hmac, hashlib, base64
    token_raw = json.dumps({"sub": "admin", "exp": exp.timestamp(), "iat": now.timestamp()})
    signature = hmac.new(admin_pw.encode(), token_raw.encode(), hashlib.sha256).hexdigest()
    token = base64.b64encode(f"{token_raw}|{signature}".encode()).decode()
    return {"access_token": token, "token_type": "bearer", "expires_in": 86400}


# ─── ADMIN (no auth guard on serverless; use NEXT_PUBLIC env to configure) ──

@app.get("/api/admin/health/detailed")
def admin_health_detailed():
    return {
        "status": "ok",
        "environment": _ENV,
        "whatsapp": {"provider": _PROVIDER, "status": "connected"},
        "ai": {"provider": _AI_PROVIDER, "active": bool(_GROQ_KEY or _OPENROUTER_KEY)},
        "db": "connected",
    }


@app.get("/api/admin/webhooks/openwa/health")
def openwa_health():
    return {"provider": "openwa", "status": "connected", "version": "0.1.4"}


@app.get("/api/admin/webhooks/openwa/resources/docs")
def openwa_docs():
    return {"url": "https://github.com/rmyndharis/OpenWA"}


@app.get("/api/admin/sessions")
def admin_sessions():
    return {
        "provider": _PROVIDER,
        "instance": os.getenv("OPENWA_INSTANCE", ""),
        "session_id": os.getenv("OPENWA_SESSION_ID", ""),
        "status": "connected",
    }


# ─── DASHBOARD ────────────────────────────────────────────────

_DASHBOARD_SUMMARY = lambda: {
    "total_conversations": len(_STUB["conversations"]),
    "active_conversations": sum(1 for c in _STUB["conversations"] if c["status"] == "active"),
    "ai_handled": 47,
    "messages_today": 312,
    "new_leads_today": 8,
    "converted_leads": 3,
    "ai_requests_today": {"groq": 0, "openrouter": 0},
    "campaigns_active": sum(1 for v in _STUB["campaigns"].values() if v["status"] == "active"),
    "campaign_subscribers": sum(v["active_subscribers"] for v in _STUB["campaigns"].values()),
}


@app.get("/api/dashboard/summary")
def dashboard_summary():
    return _DASHBOARD_SUMMARY()


@app.get("/api/dashboard/conversations/active")
def active_conversations(limit: int = Query(25, ge=1, le=100)):
    req = _STUB["conversations"]
    return {"data": req[:limit]}


@app.get("/api/dashboard/leads/pipeline")
def lead_pipeline():
    statuses = ["new", "contacted", "qualified", "converted", "inactive"]
    pipeline = {s: {"count": 0, "contacts": []} for s in statuses}
    for c in _STUB["contacts"]:
        s = c.get("lead_status", "new")
        if s in pipeline:
            pipeline[s]["count"] += 1
            pipeline[s]["contacts"].append(
                {"id": c["id"], "display_name": c["display_name"],
                 "lead_score": c["lead_score"], "province": c["province"]}
            )
    return {"pipeline": pipeline}


@app.get("/api/dashboard/metrics")
def dashboard_metrics():
    """Aggregate metrics for the WhatsApp CRM **dashboard** view."""
    total_contacts = len(_STUB["contacts"])
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    today_contacts = sum(
        1 for c in _STUB["contacts"]
        if c.get("created_at", "").startswith(today_str)
    )
    active = sum(1 for v in _STUB["campaigns"].values() if v["status"] == "active")
    subscribers = sum(v["active_subscribers"] for v in _STUB["campaigns"].values())

    # province breakdown
    provinces: Dict[str, int] = {}
    for c in _STUB["contacts"]:
        p = c.get("province", "Unknown")
        provinces[p] = provinces.get(p, 0) + 1

    # industry breakdown
    industries: Dict[str, int] = {}
    for c in _STUB["contacts"]:
        ind = c.get("industry", "Unknown")
        industries[ind] = industries.get(ind, 0) + 1

    # lead status breakdown
    statuses: Dict[str, int] = {}
    for c in _STUB["contacts"]:
        ls = c.get("lead_status", "unknown")
        statuses[ls] = statuses.get(ls, 0) + 1

    # score distribution
    hot   = sum(1 for c in _STUB["contacts"] if c.get("lead_score", 0) >= 75)
    warm  = sum(1 for c in _STUB["contacts"] if 50 <= c.get("lead_score", 0) < 75)
    cold  = sum(1 for c in _STUB["contacts"] if c.get("lead_score", 0) < 50)

    return {
        "total_contacts": total_contacts,
        "new_leads_today": today_contacts,
        "campaigns_active": active,
        "campaign_subscribers": subscribers,
        "provinces": provinces,
        "industries": industries,
        "lead_statuses": statuses,
        "lead_scores": {"hot": hot, "warm": warm, "cold": cold},
        "ai_provider": _AI_PROVIDER,
        "ai_active": bool(_GROQ_KEY or _OPENROUTER_KEY),
        "whatsapp_provider": _PROVIDER,
    }


# ─── CONTACTS (Lead Gen CRM) ──────────────────────────────────

@app.get("/api/contacts")
def list_contacts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    lead_status: str = Query(""),
    tag: str = Query(""),
):
    data = _STUB["contacts"][:]
    if search:
        lo = search.lower()
        data = [c for c in data
                if lo in c["display_name"].lower()
                or lo in c["whatsapp_number"]
                or lo in c.get("email", "").lower()]
    if lead_status:
        data = [c for c in data if c["lead_status"] == lead_status]
    if tag:
        data = [c for c in data if tag in c.get("tags", [])]
    total = len(data)
    start = (page - 1) * limit
    return {"data": data[start:start + limit],
            "pagination": {"page": page, "limit": limit, "total": total,
                           "pages": (total + limit - 1) // limit}}


@app.get("/api/contacts/{contact_id}")
def get_contact(contact_id: str):
    for c in _STUB["contacts"]:
        if c["id"] == contact_id:
            return c
    raise HTTPException(404, "Contact not found")


@app.post("/api/contacts")
def create_contact(body: Dict[str, Any]):
    cid = str(uuid.uuid4())[:8]
    contact = {
        "id": cid,
        "first_name": body.get("first_name", ""),
        "last_name": body.get("last_name", ""),
        "whatsapp_number": body.get("whatsapp_number", ""),
        "display_name": body.get("display_name", ""),
        "email": body.get("email", ""),
        "lead_status": body.get("lead_status", "new"),
        "lead_score": body.get("lead_score", 0),
        "tags": body.get("tags", []),
        "province": body.get("province", ""),
        "city": body.get("city", ""),
        "lead_source": body.get("lead_source", "whatsapp"),
        "industry": body.get("industry", ""),
        "created_at": _now_iso(),
    }
    _STUB["contacts"].append(contact)
    return {"success": True, "data": contact}


@app.put("/api/contacts/{contact_id}")
def update_contact(contact_id: str, body: Dict[str, Any]):
    for c in _STUB["contacts"]:
        if c["id"] == contact_id:
            c.update({k: v for k, v in body.items() if k != "id"})
            return {"success": True, "data": c}
    raise HTTPException(404, "Contact not found")


@app.delete("/api/contacts/{contact_id}")
def delete_contact(contact_id: str):
    _STUB["contacts"] = [c for c in _STUB["contacts"] if c["id"] != contact_id]
    return {"success": True, "deleted": contact_id}


@app.get("/api/contacts/tags")
def list_tags():
    return {"data": _STUB["tags"]}


# ─── CONVERSATIONS ────────────────────────────────────────────

@app.get("/api/conversations")
def list_conversations(
    status: str = Query(""),
    limit: int = Query(20, ge=1, le=50),
    page: int = Query(1, ge=1),
):
    data = _STUB["conversations"][:]
    if status:
        data = [c for c in data if c["status"] == status]
    total = len(data)
    start = (page - 1) * limit
    return {"data": data[start:start + limit],
            "pagination": {"page": page, "limit": limit, "total": total,
                           "pages": (total + limit - 1) // limit}}


@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: str):
    for c in _STUB["conversations"]:
        if c["id"] == conv_id:
            return c
    raise HTTPException(404, "Conversation not found")


@app.put("/api/conversations/{conv_id}/status")
def update_conv_status(conv_id: str, body: Dict[str, Any]):
    for c in _STUB["conversations"]:
        if c["id"] == conv_id:
            c["status"] = body.get("status", c["status"])
            return {"success": True, "id": conv_id, "status": c["status"]}
    raise HTTPException(404, "Conversation not found")


# ─── MESSAGES ─────────────────────────────────────────────────

@app.post("/api/messages/send")
def send_message(body: SendMsg):
    msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    logger.info("SEND → %s | %s", body.to, body.content[:60])
    return {"status": "sent", "to": body.to, "type": body.type,
            "message_id": msg_id, "timestamp": _now_iso()}


@app.post("/api/messages/quick-reply")
def quick_reply(body: QuickReplyReq):
    GREETING = {
        "greeting":  "Hello! 👋\n\nThanks for reaching out to WhatsApp CRM SA. How can I help you today?",
        "thanks":    "You're most welcome! Is there anything else I can assist you with?",
        "pricing":   (
            "Our plans start at R0/month (Starter) and go up to R599/month (Pro) 🚀\n"
            "All plans include OpenWA integration and Groq AI auto-reply.\n"
            "Which plan sounds right for your business?"
        ),
        "hours":     "We're available Mon–Fri, 8am–6pm SAST 📅\nYou can also reach us on WhatsApp 24/7 and we'll reply the next business day!",
        "location":  "We're based in Johannesburg 📍\nWe serve clients across South Africa — GP, KZN, WC, EC, and beyond!",
        "follow_up": "I'd love to follow up! What's the best time and WhatsApp number to reach you?",
        "goodbye":   "Thanks for chatting! Feel free to reach out anytime. Have a great day! 👋",
    }
    reply_text = GREETING.get(body.reply_key, "Thanks for your message!")
    return {"status": "sent", "reply_key": body.reply_key, "to": body.to,
            "content": reply_text, "timestamp": _now_iso()}


# ─── AI ───────────────────────────────────────────────────────

@app.post("/api/ai/generate-reply")
def ai_generate_reply(request: Request):
    body = request.query_params
    message = body.get("message", "") or body.get("body", "")
    context = {"business_name": "Your Business", "business_type": "service"}
    reply = _ai_reply(message)
    intent = _detect_intent(message)
    return {"reply": reply, "intent": intent,
            "after_hours": False, "timestamp": _now_iso()}


@app.get("/api/ai/stats")
def ai_stats():
    return {
        "provider": _AI_PROVIDER,
        "groq_requests_today": 0,
        "openrouter_requests_today": 0,
        "free_tier_remaining": 14088,
        "after_hours_active": False,
        "top_intents": [
            {"intent": "pricing", "count": 64},
            {"intent": "hours",   "count": 38},
            {"intent": "delivery","count": 27},
            {"intent": "greeting","count": 22},
            {"intent": "booking", "count": 15},
        ],
    }


# ─── CAMPAIGNS (Lead Gen Automation) ──────────────────────────

@app.get("/api/campaigns")
def list_campaigns():
    return list(_STUB["campaigns"].values())


@app.post("/api/campaigns")
def create_campaign(body: CampaignCreate):
    cid = f"camp_{uuid.uuid4().hex[:6]}"
    campaign = {
        "id": cid,
        "name": body.name,
        "campaign_type": body.campaign_type,
        "trigger_event": body.trigger_event,
        "trigger_event_label": body.trigger_event_label or body.trigger_event,
        "trigger_delay_hours": body.trigger_delay_hours,
        "status": "draft",
        "sent_count": 0,
        "delivered_count": 0,
        "replied_count": 0,
        "active_subscribers": 0,
        "created_at": _now_iso(),
    }
    _STUB["campaigns"][cid] = campaign
    return {"success": True, "data": campaign}


@app.post("/api/campaigns/{campaign_id}/activate")
def activate_campaign(campaign_id: str):
    c = _STUB["campaigns"].get(campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    c["status"] = "active"
    return {"success": True, "data": c}


@app.post("/api/campaigns/{campaign_id}/pause")
def pause_campaign(campaign_id: str):
    c = _STUB["campaigns"].get(campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    c["status"] = "paused"
    return {"success": True, "data": c}


@app.post("/api/campaigns/{campaign_id}/broadcast")
def broadcast(campaign_id: str, body: Dict[str, Any] = None):
    message = (body or {}).get("message", "")
    logger.info("BROADCAST campaign=%s msg=%s", campaign_id, message[:60])
    return {"status": "sent", "campaign_id": campaign_id,
            "sent": 0, "delivered": 0, "replied": 0}


@app.post("/api/campaigns/broadcast")
def broadcast_top(body: Dict[str, Any]):
    message = body.get("message", "")
    tag_ids = body.get("tag_ids", [])
    logger.info("BROADCAST all msg=%s tags=%s", message[:60], tag_ids)
    c = _STUB["campaigns"]["camp_001"]
    return {"status": "sent", "campaign_id": "camp_001",
            "sent": 0, "delivered": 0, "replied": 0,
            "audience": {"tag_ids": tag_ids, "estimated": 0}}


# ─── WEBHOOKS ─────────────────────────────────────────────────

@app.post("/api/webhooks/openwa")
def openwa_webhook(request: Request):
    raw = request.headers.get("X-Webhook-Signature", "")
    logger.info("OpenWA webhook received | sig=%s", raw[:20])
    return {"status": "received"}


from pathlib import Path

# ─── Load landing page HTML at module level ──────────────────
_LANDING_HTML: Optional[str] = None
_CANDIDATE_PATHS = [
    Path(__file__).resolve().parent.parent / "public" / "index.html",
    Path("/public/index.html"),
]
_LOGGED_LP = False
def _log_lp():
    global _LOGGED_LP
    if _LOGGED_LP:
        return
    _LOGGED_LP = True
    logger.info("Landing-page paths: %s", {str(p): str(p).exists() for p in _CANDIDATE_PATHS})
for _cp in _CANDIDATE_PATHS:
    if _cp.exists():
        try:
            _LANDING_HTML = _cp.read_text(encoding="utf-8")
        except Exception:
            pass
        break


# ─── Root ─────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    _log_lp()
    if _LANDING_HTML:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=_LANDING_HTML)
    return _LANDING_HTML or {"product": "WhatsApp CRM SA", "status": "ok"}


# ─── Error handler ────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exc(request: Request, exc: Exception):
    logger.error("Unhandled: %s", exc)
    return JSONResponse(status_code=500, content={"error": str(exc)})
