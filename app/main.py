"""
WhatsApp CRM SA — FastAPI Application Entry Point
==================================================
Main application initialization and configuration.

Run:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os
import time
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    HAS_RATE_LIMIT = True
except ImportError:
    HAS_RATE_LIMIT = False
    Limiter = None
    RateLimitExceeded = Exception

from app.config import settings
from app.services.ai_service import ai_engine
from app.services.whatsapp_service import WhatsAppService
from app.services.campaign_service import DripCampaignEngine
from app.api.router import (
    contacts_router,
    conversations_router,
    messages_router,
    campaigns_router,
    ai_router,
    dashboard_router,
    webhook_router,
    leads_router,
)
from app.auth import auth_router, admin_router
# admin_router includes:
#   GET  /api/admin/health/detailed    — full production health report
#   GET  /api/admin/webhooks/openwa/health  — OpenWA health probe
#   GET  /api/admin/webhooks/openwa/resources/docs
#   GET  /api/admin/sessions
#   POST /api/auth/login               — JWT for admin routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Database connection ─────────────────────────────────────
def init_database():
    """Initialize database using SQLAlchemy session layer."""
    from app.database import engine, init_db
    init_db()
    return engine


# ─── Background tasks ────────────────────────────────────────
db = init_database()
campaign_engine = DripCampaignEngine()
campaign_engine.db = db


async def process_due_campaign_messages():
    """Process scheduled campaign messages."""
    try:
        result = campaign_engine.process_due_messages()
        logger.info("Campaign messages processed: %s", result)
    except Exception as e:
        logger.error("Campaign processing error: %s", e)


async def reset_ai_metrics():
    """Reset AI rate limit tracking."""
    ai_engine.request_counts = {"groq": 0, "openrouter": 0}


async def daily_status_report():
    """Log daily status summary."""
    logger.info("Daily status: AI requests - Groq: %d, OR: %d",
                ai_engine.request_counts["groq"],
                ai_engine.request_counts["openrouter"])


@asynccontextmanager
async def lifespan(app):
    """Manage app startup and shutdown."""
    # Startup
    logger.info("WhatsApp CRM SA starting...")
    logger.info("Environment: %s", settings.ENVIRONMENT)
    logger.info("WhatsApp provider: %s", settings.WHATSAPP_PROVIDER)
    logger.info("AI provider: %s", settings.AI_PROVIDER)

    # Start background scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler(timezone="Africa/Johannesburg")
        scheduler.add_job(process_due_campaign_messages, "interval", minutes=5, id="campaigns")
        scheduler.add_job(reset_ai_metrics, "interval", minutes=1, id="ai_reset")
        scheduler.add_job(daily_status_report, "cron", hour=18, minute=0, timezone="Africa/Johannesburg", id="report")
        scheduler.start()
    except Exception as e:
        logger.warning("Background scheduler failed: %s", e)

    yield

    # Shutdown
    logger.info("WhatsApp CRM SA shutting down...")


# ─── App Setup ───────────────────────────────────────────────
app = FastAPI(
    title="WhatsApp CRM SA",
    description="WhatsApp CRM for South African SMMEs",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Rate limiting ───────────────────────────────────────────────
if HAS_RATE_LIMIT:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "detail": str(exc.detail)},
        )

# ─── CORS (configurable origins) ────────────────────────────────────────
# Restrict in production - set ALLOWED_ORIGINS in .env
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
if settings.is_production and os.getenv("ALLOWED_ORIGINS"):
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if settings.is_production else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ─── Response Caching ───────────────────────────────────────────────
# Cache frequently accessed endpoints in app state (simple memory cache)
app.state.cache = {}

def get_cached(key: str, ttl: int = 300):
    """Get cached value if not expired."""
    if key in app.state.cache:
        value, ts = app.state.cache[key]
        if time.time() - ts < ttl:
            return value
    return None

def set_cached(key: str, value: dict):
    """Set cached value."""
    app.state.cache[key] = (value, time.time())


# ─── Setup Endpoint (one-click onboarding) ───────────────────────────
@app.get("/setup")
async def setup_page():
    """Serve the setup wizard page for non-technical users."""
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>WhatsApp CRM SA - Setup</title></head>
    <body style="font-family: sans-serif; max-width: 600px; margin: 40px auto;">
        <h1>🚀 WhatsApp CRM SA - Setup</h1>
        <p>Run this command to start setup:</p>
        <pre>python scripts/setup_wizard.py</pre>
        <p>Or manually configure:</p>
        <ol>
            <li>Edit .env with your business details</li>
            <li>Run: <code>python scripts/start_all.py</code></li>
            <li>Scan QR code with WhatsApp mobile app</li>
        </ol>
        <p><a href="/health">Check System Status</a></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# ─── Health check ────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "whatsapp_provider": settings.WHATSAPP_PROVIDER,
        "ai_provider": settings.AI_PROVIDER,
        "ai_active": bool(settings.GROQ_API_KEY or settings.OPENROUTER_API_KEY),
        "timestamp": time.time(),
    }


# ─── Google OAuth (Supabase) ─────────────────────────────────
@app.get("/auth/google")
def auth_google(request: Request):
    """Redirect to Supabase Google OAuth."""
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_anon = os.getenv("SUPABASE_ANON_KEY", "")
    if not supabase_url or not supabase_anon:
        raise HTTPException(500, "Supabase not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.")

    redirect_to = request.query_params.get("redirect_to", "")
    if not redirect_to:
        redirect_to = os.getenv("APP_URL", "http://localhost:8000") + "/auth/callback"

    authorize_url = (
        f"{supabase_url}/auth/v1/authorize"
        f"?provider=google"
        f"&redirect_to={redirect_to}"
    )
    return RedirectResponse(url=authorize_url)


@app.get("/auth/callback")
def auth_callback(request: Request):
    """Supabase OAuth callback - exchanges code for session, then redirects."""
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(400, "Missing authorization code")

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_anon = os.getenv("SUPABASE_ANON_KEY", "")
    if not supabase_url or not supabase_anon:
        raise HTTPException(500, "Supabase not configured")

    try:
        token_resp = httpx.post(
            f"{supabase_url}/auth/v1/token?grant_type=pkce",
            json={"code": code},
            headers={"apikey": supabase_anon, "Content-Type": "application/json"},
            timeout=15.0,
        )
        if token_resp.status_code != 200:
            raise HTTPException(400, "Failed to exchange code")

        token_data = token_resp.json()
        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")

        resp = RedirectResponse(url="/dashboard")
        resp.set_cookie("wavi_auth_token", access_token, httponly=True, secure=settings.is_production, samesite="lax", max_age=86400)
        resp.set_cookie("wavi_refresh_token", refresh_token, httponly=True, secure=settings.is_production, samesite="lax", max_age=86400 * 30)
        return resp
    except Exception as e:
        raise HTTPException(500, f"OAuth error: {str(e)}")


@app.get("/auth/session")
def auth_session(request: Request):
    """Return current auth session from cookies."""
    token = request.cookies.get("wavi_auth_token")
    if not token:
        return {"authenticated": False}
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_anon = os.getenv("SUPABASE_ANON_KEY", "")
    if not supabase_url or not supabase_anon:
        return {"authenticated": False}
    try:
        user_resp = httpx.get(
            f"{supabase_url}/auth/v1/user",
            headers={"apikey": supabase_anon, "Authorization": f"Bearer {token}"},
            timeout=15.0,
        )
        if user_resp.status_code == 200:
            return {"authenticated": True, "user": user_resp.json()}
    except Exception:
        pass
    return {"authenticated": False}


@app.post("/auth/logout")
def auth_logout():
    """Logout - clear auth cookies."""
    resp = JSONResponse({"logged_out": True})
    resp.delete_cookie("wavi_auth_token")
    resp.delete_cookie("wavi_refresh_token")
    return resp


# ─── Include routers ─────────────────────────────────────────
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(contacts_router)
app.include_router(conversations_router)
app.include_router(messages_router)
app.include_router(campaigns_router)
app.include_router(ai_router)
app.include_router(dashboard_router)
app.include_router(webhook_router)
app.include_router(leads_router)


# ─── Run directly ────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )