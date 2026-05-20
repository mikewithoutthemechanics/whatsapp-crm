"""
WhatsApp CRM SA — FastAPI Application Entry Point
==================================================
Main application initialization and configuration.

Run:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
)
from app.auth import auth_router, admin_router
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
    """Initialize Supabase/PostgreSQL database connection."""
    try:
        import supabase
        if "postgresql" in settings.DATABASE_URL or "supabase" in settings.DATABASE_URL:
            url_parts = settings.DATABASE_URL.split("/")
            project_ref = url_parts[-2] if len(url_parts) > 2 else ""
            client = supabase.create_client(
                f"https://{project_ref}.supabase.co",
                settings.SUPABASE_SERVICE_KEY or ""
            )
            logger.info("Connected to Supabase database")
            return client
    except ImportError:
        logger.warning("supabase package not installed. Run: pip install supabase")
    except Exception as e:
        logger.warning("Database connection failed: %s. Using SQLite fallback.", e)

    # SQLite fallback for local development
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import Base
    engine = create_engine("sqlite:///./whatsapp_crm.db", echo=settings.DEBUG)
    Base.metadata.create_all(engine)
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

# CORS for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# ─── Error handlers ──────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


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