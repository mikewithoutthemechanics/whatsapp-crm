"""
WhatsApp CRM SA — Auth & Admin
================================
JWT-based admin authentication + admin route registrar.
Minimal: HMAC-signed JWT with shared secret from env.rotate.
"""

import os, time, hmac, hashlib, jwt, logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from fastapi import APIRouter, HTTPException, Depends, Header, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ── JWT ──────────────────────────────────────────────────────────────

def _sign(payload: dict, secret: str, expires_hours: int = 24) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    claims = {**payload, "exp": exp}
    return jwt.encode(claims, secret, algorithm="HS256")


def _verify(token: str, secret: str) -> dict:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def _create_token(*, user_id: str, role: str = "admin",
                  secret: Optional[str] = None) -> str:
    secret = secret or os.getenv("SECRET_KEY", "")
    return _sign({"sub": user_id, "role": role}, secret)


# ── Router ───────────────────────────────────────────────────────────

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.post("/login")
def login(body: dict):
    """
    Login with admin password.
    Body: { "password": "..." }

    Returns a JWT valid for 24 hours.
    Set ADMIN_PASSWORD in your .env.
    """
    from app.config import settings
    admin_pw = os.getenv("ADMIN_PASSWORD", "")
    if not admin_pw:
        raise HTTPException(500, "ADMIN_PASSWORD not configured in .env")

    pw = body.get("password", "")
    if not hmac.compare_digest(pw, admin_pw):
        raise HTTPException(401, "Invalid password")

    token = _create_token(user_id="admin", role="admin")
    return {
        "access_token":  token,
        "token_type":    "Bearer",
        "expires_in":    86400,
        "user":          {"id": "admin", "role": "admin"},
    }


async def require_auth(
    authorization: Optional[str] = Header(None),
) -> dict:
    """Dependency — strips a valid JWT from the `Authorization: Bearer` header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1]
    secret = os.getenv("SECRET_KEY", "")
    return _verify(token, secret)


# ── Admin routes (require_auth applied on the router) ────────────────

admin_router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_auth)],
)


@admin_router.get("/health/detailed")
def detailed_health():
    """
    Full production health report.
    Checks: OpenWA gateway, database, AI providers.
    Uses lazy imports to avoid circular dependency with app.main.
    """
    result = {
        "status":    "healthy",
        "timestamp": time.time(),
        "checks":    {},
        "ai":        {},
        "whatsapp":  {},
    }

    # ── Settings (lazy) ─────────────────────────────────────────
    try:
        from app.config import settings
        result["environment"] = settings.ENVIRONMENT
    except Exception as exc:
        result["checks"]["config"] = {"status": "error", "detail": str(exc)}
        result["status"] = "degraded"
        return result

    # ── DB (lazy) ───────────────────────────────────────────────
    try:
        from app.main import db                # global engine/client
        import sqlalchemy as sa
        if hasattr(db, "connect"):
            with db.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
        else:
            # Supabase client path — just verify client is set
            _ = db
        result["checks"]["database"] = {"status": "ok"}
    except Exception as exc:
        result["checks"]["database"] = {"status": "error", "detail": str(exc)}
        result["status"] = "degraded"

    # ── AI ──────────────────────────────────────────────────────
    ai = {}
    if settings.GROQ_API_KEY:
        ai["groq"]       = {"configured": True}
    if settings.OPENROUTER_API_KEY:
        ai["openrouter"] = {"configured": True}
    ai["provider"] = settings.AI_PROVIDER
    ai["active"]   = bool(settings.GROQ_API_KEY or settings.OPENROUTER_API_KEY)
    result["checks"]["ai"] = ai

    # ── WhatsApp / OpenWA ───────────────────────────────────────
    ws_info = {"provider": settings.WHATSAPP_PROVIDER}
    if settings.WHATSAPP_PROVIDER == "openwa":
        try:
            from app.services.whatsapp_service import WhatsAppService
            gw = WhatsAppService().health()
            ws_info.update(gw)
            if not gw.get("healthy"):
                result["status"] = "degraded"
        except Exception as exc:
            ws_info["error"] = str(exc)
            result["status"] = "degraded"
    result["checks"]["whatsapp"] = ws_info

    return result


@admin_router.get("/webhooks/openwa/health")
def openwa_webhook_health():
    """
    Alias consumed by OpenWA's health check probe.
    OpenWA can be configured to call this endpoint to verify CRM liveness.

    GET /api/admin/webhooks/openwa/health
    → {"status":"healthy","openwa":true,"timestamp":1234567890}
    """
    return {
        "status":   "healthy",
        "openwa":   True,
        "timestamp": time.time(),
    }


@admin_router.get("/webhooks/openwa/resources/docs")
def openwa_docs_alias():
    """Alias for openwa's agent reference docs."""
    return {
        "docs_url": "https://github.com/rmyndharis/OpenWA",
        "api_docs": "/docs",
        "version":  "whatsapp-crm/0.1.4",
    }


@admin_router.get("/summary")
async def admin_summary():
    """Consolidated admin readout shared by OpenWA and the CRM."""
    from app.api.router import dashboard_router
    return JSONResponse(content=await dashboard_summary())


@admin_router.get("/sessions")
async def list_sessions():
    """
    Return the configured WhatsApp session info.
    Extend to call OpenWA /api/sessions endpoint when available.
    """
    return {
        "provider":  settings.WHATSAPP_PROVIDER,
        "session_id": settings.OPENWA_SESSION_ID or "default",
        "status":    "connected" if settings.WHATSAPP_PROVIDER == "openwa" else "configured",
    }


# ── Public import ────────────────────────────────────────────────────

__all__ = ["auth_router", "admin_router", "require_auth", "_create_token"]
