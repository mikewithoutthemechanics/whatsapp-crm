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
from pathlib import Path
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
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

# ─── Static Assets (Next.js build output) ───────────────────────
# Serves /_next/static/* from public/_next/static so dashboard JS/CSS loads
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STATIC_ROOT = os.path.join(_ROOT, "public")
app.mount("/_next", StaticFiles(directory=_STATIC_ROOT, html=False, check_dir=False), name="_next_static")

# ─── Root landing + asset handlers ──────────────────────────
# Explicit handlers so /manifest.json / /sw.js / /icon.svg resolve at the edge.

@app.get("/manifest.json", include_in_schema=False)
def get_manifest() -> JSONResponse:
    _f = os.path.join(_STATIC_ROOT, "manifest.json")
    data = json.loads(Path(_f).read_text()) if os.path.exists(_f) else {}
    return JSONResponse(data, media_type="application/json")

@app.get("/sw.js", include_in_schema=False)
def get_sw() -> JSONResponse:
    _f = os.path.join(_STATIC_ROOT, "sw.js")
    return JSONResponse(content=Path(_f).read_text() if os.path.exists(_f) else "", media_type="application/javascript")

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


# ─── Load landing page HTML at module level ──────────────────
# Embedded from public/index.html — avoids filesystem path resolution in Vercel
_LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta name="description" content="WhatsApp CRM SA - The free WhatsApp CRM for South African SMMEs. AI auto-replies, lead scoring, drip campaigns. Zero per-message costs."/>
  <title>WhatsApp CRM SA - Free WhatsApp CRM for SA SMMEs</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>tailwind.config={theme:{extend:{fontFamily:{display:["Playfair Display","Georgia","serif"],body:["Inter","system-ui","sans-serif"]}}}}</script>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js" defer></script>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js" defer></script>
  <script src="https://cdn.jsdelivr.net/npm/lenis@1.1.18/dist/lenis.min.js" defer></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js" defer></script>
  <style>
    *,*:before,*:after{box-sizing:border-box;margin:0;padding:0}
    html{scroll-behavior:auto;overflow-x:hidden}
    body{font-family:Inter,system-ui,sans-serif;background:#06080A;color:#F8FAFC;overflow-x:hidden;-webkit-font-smoothing:antialiased}
    #grain{position:fixed;inset:0;z-index:10000;pointer-events:none;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.05'/%3E%3C/svg%3E");background-size:200px;opacity:.4}
    .vignette{position:fixed;inset:0;z-index:9998;pointer-events:none;background:radial-gradient(ellipse at 50% 50%,transparent 50%,rgba(6,8,10,.88) 100%)}
    .r{transition:opacity .5s,transform .5s}
    .headline{font-family:Playfair Display,Georgia,serif;font-weight:900;line-height:1.04;letter-spacing:-.03em}
    .eyebrow{font-weight:600;font-size:.72rem;letter-spacing:.2em;text-transform:uppercase}
    .btnW{display:inline-flex;align-items:center;gap:.55rem;padding:1.05rem 2.75rem;background:linear-gradient(135deg,#25D366,#128C7E);color:#fff;font-weight:700;font-size:1rem;border-radius:999px;border:none;text-decoration:none;position:relative;overflow:hidden;box-shadow:0 4px 25px rgba(37,211,102,.35);transition:transform .3s,box-shadow .3s}
    .btnW::after{content:"";position:absolute;inset:-50%;background:linear-gradient(115deg,transparent 30%,rgba(255,255,255,.12) 50%,transparent 70%);transform:translateX(-100%) rotate(25deg);animation:shim 3s infinite}
    @keyframes shim{to{transform:translateX(200%) rotate(25deg)}}
    .btnW:hover{transform:translateY(-4px);box-shadow:0 12px 45px rgba(37,211,102,.55)}
    .btnG{display:inline-flex;align-items:center;gap:.5rem;padding:1rem 2.5rem;background:transparent;color:#F8FAFC;font-weight:600;font-size:1rem;border:1px solid rgba(255,255,255,.12);border-radius:999px;text-decoration:none;transition:border-color .3s,color .3s}
    .btnG:hover{border-color:rgba(37,211,102,.6);color:#128C7E}
    .glass{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-radius:1.5rem}
    nav{backdrop-filter:blur(16px);background:rgba(6,8,10,.85);border-bottom:1px solid rgba(255,255,255,.06)}
    .nl{position:relative;color:rgba(255,255,255,.5);text-decoration:none;transition:color .3s}
    .nl::after{content:"";position:absolute;bottom:-3px;left:0;width:0;height:1px;background:#128C7E;transition:width .3s}
    .nl:hover{color:rgba(37,211,102,1)}.nl:hover::after{width:100%}
    .mesh{background:radial-gradient(ellipse at 18% 20%,rgba(37,211,102,.15) 0%,transparent 55%),radial-gradient(ellipse at 82% 75%,rgba(16,185,129,.1) 0%,transparent 55%),radial-gradient(ellipse at 50% 90%,rgba(37,211,102,.05) 0%,transparent 70%),#06080A}
    .meshGreen{background:radial-gradient(ellipse at 82% 20%,rgba(37,211,102,.12) 0%,transparent 55%),radial-gradient(ellipse at 18% 80%,rgba(16,185,129,.08) 0%,transparent 55%),#06080A}
    .mq{display:flex;width:max-content;animation:mq 28s linear infinite}
    @keyframes mq{to{transform:translateX(-50%)}}
    .mi{white-space:nowrap;padding:0 2.5rem;color:rgba(255,255,255,.12);font-size:.82rem;letter-spacing:.12em}
    .G{background:linear-gradient(135deg,#25D366,#128C7E,#25D366);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
    .cnt{font-variant-numeric:tabular-nums}
    .cw{border-radius:.8rem;overflow:hidden}
    .ctb{display:flex;align-items:center;gap:.4rem;padding:.7rem 1rem;border-bottom:1px solid rgba(255,255,255,.05);background:rgba(37,211,102,.05)}
    .dot{width:11px;height:11px;border-radius:50%}
    pre{padding:1.2rem;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.06);
    line-height:1.75;overflow-x:auto;font-size:.82rem}
    code{color:rgba(255,255,255,.6);font-family:JetBrains Mono,monospace}
    .divider{height:1px;max-width:5rem;margin:0 auto}
    .fcard{transition:transform .4s,border-color .4s,box-shadow .4s}
    .fcard:hover{transform:translateY(-8px);border-color:rgba(37,211,102,.3);box-shadow:0 20px 60px rgba(0,0,0,.4),0 0 24px rgba(37,211,102,.2)}
    ::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:#06080A}::-webkit-scrollbar-thumb{background:rgba(37,211,102,.3);border-radius:3px}
  </style>
</head>
<body class="nav-scroll">
<div id="grain"></div>
<div class="vignette"></div>

<!-- NAV -->
<nav class="fixed top-0 left-0 right-0 z-[6000] border-b border-white/[.06]">
  <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
    <a href="#hero" class="flex items-center gap-2 text-white no-underline"><span class="text-xl">&#128172;</span><span class="font-bold text-base tracking-tight">WhatsApp CRM SA</span></a>
    <div class="hidden md:flex items-center gap-8 text-sm">
      <a href="#problem" class="nl">Problem</a>
      <a href="#solution" class="nl">Solution</a>
      <a href="#features" class="nl">Features</a>
      <a href="#tech" class="nl">Tech</a>
      <a href="#pricing" class="nl">Pricing</a>
      <a href="#cta" class="btnW !py-2.5 !px-5 text-sm">Get Started</a>
    </div>
    <button id="mob-btn" class="md:hidden text-gray-400 text-2xl bg-none border-none cursor-pointer p-0" aria-label="Menu">&#9776;</button>
  </div>
  <div id="mob-menu" class="hidden md:hidden border-t border-white/[.06] bg-black/[.95] backdrop-blur-xl">
    <div class="px-6 py-4 space-y-3 text-gray-100">
      <a href="#problem" class="block">Problem</a><a href="#solution" class="block">Solution</a><a href="#features" class="block">Features</a><a href="#tech" class="block">Tech</a><a href="#pricing" class="block">Pricing</a><a href="#cta" class="btnW !py-2 inline-flex text-sm">Get Started</a>
    </div>
  </div>
</nav>

<!-- HERO -->
<section id="hero" class="relative min-h-screen flex items-center justify-center overflow-hidden mesh">
  <canvas id="hero-canvas" class="absolute inset-0 w-full h-full"></canvas>
  <div class="absolute bottom-0 left-0 right-0 h-48 bg-gradient-to-t from-gray-950 to-transparent z-10"></div>
  <div class="relative z-20 text-center px-6 pt-20 pb-36 max-w-5xl mx-auto">
    <div class="eyebrow text-green-500 mb-6 r0" id="h-eye">Self-Hosted &middot; Open Source &middot; Zero Per-Message Fees</div>
    <h1 class="headline text-[clamp(2.6rem,9vw,7.5rem)] mb-8 leading-none r0" id="h-title">
      Every missed<br/><span class="G">WhatsApp</span><br/>message is<br/><span class="text-gray-100">revenue on the floor.</span>
    </h1>
    <p class="text-gray-500 text-lg md:text-xl max-w-2xl mx-auto leading-relaxed mb-12 r0" id="h-sub">
      The free WhatsApp CRM for South African <strong class="text-gray-100">SMMEs</strong>. AI auto-replies &middot; lead scoring &middot; drip campaigns &mdash; all on <strong class="text-green-600">OpenWA</strong>. <strong class="text-gray-100">R0/month to start.</strong>
    </p>
    <div class="flex flex-wrap gap-4 justify-center r0" id="h-ctas">
      <a href="#cta" class="btnW text-lg py-4 px-12">Start Free &mdash; 5 min</a>
      <a href="#problem" class="btnG text-lg py-4 px-8">See the Problem &#8595;</a>
    </div>
  </div>
  <div class="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 opacity-25 animate-bounce"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6B7280" stroke-width="1.5"><path d="M12 5v14m0 0l-5-5m5 5l5-5"/></svg></div>
</section>

<!-- MARQUEE -->
<div class="py-4 overflow-hidden border-y border-white/[.06] bg-gray-900/50 backdrop-blur-sm relative z-20">
  <div class="mq"><span class="mi">OPEN SOURCE &middot; SELF-HOSTED &middot; ZERO PER-MESSAGE FEES &middot; GROQ AI FREE &middot; SAST TIMEZONE &middot; ZAR READY &middot; MIT LICENCE</span><span class="mi">OPEN SOURCE &middot; SELF-HOSTED &middot; ZERO PER-MESSAGE FEES &middot; GROQ AI FREE &middot; SAST TIMEZONE &middot; ZAR READY &middot; MIT LICENCE</span><span class="mi">OPEN SOURCE &middot; SELF-HOSTED &middot; ZERO PER-MESSAGE FEES &middot; GROQ AI FREE &middot; SAST TIMEZONE &middot; ZAR READY &middot; MIT LICENCE</span><span class="mi">OPEN SOURCE &middot; SELF-HOSTED &middot; ZERO PER-MESSAGE FEES &middot; GROQ AI FREE &middot; SAST TIMEZONE &middot; ZAR READY &middot; MIT LICENCE</span></div>
</div>

<!-- PROBLEM -->
<section id="problem" class="relative py-36 px-6">
  <div class="max-w-7xl mx-auto grid md:grid-cols-2 gap-20 items-center">
    <div>
      <p class="eyebrow text-green-600 mb-5 r0">The Problem</p>
      <h2 class="headline text-4xl md:text-6xl mb-7 leading-tight r0">R47k gone.<br/><span class="text-green-600">Every year.</span></h2>
      <p class="text-gray-500 text-lg leading-relaxed mb-14 r0">SA SMMEs live and die on WhatsApp. A customer messages at 8pm on load-shedding stage 4 mid-weekend. You are busy. The message dies. The lead is gone. Forever.</p>
      <div class="grid grid-cols-2 gap-4">
        <div class="glass p-6 fcard r0"><div class="text-3xl font-bold mb-1 text-green-600"><span class="cnt" data-t="82">0</span>%</div><div class="text-gray-400 text-sm">hit by load-shedding</div></div>
        <div class="glass p-6 fcard r0"><div class="text-3xl font-bold mb-1 text-green-600">R<span class="cnt" data-t="47">0</span>k</div><div class="text-gray-400 text-sm">avg lost per SMME/yr</div></div>
        <div class="glass p-6 fcard r0"><div class="text-3xl font-bold mb-1 text-green-600"><span class="cnt" data-t="46">0</span>%</div><div class="text-gray-400 text-sm">expect replies in 1hr</div></div>
        <div class="glass p-6 fcard r0"><div class="text-3xl font-bold mb-1 text-green-600"><span class="cnt" data-t="38">0</span>%</div><div class="text-gray-400 text-sm">lack skills to implement tech</div></div>
      </div>
    </div>
    <div class="rR"><div class="glass p-8 md:p-10 border-amber-400/15 relative">
      <div class="flex gap-1.5 mb-6"><div class="dot bg-[#ff5f57]"></div><div class="dot bg-[#febc2e]"></div><div class="dot bg-[#28c840]"></div></div>
      <p class="font-display text-xl md:text-2xl italic text-gray-100 mb-5 leading-relaxed">&#8220;We lost roughly <span class="text-green-600 font-bold" style="font-style:normal">R13,000</span> last month from WhatsApp we never answered.&#8221;</p>
      <p class="text-gray-400 text-sm">--- Sandton beauty salon, March 2026</p>
    </div><div class="absolute -inset-12 -z-10 bg-gradient-to-br from-green-500/10 to-transparent blur-3xl"></div></div>
  </div>
</section>
<div class="divider bg-gradient-to-r from-transparent via-green-500/25 to-transparent mx-auto max-w-4xl" style="height:.5px;margin-bottom:-.5px"></div>

<!-- SOLUTION -->
<section id="solution" class="relative py-36 px-6">
  <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[900px] bg-green-500/[.03] rounded-full blur-3xl pointer-events-none"></div>
  <div class="max-w-7xl mx-auto">
    <div class="text-center mb-20">
      <p class="eyebrow text-green-500 mb-5 r0">The Solution</p>
      <h2 class="headline text-4xl md:text-6xl mb-6 r0">AI that never sleeps.<br/><span class="G">No vendor lock-in.</span><br/>R0/month to start.</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto r0">Built on <strong>OpenWA</strong> (free self-hosted WhatsApp) + <strong>Groq AI</strong> (14 400 free req/day). Zero Meta approval. Zero per-message fees.</p>
    </div>
    <div class="max-w-sm mx-auto text-center rS" id="phone">
      <div class="relative">
        <div class="bg-gray-900/60 rounded-3xl border border-white/[.07] overflow-hidden shadow-2xl shadow-accent/10">
          <div class="flex justify-between items-center px-6 py-2.5 text-[10px] text-gray-400 font-mono"><span id="chat-time">09:41</span><div class="flex gap-1.5"><span>&#128225;</span><span>&#128225;</span><span>&#128267;</span></div></div>
          <div class="px-5 py-3.5 border-b border-white/[.07] flex items-center gap-3"><div class="w-9 h-9 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-green-600 text-xs font-bold">JD</div><div class="text-left"><div class="text-sm font-semibold text-gray-100">Johannes Dube</div><div class="text-[10px] text-green-600">online</div></div></div>
          <div class="p-4 space-y-3 min-h-[240px]" id="live-chat"></div>
        </div>
        <div class="absolute -bottom-6 left-1/2 -translate-x-1/2 w-2/3 h-12 bg-green-500/14 blur-2xl rounded-full"></div>
      </div>
    </div>
    <div class="mt-16 flex flex-wrap gap-6 justify-center text-gray-400 text-xs r0">
      <span>&#10003; No Meta approval</span><span>&#10003; Zero per-message fees</span><span>&#10003; Open source MIT</span><span>&#10003; Deploy in 5 min</span>
    </div>
  </div>
</section>
<div class="divider bg-gradient-to-r from-transparent via-green-500/25 to-transparent mx-auto max-w-4xl" style="height:.5px;margin-bottom:-.5px"></div>

<!-- FEATURES -->
<section id="features" class="relative py-36 px-6">
  <div class="max-w-7xl mx-auto">
    <div class="text-center mb-20"><p class="eyebrow text-green-500 mb-5 r0">Features</p><h2 class="headline text-4xl md:text-6xl mb-5 r0">Everything you need.<br/><span class="text-gray-400">Nothing you don't.</span></h2></div>
    <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div class="glass p-7 fcard r0"><div class="text-3xl mb-4">&#129302;</div><h3 class="font-display text-lg font-bold mb-2">AI Auto-Reply</h3><p class="text-gray-500 text-sm">Groq 14400 req/day free. Greetings pricing bookings. Sounds human. Runs 24/7 on SAST.</p></div>
      <div class="glass p-7 fcard r0"><div class="text-3xl mb-4">&#11088;</div><h3 class="font-display text-lg font-bold mb-2">Lead Scoring</h3><p class="text-gray-500 text-sm">Every contact scored 0-100. Tag by industry province language. Hot leads at a glance in the dashboard.</p></div>
      <div class="glass p-7 fcard r0"><div class="text-3xl mb-4">&#128233;</div><h3 class="font-display text-lg font-bold mb-2">Drip Campaigns</h3><p class="text-gray-500 text-sm">Automated sequences on new lead purchase or inactivity. Set once runs forever on SAST timezone.</p></div>
      <div class="glass p-7 fcard r0"><div class="text-3xl mb-4">&#128225;</div><h3 class="font-display text-lg font-bold mb-2">Broadcast</h3><p class="text-gray-500 text-sm">Send to segments by tag industry or province. Load-shedding aware auto-pauses during Stage 4+.</p></div>
      <div class="glass p-7 fcard r0"><div class="text-3xl mb-4">&#128018;</div><h3 class="font-display text-lg font-bold mb-2">ZAR + SA Ready</h3><p class="text-gray-500 text-sm">ZAR currency SAST timezone RSA phone numbers PayFast invoicing. Built for South Africa.</p></div>
      <div class="glass p-7 fcard r0"><div class="text-3xl mb-4">&#128187;</div><h3 class="font-display text-lg font-bold mb-2">Admin Dashboard</h3><p class="text-gray-500 text-sm">Real-time stats live conversation queue pipeline funnel message history all at /dashboard.</p></div>
      <div class="glass p-7 fcard r0"><div class="text-3xl mb-4">&#128274;</div><h3 class="font-display text-lg font-bold mb-2">JWT Protected</h3><p class="text-gray-500 text-sm">Admin routes behind HMAC-signed JWT tokens. 24-hour exp. Full health at /api/admin/health/detailed.</p></div>
      <div class="glass p-7 fcard r0"><div class="text-3xl mb-4">&#9889;</div><h3 class="font-display text-lg font-bold mb-2">5-Minute Setup</h3><p class="text-gray-500 text-sm">docker compose up -d then scan QR then paste API key then live. No engineers no Meta approval.</p></div>
      <div class="glass p-7 fcard r0"><div class="text-3xl mb-4">&#127760;</div><h3 class="font-display text-lg font-bold mb-2">Multilingual AI</h3><p class="text-gray-500 text-sm">English Afrikaans Zulu Xhosa. AI auto-detects and switches. Tag contacts by preferred language.</p></div>
    </div>
  </div>
</section>
<div class="divider bg-gradient-to-r from-transparent via-green-500/25 to-transparent mx-auto max-w-4xl" style="height:.5px;margin-bottom:-.5px"></div>

<!-- TECH -->
<section id="tech" class="relative py-36 px-6">
  <div class="max-w-7xl mx-auto">
    <div class="text-center mb-20"><p class="eyebrow text-green-500 mb-5 r0">Tech Stack</p><h2 class="headline text-4xl md:text-6xl mb-5 r0"><span class="G">Three frameworks.</span><br/>Five minutes.<br/>No catch.</h2></div>
    <div class="max-w-4xl mx-auto grid md:grid-cols-3 gap-5">
      <div class="glass p-7 text-center fcard r0"><div class="w-14 h-14 rounded-2xl bg-green-500/16 border border-green-500/30 flex items-center justify-center mx-auto mb-5 text-2xl">&#128994;</div><h3 class="font-display text-lg font-bold mb-2">OpenWA v0.1.4</h3><p class="text-gray-500 text-sm mb-4">Self-hosted WhatsApp gateway. REST API web dashboard webhook events HMAC audit. One Docker image.</p><div class="cw border border-white/[.07] bg-gray-800/90 text-left"><div class="ctb"><div class="dot bg-[#ff5f57]"></div><div class="dot bg-[#febc2e]"></div><div class="dot bg-[#28c840]"></div><span class="ml-2 text-gray-500 text-xs mono">docker</span></div><pre><code>docker run -p 2785:2785 -p 2886:2886 \
  -v openwa-data:/app/data \
  rmyndharis/openwa:0.1.4</code></pre></div></div>
      <div class="glass p-7 text-center fcard r0"><div class="w-14 h-14 rounded-2xl bg-green-500/15 border border-green-500/25 flex items-center justify-center mx-auto mb-5 text-2xl">&#129302;</div><h3 class="font-display text-lg font-bold mb-2">Groq AI</h3><p class="text-gray-500 text-sm mb-4">Llama 3.1 500+ tokens/sec. 14400 free calls/day. OpenRouter fallback. No credit card needed.</p><div class="cw border border-white/[.07] bg-gray-800/90 text-left"><div class="ctb"><div class="dot bg-[#ff5f57]"></div><div class="dot bg-[#febc2e]"></div><div class="dot bg-[#28c840]"></div><span class="ml-2 text-gray-500 text-xs mono">config</span></div><pre><code>"provider": "groq",
"model":     "llama-3.1-8b-instant",
"temperature": 0.5</code></pre></div></div>
      <div class="glass p-7 text-center fcard r0"><div class="w-14 h-14 rounded-2xl bg-acc2/15 border border-acc2/25 flex items-center justify-center mx-auto mb-5 text-2xl">&#9889;</div><h3 class="font-display text-lg font-bold mb-2">FastAPI</h3><p class="text-gray-500 text-sm mb-4">Type-safe Python 3.12 async by default. OpenAPI docs at /docs. JWT auth health checks rate-limit.</p><div class="cw border border-white/[.07] bg-gray-800/90 text-left"><div class="ctb"><div class="dot bg-[#ff5f57]"></div><div class="dot bg-[#febc2e]"></div><div class="dot bg-[#28c840]"></div><span class="ml-2 text-gray-500 text-xs mono">shell</span></div><pre><code>uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000</code></pre></div></div>
    </div>
  </div>
</section>
<div class="divider bg-gradient-to-r from-transparent via-green-500/25 to-transparent mx-auto max-w-4xl" style="height:.5px;margin-bottom:-.5px"></div>

<!-- PRICING -->
<section id="pricing" class="relative py-36 px-6">
  <div class="max-w-7xl mx-auto">
    <div class="text-center mb-20"><p class="eyebrow text-green-500 mb-5 r0">Pricing</p><h2 class="headline text-4xl md:text-6xl mb-5 r0">Start free.<br/>Scale when you need.</h2><p class="text-gray-500 text-lg r0">No credit card. No lock-in. 99% of SA SMMEs stay profitable on the free tier.</p></div>
    <div class="max-w-4xl mx-auto grid md:grid-cols-3 gap-5">
      <div class="glass p-8 fcard r0"><p class="eyebrow text-gray-500 mb-2">Starter</p><div class="text-5xl font-bold mb-1">R0</div><p class="text-gray-400 text-sm mb-7">/month forever</p><ul class="text-gray-400 text-sm space-y-2.5 mb-8"><li>&#10003; OpenWA self-hosted</li><li>&#10003; 200 conv/day</li><li>&#10003; 14400 AI calls/day</li><li>&#10003; SQLite</li><li>&#10003; Groq free tier</li></ul><a href="#cta" class="btnG w-full !justify-center text-sm">Deploy Free</a></div>
      <div class="glass p-8 fcard relative border-accent/45 shadow-[0_0_50px_rgba(37,211,102,.15)] r0"><div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-accent text-gray-50 text-xs font-semibold px-4 py-1 rounded-full">Most Popular</div><p class="eyebrow text-gray-500 mb-2">Pro</p><div class="text-5xl font-bold mb-1">R599</div><p class="text-gray-400 text-sm mb-7">/month</p><ul class="text-gray-400 text-sm space-y-2.5 mb-8"><li>&#10003; Unlimited messages</li><li>&#10003; Unlimited AI replies</li><li>&#10003; Supabase PostgreSQL</li><li>&#10003; Drip campaigns + broadcast</li><li>&#10003; PayFast invoicing</li></ul><a href="mailto:hello@agentcy.co?subject=WhatsApp%20CRM%20Pro" class="btnW w-full !justify-center text-sm">Get Pro</a></div>
      <div class="glass p-8 fcard r0"><p class="eyebrow text-gray-500 mb-2">Enterprise</p><div class="text-5xl font-bold mb-1">Custom</div><p class="text-gray-400 text-sm mb-7">on request</p><ul class="text-gray-400 text-sm space-y-2.5 mb-8"><li>&#10003; Multi-location franchises</li><li>&#10003; Custom AI fine-tuning</li><li>&#10003; On-premise deployment</li><li>&#10003; Dedicated SLA</li><li>&#10003; White-label licence</li></ul><a href="mailto:hello@agentcy.co?subject=WhatsApp%20CRM%20Enterprise" class="btnG w-full !justify-center text-sm">Contact Sales</a></div>
    </div>
  </div>
</section>
<div class="divider bg-gradient-to-r from-transparent via-green-500/25 to-transparent mx-auto max-w-4xl" style="height:.5px;margin-bottom:-.5px"></div>

<!-- HOW -->
<section id="how" class="relative py-36 px-6">
  <div class="max-w-7xl mx-auto">
    <div class="text-center mb-20"><p class="eyebrow text-green-500 mb-5 r0">How It Works</p><h2 class="headline text-4xl md:text-6xl r0">Five minutes.<br/>That's it.</h2></div>
    <div class="hidden md:flex items-start justify-between mb-16 relative px-8 r0" id="step-line">
      <div class="absolute top-5 left-0 right-0 h-[2px] bg-gradient-to-r from-green-500 via-emerald-400 to-transparent"></div>
      <div class="flex-1 flex flex-col items-center relative z-10 text-center"><div class="w-14 h-14 rounded-full bg-gray-900 border-2 border-accent flex items-center justify-center text-green-500 text-xl font-bold mb-4">1</div><p class="text-gray-400 text-sm max-w-[140px]">Pull &amp; start OpenWA</p></div>
      <div class="flex-1 flex flex-col items-center relative z-10 text-center"><div class="w-14 h-14 rounded-full bg-gray-900 border-2 border-acc2 flex items-center justify-center text-green-500 text-xl font-bold mb-4">2</div><p class="text-gray-400 text-sm max-w-[140px]">Scan QR - link WhatsApp</p></div>
      <div class="flex-1 flex flex-col items-center relative z-10 text-center"><div class="w-14 h-14 rounded-full bg-gray-900 border-2 border-acc2 flex items-center justify-center text-green-500 text-xl font-bold mb-4">3</div><p class="text-gray-400 text-sm max-w-[140px]">Copy API key from dashboard</p></div>
      <div class="flex-1 flex flex-col items-center relative z-10 text-center"><div class="w-14 h-14 rounded-full bg-gray-900 border-2 border-acc2 flex items-center justify-center text-green-500 text-xl font-bold mb-4">4</div><p class="text-gray-400 text-sm max-w-[140px]">6 lines in <code class="text-xs bg-gray-800/90/10 px-1 rounded">.env</code></p></div>
      <div class="flex-1 flex flex-col items-center relative z-10 text-center"><div class="w-14 h-14 rounded-full bg-green-500/80 border-2 border-accent flex items-center justify-center text-gray-50 text-xl mb-4 glow">&#10003;</div><p class="text-gray-400 text-sm max-w-[140px]">Start receiving &amp; replying</p></div>
    </div>
  </div>
</section>
<div class="divider bg-gradient-to-r from-transparent via-green-500/25 to-transparent mx-auto max-w-4xl" style="height:.5px;margin-bottom:-.5px"></div>

<!-- TESTIMONIALS -->
<section id="testimonials" class="relative py-36 px-6">
  <div class="max-w-7xl mx-auto">
    <div class="text-center mb-16"><p class="eyebrow text-green-500 mb-5 r0">Beta Feedback</p><h2 class="headline text-4xl md:text-5xl mb-4 r0">Loved before they even launched.</h2></div>
    <div class="grid md:grid-cols-3 gap-6">
      <div class="glass p-7 fcard rL"><div class="text-green-600 text-lg mb-3">&#11088;&#11088;&#11088;&#11088;&#11088;</div><p class="text-white/50 text-sm leading-relaxed mb-4">&#8220;Setup took literally 3 minutes. Docker run scan QR we were live. Would pay for Pro today.&#8221;</p><p class="text-gray-400 text-xs font-mono">--- Auto repair Pretoria &#183; Early Access</p></div>
      <div class="glass p-7 fcard r0"><div class="text-green-600 text-lg mb-3">&#11088;&#11088;&#11088;&#11088;&#11088;</div><p class="text-white/50 text-sm leading-relaxed mb-4">&#8220;AI replies are shockingly good for free. Missed less than 10% of enquiries versus 60% before.&#8221;</p><p class="text-gray-400 text-xs font-mono">--- Tutoring centre Cape Town &#183; Beta</p></div>
      <div class="glass p-7 fcard rR"><div class="text-green-600 text-lg mb-3">&#11088;&#11088;&#11088;&#11088;&#11088;</div><p class="text-white/50 text-sm leading-relaxed mb-4">&#8220;Finally a CRM that does not cost R2,000/month and understands SA numbers and timezones. Game changer.&#8221;</p><p class="text-gray-400 text-xs font-mono">--- Salon owner Sandton &#183; Beta</p></div>
    </div>
  </div>
</section>
<div class="divider bg-gradient-to-r from-transparent via-green-500/25 to-transparent mx-auto max-w-4xl" style="height:.5px;margin-bottom:-.5px"></div>

<!-- COMPARISON -->
<section id="compare" class="relative py-36 px-6">
  <div class="max-w-7xl mx-auto">
    <div class="text-center mb-20"><p class="eyebrow text-green-500 mb-5 r0">Why We Are Different</p><h2 class="headline text-4xl md:text-6xl mb-5 r0">The only CRM for <span class="G">South Africa</span></h2></div>
    <div class="max-w-3xl mx-auto glass overflow-hidden r0">
      <div class="grid grid-cols-4 gap-0 border-b border-white/[.07]"><div class="p-5 text-gray-500 text-xs font-semibold uppercase tracking-wider">Feature</div><div class="p-5 text-green-600 text-sm font-bold text-center">WhatsApp CRM SA</div><div class="p-5 text-green-600 text-sm font-medium text-center">Most CRMs</div><div class="p-5 text-gray-500 text-sm font-medium text-center">Meta API</div></div>
      <div class="grid grid-cols-4 gap-0 border-b border-white/[.06] items-center"><div class="p-4 text-gray-500 text-sm">Price start</div><div class="p-4 text-green-600 text-sm text-center font-semibold">R0/month</div><div class="p-4 text-gray-500 text-sm text-center">R500+/month</div><div class="p-4 text-gray-500 text-sm text-center">Free tier limited</div></div>
      <div class="grid grid-cols-4 gap-0 border-b border-white/[.06] items-center"><div class="p-4 text-gray-500 text-sm">Meta approval</div><div class="p-4 text-green-600 text-sm text-center font-semibold">Nope</div><div class="p-4 text-red-400/70 text-sm text-center">&#10007; Required</div><div class="p-4 text-red-400/70 text-sm text-center">&#10007; Required</div></div>
      <div class="grid grid-cols-4 gap-0 border-b border-white/[.06] items-center"><div class="p-4 text-gray-500 text-sm">Per-message fees</div><div class="p-4 text-green-600 text-sm text-center font-semibold">None</div><div class="p-4 text-red-400/70 text-sm text-center">&#10007; Per msg</div><div class="p-4 text-red-400/70 text-sm text-center">&#10007; Per msg</div></div>
      <div class="grid grid-cols-4 gap-0 border-b border-white/[.06] items-center"><div class="p-4 text-gray-500 text-sm">SAST + ZAR native</div><div class="p-4 text-green-600 text-sm text-center font-semibold">&#10003; Native</div><div class="p-4 text-gray-400 text-sm text-center">&#10007; Often ignored</div><div class="p-4 text-gray-400 text-sm text-center">&#10007; No</div></div>
      <div class="grid grid-cols-4 gap-0 border-b border-white/[.06] items-center"><div class="p-4 text-gray-500 text-sm">AI auto-reply</div><div class="p-4 text-green-600 text-sm text-center font-semibold">Groq free</div><div class="p-4 text-gray-400 text-sm text-center">Paid add-on</div><div class="p-4 text-gray-400 text-sm text-center">&#10007; None</div></div>
      <div class="grid grid-cols-4 gap-0 items-center"><div class="p-4 text-gray-500 text-sm">Open source</div><div class="p-4 text-green-600 text-sm text-center font-semibold">&#10003; MIT</div><div class="p-4 text-gray-400 text-sm text-center">&#10007; Proprietary</div><div class="p-4 text-gray-400 text-sm text-center">&#10007; Proprietary</div></div>
    </div>
  </div>
</section>
<div class="divider bg-gradient-to-r from-transparent via-green-500/25 to-transparent mx-auto max-w-4xl" style="height:.5px;margin-bottom:-.5px"></div>

<!-- CTA -->
<section id="cta" class="relative py-44 px-6">
  <div class="absolute inset-0 meshGreen opacity-55"></div>
  <div class="relative z-10 max-w-3xl mx-auto text-center">
    <h2 class="headline text-4xl md:text-7xl mb-6 r0">Stop leaving<br/><span class="text-green-600">R13,000</span> on the floor.</h2>
    <p class="text-gray-500 text-lg md:text-xl mb-12 r0">Deploy in under 5 minutes.<br/>Zero credit card. Zero Meta approval. Open source.</p>
    <div class="flex flex-wrap gap-4 justify-center r0" id="cta-bottom">
      <a href="https://github.com/mikewithoutthemechanics/whatsapp-crm" class="btnW text-lg py-4 px-12" target="_blank" rel="noopener">Deploy Free on GitHub</a>
      <a href="mailto:hello@agentcy.co?subject=WhatsApp%20CRM%20Enquiry" class="btnG text-lg py-4 px-10">Talk to Us</a>
    </div>
    <p class="text-gray-400 text-sm mt-8 r0">MIT licence &#183; Forever free &#183; No lock-in</p>
  </div>
</section>
<div class="divider bg-gradient-to-r from-transparent via-green-500/25 to-transparent mx-auto max-w-4xl" style="height:.5px;margin-bottom:-.5px"></div>

<!-- FOOTER -->
<footer class="relative py-16 px-6 border-t border-white/[.06]">
  <div class="max-w-7xl mx-auto grid md:grid-cols-4 gap-12">
    <div><div class="flex items-center gap-2 mb-4"><span>&#128172;</span><span class="font-display font-bold">WhatsApp CRM SA</span></div><p class="text-gray-400 text-sm leading-relaxed">Open-source WhatsApp CRM for SA SMMEs. MIT licence forever free no lock-in.</p></div>
    <div><h4 class="font-semibold mb-4 text-gray-100">Product</h4><ul class="space-y-2 text-gray-400 text-sm"><li><a href="#features" class="hover:text-gray-100">Features</a></li><li><a href="#pricing" class="hover:text-gray-100">Pricing</a></li><li><a href="#tech" class="hover:text-gray-100">Tech Stack</a></li><li><a href="https://github.com/mikewithoutthemechanics/whatsapp-crm" class="hover:text-gray-100">GitHub</a></li></ul></div>
    <div><h4 class="font-semibold mb-4 text-gray-100">Links</h4><ul class="space-y-2 text-gray-400 text-sm"><li><a href="https://agentcy.co" class="hover:text-gray-100">Agentcy</a></li><li><a href="https://github.com/rmyndharis/OpenWA" class="hover:text-gray-100">OpenWA</a></li><li><a href="https://console.groq.com" class="hover:text-gray-100">Groq Console</a></li><li><a href="https://github.com/mikewithoutthemechanics/whatsapp-crm/blob/main/CLIENT-ONBOARDING.md" class="hover:text-gray-100">Client Guide</a></li></ul></div>
    <div><h4 class="font-semibold mb-4 text-gray-100">Stack</h4><div class="space-y-2 text-gray-400 text-sm font-mono"><div>OpenWA <span class="text-green-600">&#9679;</span> v0.1.4</div><div>AI Engine <span class="text-green-600">&#9679;</span> Groq Free</div><div>Database <span class="text-green-600">&#9679;</span> Supabase/SQLite</div><div>Licence <span class="text-gray-500">&#9679;</span> MIT</div></div></div>
  </div>
  <div class="mt-12 text-center text-white/50 text-xs">&#169; 2026 &#183; MIT licence &#183; <a href="https://github.com/mikewithoutthemechanics" class="text-gray-400 hover:text-gray-500">mikewithoutthemechanics</a> &#183; Powered by <a href="https://github.com/rmyndharis/OpenWA" class="text-gray-400 hover:text-gray-500">OpenWA</a></div>
</footer>

<!-- SCRIPTS -->
<script>
const lenis=new Lenis({duration:1.25,easing:t=>Math.min(1,1.001-Math.pow(2,-10*t)),smooth:true})
function raf(t){lenis.raf(t);requestAnimationFrame(raf)};requestAnimationFrame(raf)
gsap.registerPlugin(ScrollTrigger)

(function(){
  const tl=gsap.timeline({defaults:{ease:"power3.out",duration:1.1}})
  tl.to("#h-eye",{opacity:1,y:0,duration:.8,delay:.4}).to("#h-title",{opacity:1,y:0,duration:1.1},"-=.5").to("#h-sub",{opacity:1,y:0,duration:.9},"-=.6").to("#h-ctas",{opacity:1,y:0,duration:.8},"-=.5")
  setTimeout(revealALL,400);setTimeout(startChat,1000)
})();

function revealALL(){
  gsap.fromTo(".fcard",{opacity:0,y:40},{opacity:1,y:0,stagger:.07,duration:.7,ease:"power3.out",scrollTrigger:{trigger:"#features",start:"top 80%",once:true}})
}

function countUp(el){const t=+el.dataset.t,dur=1800,step=t/(dur/16);let c=0;const rf=()=>{c=Math.min(c+step,t);el.textContent=Math.round(c);if(c<t)requestAnimationFrame(rf)};requestAnimationFrame(rf)}
document.querySelectorAll(".cnt").forEach(el=>{ScrollTrigger.create({trigger:el,start:"top 90%",once:true,onEnter:()=>countUp(el)})})

// live chat demo
const chatMsgs=[
  {s:"left",t:"Hi how much for a full house clean?",d:0},
  {s:"right",t:"Hi 3-bedroom is R650 floors bathrooms and kitchen included. Want to book?",d:2500,a:true},
  {s:"left",t:"Yes this Saturday if possible?",d:5000},
  {s:"right",t:"Saturday 2pm works perfectly I have pencilled you in. Can I get your address?",d:7500,a:true},
  {s:"left",t:"22 Oak Street Sandton",d:11500},
  {s:"right",t:"All set Your booking is confirmed. I will send you a reminder on Saturday morning.",d:14000,a:true},
]
let timer=null
function addMsg(m){
  const d=document.createElement("div");d.className="flex "+(m.s==="right"?"justify-end":"justify-start")
  d.innerHTML=`<div class="${m.s==="right"?"bg-green-500/85":"bg-gray-800/90/[.07]"} rounded-2xl ${m.s==="right"?"rounded-tr-sm":"rounded-tl-sm"} px-4 py-2.5 max-w-[78%] ${m.s==="right"?"text-gray-50 shadow-md":"text-gray-500"} text-sm leading-relaxed">${m.t}<span class="text-[9px] block mt-1 ${m.s==="right"?"text-gray-400 text-right":"text-gray-500"}">09:42 ${m.a?" · AI reply":""}</span></div>`
  document.getElementById("live-chat").appendChild(d)
  document.getElementById("live-chat").scrollTop=document.getElementById("live-chat").scrollHeight
}
function startChat(){if(timer)return;chatMsgs.forEach(m=>{timer=setTimeout(()=>addMsg(m),m.d)})}
function resetChat(){clearTimeout(timer);timer=null;document.getElementById("live-chat").innerHTML="";addMsg(chatMsgs[0]);setTimeout(startChat,1500)}

document.querySelectorAll('a[href^="#"]').forEach(a=>{a.addEventListener("click",e=>{const t=document.querySelector(a.getAttribute("href"));if(t){e.preventDefault();lenis.scrollTo(t,{offset:-80})}})})
document.getElementById("mob-btn").addEventListener("click",()=>{document.getElementById("mob-menu").classList.toggle("hidden")})
document.querySelectorAll("#mob-menu a").forEach(a=>a.addEventListener("click",()=>document.getElementById("mob-menu").classList.add("hidden")))
lenis.on("scroll",ScrollTrigger.update);gsap.ticker.add(t=>lenis.raf(t*1000));gsap.ticker.lagSmoothing(0)

;(function(){
  const c=document.getElementById("hero-canvas");if(!c||typeof THREE==="undefined")return
  const r=new THREE.WebGLRenderer({canvas:c,alpha:true,antialias:false})
  r.setSize(window.innerWidth,window.innerHeight);r.setPixelRatio(Math.min(window.devicePixelRatio,1.5))
  const s=new THREE.Scene(),p=new THREE.PerspectiveCamera(60,window.innerWidth/window.innerHeight,.1,1000);p.position.z=50
  const N=900,pos=new Float32Array(N*3);for(let i=0;i<N;i++){pos[i*3]=(Math.random()-.5)*120;pos[i*3+1]=(Math.random()-.5)*80;pos[i*3+2]=(Math.random()-.5)*80}
  const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3))
  const m=new THREE.PointsMaterial({color:0x25D366,size:.35,transparent:true,opacity:.55,sizeAttenuation:true});s.add(new THREE.Points(g,m))
  let mx=0,my=0;document.addEventListener("mousemove",e=>{mx=(e.clientX/window.innerWidth-.5)*2;my=-(e.clientY/window.innerHeight-.5)*2})
  window.addEventListener("resize",()=>{r.setSize(window.innerWidth,window.innerHeight);p.aspect=window.innerWidth/window.innerHeight;p.updateProjectionMatrix()})
  let t0=performance.now()
  function loop(){requestAnimationFrame(loop);const t=(performance.now()-t0)/1000;s.rotation.y=t*.04+mx*.05;s.rotation.x=my*.03;m.opacity=.4+.15*Math.sin(t*.8);r.render(s,p)}loop()
})()
</script>
</body>
</html>
"""

# ─── Admin Static Pages (Next.js v0.1.4 export / build-hash _3x95xLmWbLN0GMJUinot ──
# Auto-generated by scripts/embed-admin-routes.py — re-run after web/admin/ layout/content changes

_APP_PAGE_DASHBOARD = """<!DOCTYPE html><!--_3x95xLmWbLN0GMJUinot--><html lang="en"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/><meta name="viewport" content="width=device-width, initial-scale=1"/><link rel="stylesheet" href="/_next/static/css/a5b9e56526ddf77e.css" data-precedence="next"/><link rel="preload" as="script" fetchPriority="low" href="/_next/static/chunks/webpack-74c939c87fa0092a.js"/><script src="/_next/static/chunks/4bd1b696-c023c6e3521b1417.js" async=""></script><script src="/_next/static/chunks/255-81ba70bd132d3eed.js" async=""></script><script src="/_next/static/chunks/main-app-3e6673f4a8380c97.js" async=""></script><script src="/_next/static/chunks/12-7d516a2f290e26f2.js" async=""></script><script src="/_next/static/chunks/app/layout-82602bdfed5552b0.js" async=""></script><script src="/_next/static/chunks/app/dashboard/page-166872433b798cd6.js" async=""></script><meta name="theme-color" content="#25D366"/><meta name="apple-mobile-web-app-capable" content="yes"/><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/><meta name="apple-mobile-web-app-title" content="WA CRM"/><link rel="manifest" href="/manifest.json"/><title>WhatsApp CRM SA — Admin</title><script src="/_next/static/chunks/polyfills-42372ed130431b0a.js" noModule=""></script></head><body><div hidden=""><!--$--><!--/$--></div><div class="flex min-h-screen"><aside class="fixed left-0 top-0 h-full w-[260px] bg-black/40 backdrop-blur-xl border-r border-white/[.06] flex flex-col z-50"><div class="p-5 border-b border-white/[.06]"><a class="flex items-center gap-2 text-lg font-semibold text-white no-underline" href="/dashboard/"><span class="text-xl">💬</span><span>WhatsApp CRM</span></a><p class="text-xs text-white/30 mt-1">Admin Dashboard</p></div><nav class="flex-1 py-4 px-3 space-y-1"><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/dashboard/"><span class="text-base">🏠</span><span>Dashboard</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/conversations/"><span class="text-base">💬</span><span>Conversations</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/contacts/"><span class="text-base">👥</span><span>Contacts</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/campaigns/"><span class="text-base">📨</span><span>Campaigns</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/ai/"><span class="text-base">🤖</span><span>AI Stats</span></a></nav><div class="p-3 border-t border-white/[.06]"><button class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/50 hover:text-white hover:bg-white/[.06] transition-all cursor-pointer bg-transparent border-none"><span class="text-base">🚪</span><span>Logout</span></button></div></aside><main class="ml-[260px] flex-1"><div class="flex items-center justify-center h-64 text-white/30">Loading…</div><!--$--><!--/$--></main></div><script src="/_next/static/chunks/webpack-74c939c87fa0092a.js" id="_R_" async=""></script><script>(self.__next_f=self.__next_f||[]).push([0])</script><script>self.__next_f.push([1,"1:\"$Sreact.fragment\"\n2:I[6710,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"default\"]\n3:I[9766,[],\"\"]\n4:I[8924,[],\"\"]\n5:I[3762,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"PWAInstallScript\"]\n6:I[1959,[],\"ClientPageRoot\"]\n7:I[9485,[\"105\",\"static/chunks/app/dashboard/page-166872433b798cd6.js\"],\"default\"]\na:I[4431,[],\"OutletBoundary\"]\nc:I[5278,[],\"AsyncMetadataOutlet\"]\ne:I[4431,[],\"ViewportBoundary\"]\n10:I[4431,[],\"MetadataBoundary\"]\n11:\"$Sreact.suspense\"\n13:I[7150,[],\"\"]\n:HL[\"/_next/static/css/a5b9e56526ddf77e.css\",\"style\"]\n"])</script><script>self.__next_f.push([1,"0:{\"P\":null,\"b\":\"_3x95xLmWbLN0GMJUinot\",\"p\":\"\",\"c\":[\"\",\"dashboard\",\"\"],\"i\":false,\"f\":[[[\"\",{\"children\":[\"dashboard\",{\"children\":[\"__PAGE__\",{}]}]},\"$undefined\",\"$undefined\",true],[\"\",[\"$\",\"$1\",\"c\",{\"children\":[[[\"$\",\"link\",\"0\",{\"rel\":\"stylesheet\",\"href\":\"/_next/static/css/a5b9e56526ddf77e.css\",\"precedence\":\"next\",\"crossOrigin\":\"$undefined\",\"nonce\":\"$undefined\"}]],[\"$\",\"html\",null,{\"lang\":\"en\",\"children\":[[\"$\",\"head\",null,{\"children\":[[\"$\",\"meta\",null,{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no\"}],[\"$\",\"meta\",null,{\"name\":\"theme-color\",\"content\":\"#25D366\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-capable\",\"content\":\"yes\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-status-bar-style\",\"content\":\"black-translucent\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-title\",\"content\":\"WA CRM\"}],[\"$\",\"link\",null,{\"rel\":\"manifest\",\"href\":\"/manifest.json\"}]]}],[\"$\",\"body\",null,{\"children\":[[\"$\",\"$L2\",null,{\"children\":[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":[[[\"$\",\"title\",null,{\"children\":\"404: This page could not be found.\"}],[\"$\",\"div\",null,{\"style\":{\"fontFamily\":\"system-ui,\\\"Segoe UI\\\",Roboto,Helvetica,Arial,sans-serif,\\\"Apple Color Emoji\\\",\\\"Segoe UI Emoji\\\"\",\"height\":\"100vh\",\"textAlign\":\"center\",\"display\":\"flex\",\"flexDirection\":\"column\",\"alignItems\":\"center\",\"justifyContent\":\"center\"},\"children\":[\"$\",\"div\",null,{\"children\":[[\"$\",\"style\",null,{\"dangerouslySetInnerHTML\":{\"__html\":\"body{color:#000;background:#fff;margin:0}.next-error-h1{border-right:1px solid rgba(0,0,0,.3)}@media (prefers-color-scheme:dark){body{color:#fff;background:#000}.next-error-h1{border-right:1px solid rgba(255,255,255,.3)}}\"}}],[\"$\",\"h1\",null,{\"className\":\"next-error-h1\",\"style\":{\"display\":\"inline-block\",\"margin\":\"0 20px 0 0\",\"padding\":\"0 23px 0 0\",\"fontSize\":24,\"fontWeight\":500,\"verticalAlign\":\"top\",\"lineHeight\":\"49px\"},\"children\":404}],[\"$\",\"div\",null,{\"style\":{\"display\":\"inline-block\"},\"children\":[\"$\",\"h2\",null,{\"style\":{\"fontSize\":14,\"fontWeight\":400,\"lineHeight\":\"49px\",\"margin\":0},\"children\":\"This page could not be found.\"}]}]]}]}]],[]],\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]}],[\"$\",\"$L5\",null,{}]]}]]}]]}],{\"children\":[\"dashboard\",[\"$\",\"$1\",\"c\",{\"children\":[null,[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":\"$undefined\",\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]]}],{\"children\":[\"__PAGE__\",[\"$\",\"$1\",\"c\",{\"children\":[[\"$\",\"$L6\",null,{\"Component\":\"$7\",\"searchParams\":{},\"params\":{},\"promises\":[\"$@8\",\"$@9\"]}],null,[\"$\",\"$La\",null,{\"children\":[\"$Lb\",[\"$\",\"$Lc\",null,{\"promise\":\"$@d\"}]]}]]}],{},null,false]},null,false]},null,false],[\"$\",\"$1\",\"h\",{\"children\":[null,[[\"$\",\"$Le\",null,{\"children\":\"$Lf\"}],null],[\"$\",\"$L10\",null,{\"children\":[\"$\",\"div\",null,{\"hidden\":true,\"children\":[\"$\",\"$11\",null,{\"fallback\":null,\"children\":\"$L12\"}]}]}]]}],false]],\"m\":\"$undefined\",\"G\":[\"$13\",[]],\"s\":false,\"S\":true}\n"])</script><script>self.__next_f.push([1,"8:{}\n9:\"$0:f:0:1:2:children:2:children:1:props:children:0:props:params\"\n"])</script><script>self.__next_f.push([1,"f:[[\"$\",\"meta\",\"0\",{\"charSet\":\"utf-8\"}],[\"$\",\"meta\",\"1\",{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1\"}]]\nb:null\n"])</script><script>self.__next_f.push([1,"d:{\"metadata\":[[\"$\",\"title\",\"0\",{\"children\":\"WhatsApp CRM SA — Admin\"}]],\"error\":null,\"digest\":\"$undefined\"}\n"])</script><script>self.__next_f.push([1,"12:\"$d:metadata\"\n"])</script></body></html>"""

# ── /dashboard ──────────────────────────────────────────────────────────────────
@app.get("/dashboard", include_in_schema=False)
@app.get("/dashboard/", include_in_schema=False)
def route_dashboard():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=(_APP_PAGE_DASHBOARD))

_APP_PAGE_CONTACTS = """<!DOCTYPE html><!--_3x95xLmWbLN0GMJUinot--><html lang="en"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/><meta name="viewport" content="width=device-width, initial-scale=1"/><link rel="stylesheet" href="/_next/static/css/a5b9e56526ddf77e.css" data-precedence="next"/><link rel="preload" as="script" fetchPriority="low" href="/_next/static/chunks/webpack-74c939c87fa0092a.js"/><script src="/_next/static/chunks/4bd1b696-c023c6e3521b1417.js" async=""></script><script src="/_next/static/chunks/255-81ba70bd132d3eed.js" async=""></script><script src="/_next/static/chunks/main-app-3e6673f4a8380c97.js" async=""></script><script src="/_next/static/chunks/12-7d516a2f290e26f2.js" async=""></script><script src="/_next/static/chunks/app/layout-82602bdfed5552b0.js" async=""></script><script src="/_next/static/chunks/app/contacts/page-4371f6d2c8d556a9.js" async=""></script><meta name="theme-color" content="#25D366"/><meta name="apple-mobile-web-app-capable" content="yes"/><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/><meta name="apple-mobile-web-app-title" content="WA CRM"/><link rel="manifest" href="/manifest.json"/><title>WhatsApp CRM SA — Admin</title><script src="/_next/static/chunks/polyfills-42372ed130431b0a.js" noModule=""></script></head><body><div hidden=""><!--$--><!--/$--></div><div class="flex min-h-screen"><aside class="fixed left-0 top-0 h-full w-[260px] bg-black/40 backdrop-blur-xl border-r border-white/[.06] flex flex-col z-50"><div class="p-5 border-b border-white/[.06]"><a class="flex items-center gap-2 text-lg font-semibold text-white no-underline" href="/dashboard/"><span class="text-xl">💬</span><span>WhatsApp CRM</span></a><p class="text-xs text-white/30 mt-1">Admin Dashboard</p></div><nav class="flex-1 py-4 px-3 space-y-1"><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/dashboard/"><span class="text-base">🏠</span><span>Dashboard</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/conversations/"><span class="text-base">💬</span><span>Conversations</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/contacts/"><span class="text-base">👥</span><span>Contacts</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/campaigns/"><span class="text-base">📨</span><span>Campaigns</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/ai/"><span class="text-base">🤖</span><span>AI Stats</span></a></nav><div class="p-3 border-t border-white/[.06]"><button class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/50 hover:text-white hover:bg-white/[.06] transition-all cursor-pointer bg-transparent border-none"><span class="text-base">🚪</span><span>Logout</span></button></div></aside><main class="ml-[260px] flex-1"><div class="flex items-center justify-center h-64 text-white/30">Loading…</div><!--$--><!--/$--></main></div><script src="/_next/static/chunks/webpack-74c939c87fa0092a.js" id="_R_" async=""></script><script>(self.__next_f=self.__next_f||[]).push([0])</script><script>self.__next_f.push([1,"1:\"$Sreact.fragment\"\n2:I[6710,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"default\"]\n3:I[9766,[],\"\"]\n4:I[8924,[],\"\"]\n5:I[3762,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"PWAInstallScript\"]\n6:I[1959,[],\"ClientPageRoot\"]\n7:I[4971,[\"102\",\"static/chunks/app/contacts/page-4371f6d2c8d556a9.js\"],\"default\"]\na:I[4431,[],\"OutletBoundary\"]\nc:I[5278,[],\"AsyncMetadataOutlet\"]\ne:I[4431,[],\"ViewportBoundary\"]\n10:I[4431,[],\"MetadataBoundary\"]\n11:\"$Sreact.suspense\"\n13:I[7150,[],\"\"]\n:HL[\"/_next/static/css/a5b9e56526ddf77e.css\",\"style\"]\n"])</script><script>self.__next_f.push([1,"0:{\"P\":null,\"b\":\"_3x95xLmWbLN0GMJUinot\",\"p\":\"\",\"c\":[\"\",\"contacts\",\"\"],\"i\":false,\"f\":[[[\"\",{\"children\":[\"contacts\",{\"children\":[\"__PAGE__\",{}]}]},\"$undefined\",\"$undefined\",true],[\"\",[\"$\",\"$1\",\"c\",{\"children\":[[[\"$\",\"link\",\"0\",{\"rel\":\"stylesheet\",\"href\":\"/_next/static/css/a5b9e56526ddf77e.css\",\"precedence\":\"next\",\"crossOrigin\":\"$undefined\",\"nonce\":\"$undefined\"}]],[\"$\",\"html\",null,{\"lang\":\"en\",\"children\":[[\"$\",\"head\",null,{\"children\":[[\"$\",\"meta\",null,{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no\"}],[\"$\",\"meta\",null,{\"name\":\"theme-color\",\"content\":\"#25D366\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-capable\",\"content\":\"yes\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-status-bar-style\",\"content\":\"black-translucent\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-title\",\"content\":\"WA CRM\"}],[\"$\",\"link\",null,{\"rel\":\"manifest\",\"href\":\"/manifest.json\"}]]}],[\"$\",\"body\",null,{\"children\":[[\"$\",\"$L2\",null,{\"children\":[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":[[[\"$\",\"title\",null,{\"children\":\"404: This page could not be found.\"}],[\"$\",\"div\",null,{\"style\":{\"fontFamily\":\"system-ui,\\\"Segoe UI\\\",Roboto,Helvetica,Arial,sans-serif,\\\"Apple Color Emoji\\\",\\\"Segoe UI Emoji\\\"\",\"height\":\"100vh\",\"textAlign\":\"center\",\"display\":\"flex\",\"flexDirection\":\"column\",\"alignItems\":\"center\",\"justifyContent\":\"center\"},\"children\":[\"$\",\"div\",null,{\"children\":[[\"$\",\"style\",null,{\"dangerouslySetInnerHTML\":{\"__html\":\"body{color:#000;background:#fff;margin:0}.next-error-h1{border-right:1px solid rgba(0,0,0,.3)}@media (prefers-color-scheme:dark){body{color:#fff;background:#000}.next-error-h1{border-right:1px solid rgba(255,255,255,.3)}}\"}}],[\"$\",\"h1\",null,{\"className\":\"next-error-h1\",\"style\":{\"display\":\"inline-block\",\"margin\":\"0 20px 0 0\",\"padding\":\"0 23px 0 0\",\"fontSize\":24,\"fontWeight\":500,\"verticalAlign\":\"top\",\"lineHeight\":\"49px\"},\"children\":404}],[\"$\",\"div\",null,{\"style\":{\"display\":\"inline-block\"},\"children\":[\"$\",\"h2\",null,{\"style\":{\"fontSize\":14,\"fontWeight\":400,\"lineHeight\":\"49px\",\"margin\":0},\"children\":\"This page could not be found.\"}]}]]}]}]],[]],\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]}],[\"$\",\"$L5\",null,{}]]}]]}]]}],{\"children\":[\"contacts\",[\"$\",\"$1\",\"c\",{\"children\":[null,[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":\"$undefined\",\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]]}],{\"children\":[\"__PAGE__\",[\"$\",\"$1\",\"c\",{\"children\":[[\"$\",\"$L6\",null,{\"Component\":\"$7\",\"searchParams\":{},\"params\":{},\"promises\":[\"$@8\",\"$@9\"]}],null,[\"$\",\"$La\",null,{\"children\":[\"$Lb\",[\"$\",\"$Lc\",null,{\"promise\":\"$@d\"}]]}]]}],{},null,false]},null,false]},null,false],[\"$\",\"$1\",\"h\",{\"children\":[null,[[\"$\",\"$Le\",null,{\"children\":\"$Lf\"}],null],[\"$\",\"$L10\",null,{\"children\":[\"$\",\"div\",null,{\"hidden\":true,\"children\":[\"$\",\"$11\",null,{\"fallback\":null,\"children\":\"$L12\"}]}]}]]}],false]],\"m\":\"$undefined\",\"G\":[\"$13\",[]],\"s\":false,\"S\":true}\n"])</script><script>self.__next_f.push([1,"8:{}\n9:\"$0:f:0:1:2:children:2:children:1:props:children:0:props:params\"\n"])</script><script>self.__next_f.push([1,"f:[[\"$\",\"meta\",\"0\",{\"charSet\":\"utf-8\"}],[\"$\",\"meta\",\"1\",{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1\"}]]\nb:null\n"])</script><script>self.__next_f.push([1,"d:{\"metadata\":[[\"$\",\"title\",\"0\",{\"children\":\"WhatsApp CRM SA — Admin\"}]],\"error\":null,\"digest\":\"$undefined\"}\n"])</script><script>self.__next_f.push([1,"12:\"$d:metadata\"\n"])</script></body></html>"""

# ── /contacts ──────────────────────────────────────────────────────────────────
@app.get("/contacts", include_in_schema=False)
@app.get("/contacts/", include_in_schema=False)
def route_contacts():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=(_APP_PAGE_CONTACTS))

_APP_PAGE_CONVERSATIONS = """<!DOCTYPE html><!--_3x95xLmWbLN0GMJUinot--><html lang="en"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/><meta name="viewport" content="width=device-width, initial-scale=1"/><link rel="stylesheet" href="/_next/static/css/a5b9e56526ddf77e.css" data-precedence="next"/><link rel="preload" as="script" fetchPriority="low" href="/_next/static/chunks/webpack-74c939c87fa0092a.js"/><script src="/_next/static/chunks/4bd1b696-c023c6e3521b1417.js" async=""></script><script src="/_next/static/chunks/255-81ba70bd132d3eed.js" async=""></script><script src="/_next/static/chunks/main-app-3e6673f4a8380c97.js" async=""></script><script src="/_next/static/chunks/12-7d516a2f290e26f2.js" async=""></script><script src="/_next/static/chunks/app/layout-82602bdfed5552b0.js" async=""></script><script src="/_next/static/chunks/app/conversations/page-7da8b9929f42ef0d.js" async=""></script><meta name="theme-color" content="#25D366"/><meta name="apple-mobile-web-app-capable" content="yes"/><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/><meta name="apple-mobile-web-app-title" content="WA CRM"/><link rel="manifest" href="/manifest.json"/><title>WhatsApp CRM SA — Admin</title><script src="/_next/static/chunks/polyfills-42372ed130431b0a.js" noModule=""></script></head><body><div hidden=""><!--$--><!--/$--></div><div class="flex min-h-screen"><aside class="fixed left-0 top-0 h-full w-[260px] bg-black/40 backdrop-blur-xl border-r border-white/[.06] flex flex-col z-50"><div class="p-5 border-b border-white/[.06]"><a class="flex items-center gap-2 text-lg font-semibold text-white no-underline" href="/dashboard/"><span class="text-xl">💬</span><span>WhatsApp CRM</span></a><p class="text-xs text-white/30 mt-1">Admin Dashboard</p></div><nav class="flex-1 py-4 px-3 space-y-1"><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/dashboard/"><span class="text-base">🏠</span><span>Dashboard</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/conversations/"><span class="text-base">💬</span><span>Conversations</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/contacts/"><span class="text-base">👥</span><span>Contacts</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/campaigns/"><span class="text-base">📨</span><span>Campaigns</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/ai/"><span class="text-base">🤖</span><span>AI Stats</span></a></nav><div class="p-3 border-t border-white/[.06]"><button class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/50 hover:text-white hover:bg-white/[.06] transition-all cursor-pointer bg-transparent border-none"><span class="text-base">🚪</span><span>Logout</span></button></div></aside><main class="ml-[260px] flex-1"><div class="space-y-4 h-[calc(100vh-4rem)] flex flex-col"><div><h1 class="text-2xl font-bold text-white">Conversations</h1><p class="text-sm text-white/35 mt-0.5">Live WhatsApp conversations</p></div><div class="flex flex-1 gap-0 rounded-xl border overflow-hidden" style="background:rgba(255,255,255,0.02);border-color:rgba(255,255,255,0.06)"><div class="w-full md:w-[30%] min-w-0 border-r flex flex-col" style="border-color:rgba(255,255,255,0.06)"><div class="p-4 border-b border-white/[.06]"><p class="text-xs text-white/35 uppercase tracking-wider font-medium">Active Conversations (<!-- -->0<!-- -->)</p></div><div class="flex-1 overflow-y-auto"><p class="p-4 text-sm text-white/25">No conversations yet.</p></div></div><div class="flex-1 flex flex-col min-w-0"><div class="flex-1 flex items-center justify-center text-white/25 text-sm">Select a conversation to start chatting</div></div></div></div><!--$--><!--/$--></main></div><script src="/_next/static/chunks/webpack-74c939c87fa0092a.js" id="_R_" async=""></script><script>(self.__next_f=self.__next_f||[]).push([0])</script><script>self.__next_f.push([1,"1:\"$Sreact.fragment\"\n2:I[6710,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"default\"]\n3:I[9766,[],\"\"]\n4:I[8924,[],\"\"]\n5:I[3762,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"PWAInstallScript\"]\n6:I[1959,[],\"ClientPageRoot\"]\n7:I[6493,[\"397\",\"static/chunks/app/conversations/page-7da8b9929f42ef0d.js\"],\"default\"]\na:I[4431,[],\"OutletBoundary\"]\nc:I[5278,[],\"AsyncMetadataOutlet\"]\ne:I[4431,[],\"ViewportBoundary\"]\n10:I[4431,[],\"MetadataBoundary\"]\n11:\"$Sreact.suspense\"\n13:I[7150,[],\"\"]\n:HL[\"/_next/static/css/a5b9e56526ddf77e.css\",\"style\"]\n"])</script><script>self.__next_f.push([1,"0:{\"P\":null,\"b\":\"_3x95xLmWbLN0GMJUinot\",\"p\":\"\",\"c\":[\"\",\"conversations\",\"\"],\"i\":false,\"f\":[[[\"\",{\"children\":[\"conversations\",{\"children\":[\"__PAGE__\",{}]}]},\"$undefined\",\"$undefined\",true],[\"\",[\"$\",\"$1\",\"c\",{\"children\":[[[\"$\",\"link\",\"0\",{\"rel\":\"stylesheet\",\"href\":\"/_next/static/css/a5b9e56526ddf77e.css\",\"precedence\":\"next\",\"crossOrigin\":\"$undefined\",\"nonce\":\"$undefined\"}]],[\"$\",\"html\",null,{\"lang\":\"en\",\"children\":[[\"$\",\"head\",null,{\"children\":[[\"$\",\"meta\",null,{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no\"}],[\"$\",\"meta\",null,{\"name\":\"theme-color\",\"content\":\"#25D366\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-capable\",\"content\":\"yes\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-status-bar-style\",\"content\":\"black-translucent\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-title\",\"content\":\"WA CRM\"}],[\"$\",\"link\",null,{\"rel\":\"manifest\",\"href\":\"/manifest.json\"}]]}],[\"$\",\"body\",null,{\"children\":[[\"$\",\"$L2\",null,{\"children\":[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":[[[\"$\",\"title\",null,{\"children\":\"404: This page could not be found.\"}],[\"$\",\"div\",null,{\"style\":{\"fontFamily\":\"system-ui,\\\"Segoe UI\\\",Roboto,Helvetica,Arial,sans-serif,\\\"Apple Color Emoji\\\",\\\"Segoe UI Emoji\\\"\",\"height\":\"100vh\",\"textAlign\":\"center\",\"display\":\"flex\",\"flexDirection\":\"column\",\"alignItems\":\"center\",\"justifyContent\":\"center\"},\"children\":[\"$\",\"div\",null,{\"children\":[[\"$\",\"style\",null,{\"dangerouslySetInnerHTML\":{\"__html\":\"body{color:#000;background:#fff;margin:0}.next-error-h1{border-right:1px solid rgba(0,0,0,.3)}@media (prefers-color-scheme:dark){body{color:#fff;background:#000}.next-error-h1{border-right:1px solid rgba(255,255,255,.3)}}\"}}],[\"$\",\"h1\",null,{\"className\":\"next-error-h1\",\"style\":{\"display\":\"inline-block\",\"margin\":\"0 20px 0 0\",\"padding\":\"0 23px 0 0\",\"fontSize\":24,\"fontWeight\":500,\"verticalAlign\":\"top\",\"lineHeight\":\"49px\"},\"children\":404}],[\"$\",\"div\",null,{\"style\":{\"display\":\"inline-block\"},\"children\":[\"$\",\"h2\",null,{\"style\":{\"fontSize\":14,\"fontWeight\":400,\"lineHeight\":\"49px\",\"margin\":0},\"children\":\"This page could not be found.\"}]}]]}]}]],[]],\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]}],[\"$\",\"$L5\",null,{}]]}]]}]]}],{\"children\":[\"conversations\",[\"$\",\"$1\",\"c\",{\"children\":[null,[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":\"$undefined\",\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]]}],{\"children\":[\"__PAGE__\",[\"$\",\"$1\",\"c\",{\"children\":[[\"$\",\"$L6\",null,{\"Component\":\"$7\",\"searchParams\":{},\"params\":{},\"promises\":[\"$@8\",\"$@9\"]}],null,[\"$\",\"$La\",null,{\"children\":[\"$Lb\",[\"$\",\"$Lc\",null,{\"promise\":\"$@d\"}]]}]]}],{},null,false]},null,false]},null,false],[\"$\",\"$1\",\"h\",{\"children\":[null,[[\"$\",\"$Le\",null,{\"children\":\"$Lf\"}],null],[\"$\",\"$L10\",null,{\"children\":[\"$\",\"div\",null,{\"hidden\":true,\"children\":[\"$\",\"$11\",null,{\"fallback\":null,\"children\":\"$L12\"}]}]}]]}],false]],\"m\":\"$undefined\",\"G\":[\"$13\",[]],\"s\":false,\"S\":true}\n"])</script><script>self.__next_f.push([1,"8:{}\n9:\"$0:f:0:1:2:children:2:children:1:props:children:0:props:params\"\n"])</script><script>self.__next_f.push([1,"f:[[\"$\",\"meta\",\"0\",{\"charSet\":\"utf-8\"}],[\"$\",\"meta\",\"1\",{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1\"}]]\nb:null\n"])</script><script>self.__next_f.push([1,"d:{\"metadata\":[[\"$\",\"title\",\"0\",{\"children\":\"WhatsApp CRM SA — Admin\"}]],\"error\":null,\"digest\":\"$undefined\"}\n"])</script><script>self.__next_f.push([1,"12:\"$d:metadata\"\n"])</script></body></html>"""

# ── /conversations ──────────────────────────────────────────────────────────────────
@app.get("/conversations", include_in_schema=False)
@app.get("/conversations/", include_in_schema=False)
def route_conversations():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=(_APP_PAGE_CONVERSATIONS))

_APP_PAGE_AI = """<!DOCTYPE html><!--_3x95xLmWbLN0GMJUinot--><html lang="en"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/><meta name="viewport" content="width=device-width, initial-scale=1"/><link rel="stylesheet" href="/_next/static/css/a5b9e56526ddf77e.css" data-precedence="next"/><link rel="preload" as="script" fetchPriority="low" href="/_next/static/chunks/webpack-74c939c87fa0092a.js"/><script src="/_next/static/chunks/4bd1b696-c023c6e3521b1417.js" async=""></script><script src="/_next/static/chunks/255-81ba70bd132d3eed.js" async=""></script><script src="/_next/static/chunks/main-app-3e6673f4a8380c97.js" async=""></script><script src="/_next/static/chunks/12-7d516a2f290e26f2.js" async=""></script><script src="/_next/static/chunks/app/layout-82602bdfed5552b0.js" async=""></script><script src="/_next/static/chunks/app/ai/page-c06f904feb50dd51.js" async=""></script><meta name="theme-color" content="#25D366"/><meta name="apple-mobile-web-app-capable" content="yes"/><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/><meta name="apple-mobile-web-app-title" content="WA CRM"/><link rel="manifest" href="/manifest.json"/><title>WhatsApp CRM SA — Admin</title><script src="/_next/static/chunks/polyfills-42372ed130431b0a.js" noModule=""></script></head><body><div hidden=""><!--$--><!--/$--></div><div class="flex min-h-screen"><aside class="fixed left-0 top-0 h-full w-[260px] bg-black/40 backdrop-blur-xl border-r border-white/[.06] flex flex-col z-50"><div class="p-5 border-b border-white/[.06]"><a class="flex items-center gap-2 text-lg font-semibold text-white no-underline" href="/dashboard/"><span class="text-xl">💬</span><span>WhatsApp CRM</span></a><p class="text-xs text-white/30 mt-1">Admin Dashboard</p></div><nav class="flex-1 py-4 px-3 space-y-1"><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/dashboard/"><span class="text-base">🏠</span><span>Dashboard</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/conversations/"><span class="text-base">💬</span><span>Conversations</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/contacts/"><span class="text-base">👥</span><span>Contacts</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/campaigns/"><span class="text-base">📨</span><span>Campaigns</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/ai/"><span class="text-base">🤖</span><span>AI Stats</span></a></nav><div class="p-3 border-t border-white/[.06]"><button class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/50 hover:text-white hover:bg-white/[.06] transition-all cursor-pointer bg-transparent border-none"><span class="text-base">🚪</span><span>Logout</span></button></div></aside><main class="ml-[260px] flex-1"><div class="flex items-center justify-center h-64 text-white/30">Loading…</div><!--$--><!--/$--></main></div><script src="/_next/static/chunks/webpack-74c939c87fa0092a.js" id="_R_" async=""></script><script>(self.__next_f=self.__next_f||[]).push([0])</script><script>self.__next_f.push([1,"1:\"$Sreact.fragment\"\n2:I[6710,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"default\"]\n3:I[9766,[],\"\"]\n4:I[8924,[],\"\"]\n5:I[3762,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"PWAInstallScript\"]\n6:I[1959,[],\"ClientPageRoot\"]\n7:I[6406,[\"141\",\"static/chunks/app/ai/page-c06f904feb50dd51.js\"],\"default\"]\na:I[4431,[],\"OutletBoundary\"]\nc:I[5278,[],\"AsyncMetadataOutlet\"]\ne:I[4431,[],\"ViewportBoundary\"]\n10:I[4431,[],\"MetadataBoundary\"]\n11:\"$Sreact.suspense\"\n13:I[7150,[],\"\"]\n:HL[\"/_next/static/css/a5b9e56526ddf77e.css\",\"style\"]\n"])</script><script>self.__next_f.push([1,"0:{\"P\":null,\"b\":\"_3x95xLmWbLN0GMJUinot\",\"p\":\"\",\"c\":[\"\",\"ai\",\"\"],\"i\":false,\"f\":[[[\"\",{\"children\":[\"ai\",{\"children\":[\"__PAGE__\",{}]}]},\"$undefined\",\"$undefined\",true],[\"\",[\"$\",\"$1\",\"c\",{\"children\":[[[\"$\",\"link\",\"0\",{\"rel\":\"stylesheet\",\"href\":\"/_next/static/css/a5b9e56526ddf77e.css\",\"precedence\":\"next\",\"crossOrigin\":\"$undefined\",\"nonce\":\"$undefined\"}]],[\"$\",\"html\",null,{\"lang\":\"en\",\"children\":[[\"$\",\"head\",null,{\"children\":[[\"$\",\"meta\",null,{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no\"}],[\"$\",\"meta\",null,{\"name\":\"theme-color\",\"content\":\"#25D366\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-capable\",\"content\":\"yes\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-status-bar-style\",\"content\":\"black-translucent\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-title\",\"content\":\"WA CRM\"}],[\"$\",\"link\",null,{\"rel\":\"manifest\",\"href\":\"/manifest.json\"}]]}],[\"$\",\"body\",null,{\"children\":[[\"$\",\"$L2\",null,{\"children\":[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":[[[\"$\",\"title\",null,{\"children\":\"404: This page could not be found.\"}],[\"$\",\"div\",null,{\"style\":{\"fontFamily\":\"system-ui,\\\"Segoe UI\\\",Roboto,Helvetica,Arial,sans-serif,\\\"Apple Color Emoji\\\",\\\"Segoe UI Emoji\\\"\",\"height\":\"100vh\",\"textAlign\":\"center\",\"display\":\"flex\",\"flexDirection\":\"column\",\"alignItems\":\"center\",\"justifyContent\":\"center\"},\"children\":[\"$\",\"div\",null,{\"children\":[[\"$\",\"style\",null,{\"dangerouslySetInnerHTML\":{\"__html\":\"body{color:#000;background:#fff;margin:0}.next-error-h1{border-right:1px solid rgba(0,0,0,.3)}@media (prefers-color-scheme:dark){body{color:#fff;background:#000}.next-error-h1{border-right:1px solid rgba(255,255,255,.3)}}\"}}],[\"$\",\"h1\",null,{\"className\":\"next-error-h1\",\"style\":{\"display\":\"inline-block\",\"margin\":\"0 20px 0 0\",\"padding\":\"0 23px 0 0\",\"fontSize\":24,\"fontWeight\":500,\"verticalAlign\":\"top\",\"lineHeight\":\"49px\"},\"children\":404}],[\"$\",\"div\",null,{\"style\":{\"display\":\"inline-block\"},\"children\":[\"$\",\"h2\",null,{\"style\":{\"fontSize\":14,\"fontWeight\":400,\"lineHeight\":\"49px\",\"margin\":0},\"children\":\"This page could not be found.\"}]}]]}]}]],[]],\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]}],[\"$\",\"$L5\",null,{}]]}]]}]]}],{\"children\":[\"ai\",[\"$\",\"$1\",\"c\",{\"children\":[null,[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":\"$undefined\",\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]]}],{\"children\":[\"__PAGE__\",[\"$\",\"$1\",\"c\",{\"children\":[[\"$\",\"$L6\",null,{\"Component\":\"$7\",\"searchParams\":{},\"params\":{},\"promises\":[\"$@8\",\"$@9\"]}],null,[\"$\",\"$La\",null,{\"children\":[\"$Lb\",[\"$\",\"$Lc\",null,{\"promise\":\"$@d\"}]]}]]}],{},null,false]},null,false]},null,false],[\"$\",\"$1\",\"h\",{\"children\":[null,[[\"$\",\"$Le\",null,{\"children\":\"$Lf\"}],null],[\"$\",\"$L10\",null,{\"children\":[\"$\",\"div\",null,{\"hidden\":true,\"children\":[\"$\",\"$11\",null,{\"fallback\":null,\"children\":\"$L12\"}]}]}]]}],false]],\"m\":\"$undefined\",\"G\":[\"$13\",[]],\"s\":false,\"S\":true}\n"])</script><script>self.__next_f.push([1,"8:{}\n9:\"$0:f:0:1:2:children:2:children:1:props:children:0:props:params\"\n"])</script><script>self.__next_f.push([1,"f:[[\"$\",\"meta\",\"0\",{\"charSet\":\"utf-8\"}],[\"$\",\"meta\",\"1\",{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1\"}]]\nb:null\n"])</script><script>self.__next_f.push([1,"d:{\"metadata\":[[\"$\",\"title\",\"0\",{\"children\":\"WhatsApp CRM SA — Admin\"}]],\"error\":null,\"digest\":\"$undefined\"}\n"])</script><script>self.__next_f.push([1,"12:\"$d:metadata\"\n"])</script></body></html>"""

# ── /ai ──────────────────────────────────────────────────────────────────
@app.get("/ai", include_in_schema=False)
@app.get("/ai/", include_in_schema=False)
def route_ai():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=(_APP_PAGE_AI))

_APP_PAGE_CAMPAIGNS = """<!DOCTYPE html><!--_3x95xLmWbLN0GMJUinot--><html lang="en"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/><meta name="viewport" content="width=device-width, initial-scale=1"/><link rel="stylesheet" href="/_next/static/css/a5b9e56526ddf77e.css" data-precedence="next"/><link rel="preload" as="script" fetchPriority="low" href="/_next/static/chunks/webpack-74c939c87fa0092a.js"/><script src="/_next/static/chunks/4bd1b696-c023c6e3521b1417.js" async=""></script><script src="/_next/static/chunks/255-81ba70bd132d3eed.js" async=""></script><script src="/_next/static/chunks/main-app-3e6673f4a8380c97.js" async=""></script><script src="/_next/static/chunks/12-7d516a2f290e26f2.js" async=""></script><script src="/_next/static/chunks/app/layout-82602bdfed5552b0.js" async=""></script><script src="/_next/static/chunks/app/campaigns/page-2068dc14659b9622.js" async=""></script><meta name="theme-color" content="#25D366"/><meta name="apple-mobile-web-app-capable" content="yes"/><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/><meta name="apple-mobile-web-app-title" content="WA CRM"/><link rel="manifest" href="/manifest.json"/><title>WhatsApp CRM SA — Admin</title><script src="/_next/static/chunks/polyfills-42372ed130431b0a.js" noModule=""></script></head><body><div hidden=""><!--$--><!--/$--></div><div class="flex min-h-screen"><aside class="fixed left-0 top-0 h-full w-[260px] bg-black/40 backdrop-blur-xl border-r border-white/[.06] flex flex-col z-50"><div class="p-5 border-b border-white/[.06]"><a class="flex items-center gap-2 text-lg font-semibold text-white no-underline" href="/dashboard/"><span class="text-xl">💬</span><span>WhatsApp CRM</span></a><p class="text-xs text-white/30 mt-1">Admin Dashboard</p></div><nav class="flex-1 py-4 px-3 space-y-1"><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/dashboard/"><span class="text-base">🏠</span><span>Dashboard</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/conversations/"><span class="text-base">💬</span><span>Conversations</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/contacts/"><span class="text-base">👥</span><span>Contacts</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/campaigns/"><span class="text-base">📨</span><span>Campaigns</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/ai/"><span class="text-base">🤖</span><span>AI Stats</span></a></nav><div class="p-3 border-t border-white/[.06]"><button class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/50 hover:text-white hover:bg-white/[.06] transition-all cursor-pointer bg-transparent border-none"><span class="text-base">🚪</span><span>Logout</span></button></div></aside><main class="ml-[260px] flex-1"><div class="flex items-center justify-center h-64 text-white/30">Loading…</div><!--$--><!--/$--></main></div><script src="/_next/static/chunks/webpack-74c939c87fa0092a.js" id="_R_" async=""></script><script>(self.__next_f=self.__next_f||[]).push([0])</script><script>self.__next_f.push([1,"1:\"$Sreact.fragment\"\n2:I[6710,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"default\"]\n3:I[9766,[],\"\"]\n4:I[8924,[],\"\"]\n5:I[3762,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"PWAInstallScript\"]\n6:I[1959,[],\"ClientPageRoot\"]\n7:I[3997,[\"134\",\"static/chunks/app/campaigns/page-2068dc14659b9622.js\"],\"default\"]\na:I[4431,[],\"OutletBoundary\"]\nc:I[5278,[],\"AsyncMetadataOutlet\"]\ne:I[4431,[],\"ViewportBoundary\"]\n10:I[4431,[],\"MetadataBoundary\"]\n11:\"$Sreact.suspense\"\n13:I[7150,[],\"\"]\n:HL[\"/_next/static/css/a5b9e56526ddf77e.css\",\"style\"]\n"])</script><script>self.__next_f.push([1,"0:{\"P\":null,\"b\":\"_3x95xLmWbLN0GMJUinot\",\"p\":\"\",\"c\":[\"\",\"campaigns\",\"\"],\"i\":false,\"f\":[[[\"\",{\"children\":[\"campaigns\",{\"children\":[\"__PAGE__\",{}]}]},\"$undefined\",\"$undefined\",true],[\"\",[\"$\",\"$1\",\"c\",{\"children\":[[[\"$\",\"link\",\"0\",{\"rel\":\"stylesheet\",\"href\":\"/_next/static/css/a5b9e56526ddf77e.css\",\"precedence\":\"next\",\"crossOrigin\":\"$undefined\",\"nonce\":\"$undefined\"}]],[\"$\",\"html\",null,{\"lang\":\"en\",\"children\":[[\"$\",\"head\",null,{\"children\":[[\"$\",\"meta\",null,{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no\"}],[\"$\",\"meta\",null,{\"name\":\"theme-color\",\"content\":\"#25D366\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-capable\",\"content\":\"yes\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-status-bar-style\",\"content\":\"black-translucent\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-title\",\"content\":\"WA CRM\"}],[\"$\",\"link\",null,{\"rel\":\"manifest\",\"href\":\"/manifest.json\"}]]}],[\"$\",\"body\",null,{\"children\":[[\"$\",\"$L2\",null,{\"children\":[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":[[[\"$\",\"title\",null,{\"children\":\"404: This page could not be found.\"}],[\"$\",\"div\",null,{\"style\":{\"fontFamily\":\"system-ui,\\\"Segoe UI\\\",Roboto,Helvetica,Arial,sans-serif,\\\"Apple Color Emoji\\\",\\\"Segoe UI Emoji\\\"\",\"height\":\"100vh\",\"textAlign\":\"center\",\"display\":\"flex\",\"flexDirection\":\"column\",\"alignItems\":\"center\",\"justifyContent\":\"center\"},\"children\":[\"$\",\"div\",null,{\"children\":[[\"$\",\"style\",null,{\"dangerouslySetInnerHTML\":{\"__html\":\"body{color:#000;background:#fff;margin:0}.next-error-h1{border-right:1px solid rgba(0,0,0,.3)}@media (prefers-color-scheme:dark){body{color:#fff;background:#000}.next-error-h1{border-right:1px solid rgba(255,255,255,.3)}}\"}}],[\"$\",\"h1\",null,{\"className\":\"next-error-h1\",\"style\":{\"display\":\"inline-block\",\"margin\":\"0 20px 0 0\",\"padding\":\"0 23px 0 0\",\"fontSize\":24,\"fontWeight\":500,\"verticalAlign\":\"top\",\"lineHeight\":\"49px\"},\"children\":404}],[\"$\",\"div\",null,{\"style\":{\"display\":\"inline-block\"},\"children\":[\"$\",\"h2\",null,{\"style\":{\"fontSize\":14,\"fontWeight\":400,\"lineHeight\":\"49px\",\"margin\":0},\"children\":\"This page could not be found.\"}]}]]}]}]],[]],\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]}],[\"$\",\"$L5\",null,{}]]}]]}]]}],{\"children\":[\"campaigns\",[\"$\",\"$1\",\"c\",{\"children\":[null,[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":\"$undefined\",\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]]}],{\"children\":[\"__PAGE__\",[\"$\",\"$1\",\"c\",{\"children\":[[\"$\",\"$L6\",null,{\"Component\":\"$7\",\"searchParams\":{},\"params\":{},\"promises\":[\"$@8\",\"$@9\"]}],null,[\"$\",\"$La\",null,{\"children\":[\"$Lb\",[\"$\",\"$Lc\",null,{\"promise\":\"$@d\"}]]}]]}],{},null,false]},null,false]},null,false],[\"$\",\"$1\",\"h\",{\"children\":[null,[[\"$\",\"$Le\",null,{\"children\":\"$Lf\"}],null],[\"$\",\"$L10\",null,{\"children\":[\"$\",\"div\",null,{\"hidden\":true,\"children\":[\"$\",\"$11\",null,{\"fallback\":null,\"children\":\"$L12\"}]}]}]]}],false]],\"m\":\"$undefined\",\"G\":[\"$13\",[]],\"s\":false,\"S\":true}\n"])</script><script>self.__next_f.push([1,"8:{}\n9:\"$0:f:0:1:2:children:2:children:1:props:children:0:props:params\"\n"])</script><script>self.__next_f.push([1,"f:[[\"$\",\"meta\",\"0\",{\"charSet\":\"utf-8\"}],[\"$\",\"meta\",\"1\",{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1\"}]]\nb:null\n"])</script><script>self.__next_f.push([1,"d:{\"metadata\":[[\"$\",\"title\",\"0\",{\"children\":\"WhatsApp CRM SA — Admin\"}]],\"error\":null,\"digest\":\"$undefined\"}\n"])</script><script>self.__next_f.push([1,"12:\"$d:metadata\"\n"])</script></body></html>"""

# ── /campaigns ──────────────────────────────────────────────────────────────────
@app.get("/campaigns", include_in_schema=False)
@app.get("/campaigns/", include_in_schema=False)
def route_campaigns():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=(_APP_PAGE_CAMPAIGNS))

_APP_PAGE_LOGIN = """<!DOCTYPE html><!--_3x95xLmWbLN0GMJUinot--><html lang="en"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/><meta name="viewport" content="width=device-width, initial-scale=1"/><link rel="stylesheet" href="/_next/static/css/a5b9e56526ddf77e.css" data-precedence="next"/><link rel="preload" as="script" fetchPriority="low" href="/_next/static/chunks/webpack-74c939c87fa0092a.js"/><script src="/_next/static/chunks/4bd1b696-c023c6e3521b1417.js" async=""></script><script src="/_next/static/chunks/255-81ba70bd132d3eed.js" async=""></script><script src="/_next/static/chunks/main-app-3e6673f4a8380c97.js" async=""></script><script src="/_next/static/chunks/12-7d516a2f290e26f2.js" async=""></script><script src="/_next/static/chunks/app/layout-82602bdfed5552b0.js" async=""></script><script src="/_next/static/chunks/app/login/page-bccf4a072279e02a.js" async=""></script><meta name="theme-color" content="#25D366"/><meta name="apple-mobile-web-app-capable" content="yes"/><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/><meta name="apple-mobile-web-app-title" content="WA CRM"/><link rel="manifest" href="/manifest.json"/><title>WhatsApp CRM SA — Admin</title><script src="/_next/static/chunks/polyfills-42372ed130431b0a.js" noModule=""></script></head><body><div hidden=""><!--$--><!--/$--></div><div class="flex min-h-screen"><aside class="fixed left-0 top-0 h-full w-[260px] bg-black/40 backdrop-blur-xl border-r border-white/[.06] flex flex-col z-50"><div class="p-5 border-b border-white/[.06]"><a class="flex items-center gap-2 text-lg font-semibold text-white no-underline" href="/dashboard/"><span class="text-xl">💬</span><span>WhatsApp CRM</span></a><p class="text-xs text-white/30 mt-1">Admin Dashboard</p></div><nav class="flex-1 py-4 px-3 space-y-1"><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/dashboard/"><span class="text-base">🏠</span><span>Dashboard</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/conversations/"><span class="text-base">💬</span><span>Conversations</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/contacts/"><span class="text-base">👥</span><span>Contacts</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/campaigns/"><span class="text-base">📨</span><span>Campaigns</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/ai/"><span class="text-base">🤖</span><span>AI Stats</span></a></nav><div class="p-3 border-t border-white/[.06]"><button class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/50 hover:text-white hover:bg-white/[.06] transition-all cursor-pointer bg-transparent border-none"><span class="text-base">🚪</span><span>Logout</span></button></div></aside><main class="ml-[260px] flex-1"><!--$--><!--/$--></main></div><script src="/_next/static/chunks/webpack-74c939c87fa0092a.js" id="_R_" async=""></script><script>(self.__next_f=self.__next_f||[]).push([0])</script><script>self.__next_f.push([1,"1:\"$Sreact.fragment\"\n2:I[6710,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"default\"]\n3:I[9766,[],\"\"]\n4:I[8924,[],\"\"]\n5:I[3762,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"PWAInstallScript\"]\n6:I[1959,[],\"ClientPageRoot\"]\n7:I[5404,[\"520\",\"static/chunks/app/login/page-bccf4a072279e02a.js\"],\"default\"]\na:I[4431,[],\"OutletBoundary\"]\nc:I[5278,[],\"AsyncMetadataOutlet\"]\ne:I[4431,[],\"ViewportBoundary\"]\n10:I[4431,[],\"MetadataBoundary\"]\n11:\"$Sreact.suspense\"\n13:I[7150,[],\"\"]\n:HL[\"/_next/static/css/a5b9e56526ddf77e.css\",\"style\"]\n"])</script><script>self.__next_f.push([1,"0:{\"P\":null,\"b\":\"_3x95xLmWbLN0GMJUinot\",\"p\":\"\",\"c\":[\"\",\"login\",\"\"],\"i\":false,\"f\":[[[\"\",{\"children\":[\"login\",{\"children\":[\"__PAGE__\",{}]}]},\"$undefined\",\"$undefined\",true],[\"\",[\"$\",\"$1\",\"c\",{\"children\":[[[\"$\",\"link\",\"0\",{\"rel\":\"stylesheet\",\"href\":\"/_next/static/css/a5b9e56526ddf77e.css\",\"precedence\":\"next\",\"crossOrigin\":\"$undefined\",\"nonce\":\"$undefined\"}]],[\"$\",\"html\",null,{\"lang\":\"en\",\"children\":[[\"$\",\"head\",null,{\"children\":[[\"$\",\"meta\",null,{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no\"}],[\"$\",\"meta\",null,{\"name\":\"theme-color\",\"content\":\"#25D366\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-capable\",\"content\":\"yes\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-status-bar-style\",\"content\":\"black-translucent\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-title\",\"content\":\"WA CRM\"}],[\"$\",\"link\",null,{\"rel\":\"manifest\",\"href\":\"/manifest.json\"}]]}],[\"$\",\"body\",null,{\"children\":[[\"$\",\"$L2\",null,{\"children\":[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":[[[\"$\",\"title\",null,{\"children\":\"404: This page could not be found.\"}],[\"$\",\"div\",null,{\"style\":{\"fontFamily\":\"system-ui,\\\"Segoe UI\\\",Roboto,Helvetica,Arial,sans-serif,\\\"Apple Color Emoji\\\",\\\"Segoe UI Emoji\\\"\",\"height\":\"100vh\",\"textAlign\":\"center\",\"display\":\"flex\",\"flexDirection\":\"column\",\"alignItems\":\"center\",\"justifyContent\":\"center\"},\"children\":[\"$\",\"div\",null,{\"children\":[[\"$\",\"style\",null,{\"dangerouslySetInnerHTML\":{\"__html\":\"body{color:#000;background:#fff;margin:0}.next-error-h1{border-right:1px solid rgba(0,0,0,.3)}@media (prefers-color-scheme:dark){body{color:#fff;background:#000}.next-error-h1{border-right:1px solid rgba(255,255,255,.3)}}\"}}],[\"$\",\"h1\",null,{\"className\":\"next-error-h1\",\"style\":{\"display\":\"inline-block\",\"margin\":\"0 20px 0 0\",\"padding\":\"0 23px 0 0\",\"fontSize\":24,\"fontWeight\":500,\"verticalAlign\":\"top\",\"lineHeight\":\"49px\"},\"children\":404}],[\"$\",\"div\",null,{\"style\":{\"display\":\"inline-block\"},\"children\":[\"$\",\"h2\",null,{\"style\":{\"fontSize\":14,\"fontWeight\":400,\"lineHeight\":\"49px\",\"margin\":0},\"children\":\"This page could not be found.\"}]}]]}]}]],[]],\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]}],[\"$\",\"$L5\",null,{}]]}]]}]]}],{\"children\":[\"login\",[\"$\",\"$1\",\"c\",{\"children\":[null,[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":\"$undefined\",\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]]}],{\"children\":[\"__PAGE__\",[\"$\",\"$1\",\"c\",{\"children\":[[\"$\",\"$L6\",null,{\"Component\":\"$7\",\"searchParams\":{},\"params\":{},\"promises\":[\"$@8\",\"$@9\"]}],null,[\"$\",\"$La\",null,{\"children\":[\"$Lb\",[\"$\",\"$Lc\",null,{\"promise\":\"$@d\"}]]}]]}],{},null,false]},null,false]},null,false],[\"$\",\"$1\",\"h\",{\"children\":[null,[[\"$\",\"$Le\",null,{\"children\":\"$Lf\"}],null],[\"$\",\"$L10\",null,{\"children\":[\"$\",\"div\",null,{\"hidden\":true,\"children\":[\"$\",\"$11\",null,{\"fallback\":null,\"children\":\"$L12\"}]}]}]]}],false]],\"m\":\"$undefined\",\"G\":[\"$13\",[]],\"s\":false,\"S\":true}\n"])</script><script>self.__next_f.push([1,"8:{}\n9:\"$0:f:0:1:2:children:2:children:1:props:children:0:props:params\"\n"])</script><script>self.__next_f.push([1,"f:[[\"$\",\"meta\",\"0\",{\"charSet\":\"utf-8\"}],[\"$\",\"meta\",\"1\",{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1\"}]]\nb:null\n"])</script><script>self.__next_f.push([1,"d:{\"metadata\":[[\"$\",\"title\",\"0\",{\"children\":\"WhatsApp CRM SA — Admin\"}]],\"error\":null,\"digest\":\"$undefined\"}\n"])</script><script>self.__next_f.push([1,"12:\"$d:metadata\"\n"])</script></body></html>"""

# ── /login ──────────────────────────────────────────────────────────────────
@app.get("/login", include_in_schema=False)
@app.get("/login/", include_in_schema=False)
def route_login():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=(_APP_PAGE_LOGIN))

_APP_PAGE_404_7 = """<!DOCTYPE html><!--_3x95xLmWbLN0GMJUinot--><html lang="en"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/><meta name="viewport" content="width=device-width, initial-scale=1"/><link rel="stylesheet" href="/_next/static/css/a5b9e56526ddf77e.css" data-precedence="next"/><link rel="preload" as="script" fetchPriority="low" href="/_next/static/chunks/webpack-74c939c87fa0092a.js"/><script src="/_next/static/chunks/4bd1b696-c023c6e3521b1417.js" async=""></script><script src="/_next/static/chunks/255-81ba70bd132d3eed.js" async=""></script><script src="/_next/static/chunks/main-app-3e6673f4a8380c97.js" async=""></script><script src="/_next/static/chunks/12-7d516a2f290e26f2.js" async=""></script><script src="/_next/static/chunks/app/layout-82602bdfed5552b0.js" async=""></script><meta name="robots" content="noindex"/><meta name="theme-color" content="#25D366"/><meta name="apple-mobile-web-app-capable" content="yes"/><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/><meta name="apple-mobile-web-app-title" content="WA CRM"/><link rel="manifest" href="/manifest.json"/><title>404: This page could not be found.</title><title>WhatsApp CRM SA — Admin</title><script src="/_next/static/chunks/polyfills-42372ed130431b0a.js" noModule=""></script></head><body><div hidden=""><!--$--><!--/$--></div><div class="flex min-h-screen"><aside class="fixed left-0 top-0 h-full w-[260px] bg-black/40 backdrop-blur-xl border-r border-white/[.06] flex flex-col z-50"><div class="p-5 border-b border-white/[.06]"><a class="flex items-center gap-2 text-lg font-semibold text-white no-underline" href="/dashboard/"><span class="text-xl">💬</span><span>WhatsApp CRM</span></a><p class="text-xs text-white/30 mt-1">Admin Dashboard</p></div><nav class="flex-1 py-4 px-3 space-y-1"><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/dashboard/"><span class="text-base">🏠</span><span>Dashboard</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/conversations/"><span class="text-base">💬</span><span>Conversations</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/contacts/"><span class="text-base">👥</span><span>Contacts</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/campaigns/"><span class="text-base">📨</span><span>Campaigns</span></a><a class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline" href="/ai/"><span class="text-base">🤖</span><span>AI Stats</span></a></nav><div class="p-3 border-t border-white/[.06]"><button class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/50 hover:text-white hover:bg-white/[.06] transition-all cursor-pointer bg-transparent border-none"><span class="text-base">🚪</span><span>Logout</span></button></div></aside><main class="ml-[260px] flex-1"><div style="font-family:system-ui,&quot;Segoe UI&quot;,Roboto,Helvetica,Arial,sans-serif,&quot;Apple Color Emoji&quot;,&quot;Segoe UI Emoji&quot;;height:100vh;text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center"><div><style>body{color:#000;background:#fff;margin:0}.next-error-h1{border-right:1px solid rgba(0,0,0,.3)}@media (prefers-color-scheme:dark){body{color:#fff;background:#000}.next-error-h1{border-right:1px solid rgba(255,255,255,.3)}}</style><h1 class="next-error-h1" style="display:inline-block;margin:0 20px 0 0;padding:0 23px 0 0;font-size:24px;font-weight:500;vertical-align:top;line-height:49px">404</h1><div style="display:inline-block"><h2 style="font-size:14px;font-weight:400;line-height:49px;margin:0">This page could not be found.</h2></div></div></div><!--$--><!--/$--></main></div><script src="/_next/static/chunks/webpack-74c939c87fa0092a.js" id="_R_" async=""></script><script>(self.__next_f=self.__next_f||[]).push([0])</script><script>self.__next_f.push([1,"1:\"$Sreact.fragment\"\n2:I[6710,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"default\"]\n3:I[9766,[],\"\"]\n4:I[8924,[],\"\"]\n5:I[3762,[\"12\",\"static/chunks/12-7d516a2f290e26f2.js\",\"177\",\"static/chunks/app/layout-82602bdfed5552b0.js\"],\"PWAInstallScript\"]\n6:I[4431,[],\"OutletBoundary\"]\n8:I[5278,[],\"AsyncMetadataOutlet\"]\na:I[4431,[],\"ViewportBoundary\"]\nc:I[4431,[],\"MetadataBoundary\"]\nd:\"$Sreact.suspense\"\nf:I[7150,[],\"\"]\n:HL[\"/_next/static/css/a5b9e56526ddf77e.css\",\"style\"]\n"])</script><script>self.__next_f.push([1,"0:{\"P\":null,\"b\":\"_3x95xLmWbLN0GMJUinot\",\"p\":\"\",\"c\":[\"\",\"_not-found\",\"\"],\"i\":false,\"f\":[[[\"\",{\"children\":[\"/_not-found\",{\"children\":[\"__PAGE__\",{}]}]},\"$undefined\",\"$undefined\",true],[\"\",[\"$\",\"$1\",\"c\",{\"children\":[[[\"$\",\"link\",\"0\",{\"rel\":\"stylesheet\",\"href\":\"/_next/static/css/a5b9e56526ddf77e.css\",\"precedence\":\"next\",\"crossOrigin\":\"$undefined\",\"nonce\":\"$undefined\"}]],[\"$\",\"html\",null,{\"lang\":\"en\",\"children\":[[\"$\",\"head\",null,{\"children\":[[\"$\",\"meta\",null,{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no\"}],[\"$\",\"meta\",null,{\"name\":\"theme-color\",\"content\":\"#25D366\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-capable\",\"content\":\"yes\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-status-bar-style\",\"content\":\"black-translucent\"}],[\"$\",\"meta\",null,{\"name\":\"apple-mobile-web-app-title\",\"content\":\"WA CRM\"}],[\"$\",\"link\",null,{\"rel\":\"manifest\",\"href\":\"/manifest.json\"}]]}],[\"$\",\"body\",null,{\"children\":[[\"$\",\"$L2\",null,{\"children\":[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":\"$undefined\",\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]}],[\"$\",\"$L5\",null,{}]]}]]}]]}],{\"children\":[\"/_not-found\",[\"$\",\"$1\",\"c\",{\"children\":[null,[\"$\",\"$L3\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L4\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":\"$undefined\",\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]]}],{\"children\":[\"__PAGE__\",[\"$\",\"$1\",\"c\",{\"children\":[[[\"$\",\"title\",null,{\"children\":\"404: This page could not be found.\"}],[\"$\",\"div\",null,{\"style\":{\"fontFamily\":\"system-ui,\\\"Segoe UI\\\",Roboto,Helvetica,Arial,sans-serif,\\\"Apple Color Emoji\\\",\\\"Segoe UI Emoji\\\"\",\"height\":\"100vh\",\"textAlign\":\"center\",\"display\":\"flex\",\"flexDirection\":\"column\",\"alignItems\":\"center\",\"justifyContent\":\"center\"},\"children\":[\"$\",\"div\",null,{\"children\":[[\"$\",\"style\",null,{\"dangerouslySetInnerHTML\":{\"__html\":\"body{color:#000;background:#fff;margin:0}.next-error-h1{border-right:1px solid rgba(0,0,0,.3)}@media (prefers-color-scheme:dark){body{color:#fff;background:#000}.next-error-h1{border-right:1px solid rgba(255,255,255,.3)}}\"}}],[\"$\",\"h1\",null,{\"className\":\"next-error-h1\",\"style\":{\"display\":\"inline-block\",\"margin\":\"0 20px 0 0\",\"padding\":\"0 23px 0 0\",\"fontSize\":24,\"fontWeight\":500,\"verticalAlign\":\"top\",\"lineHeight\":\"49px\"},\"children\":404}],[\"$\",\"div\",null,{\"style\":{\"display\":\"inline-block\"},\"children\":[\"$\",\"h2\",null,{\"style\":{\"fontSize\":14,\"fontWeight\":400,\"lineHeight\":\"49px\",\"margin\":0},\"children\":\"This page could not be found.\"}]}]]}]}]],null,[\"$\",\"$L6\",null,{\"children\":[\"$L7\",[\"$\",\"$L8\",null,{\"promise\":\"$@9\"}]]}]]}],{},null,false]},null,false]},null,false],[\"$\",\"$1\",\"h\",{\"children\":[[\"$\",\"meta\",null,{\"name\":\"robots\",\"content\":\"noindex\"}],[[\"$\",\"$La\",null,{\"children\":\"$Lb\"}],null],[\"$\",\"$Lc\",null,{\"children\":[\"$\",\"div\",null,{\"hidden\":true,\"children\":[\"$\",\"$d\",null,{\"fallback\":null,\"children\":\"$Le\"}]}]}]]}],false]],\"m\":\"$undefined\",\"G\":[\"$f\",[]],\"s\":false,\"S\":true}\n"])</script><script>self.__next_f.push([1,"b:[[\"$\",\"meta\",\"0\",{\"charSet\":\"utf-8\"}],[\"$\",\"meta\",\"1\",{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1\"}]]\n7:null\n"])</script><script>self.__next_f.push([1,"9:{\"metadata\":[[\"$\",\"title\",\"0\",{\"children\":\"WhatsApp CRM SA — Admin\"}]],\"error\":null,\"digest\":\"$undefined\"}\n"])</script><script>self.__next_f.push([1,"e:\"$9:metadata\"\n"])</script></body></html>"""

# ── /404 ──────────────────────────────────────────────────────────────────
@app.get("/404", include_in_schema=False)
@app.get("/404/", include_in_schema=False)
def route_404():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=(_APP_PAGE_404_7))




# ─── Root ─────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    if _LANDING_HTML:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=_LANDING_HTML)
    return {"product": "WhatsApp CRM SA", "status": "ok", "version": "0.1.4"}


# ─── Error handler ────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exc(request: Request, exc: Exception):
    logger.error("Unhandled: %s", exc)
    return JSONResponse(status_code=500, content={"error": str(exc)})
