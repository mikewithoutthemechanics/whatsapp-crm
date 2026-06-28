"""
WhatsApp CRM SA — Environment Variables
=======================================
Copy to .env:  cp .env.example .env
Quick start:  see README.md
"""

import os
from functools import lru_cache

try:
    from opentelemetry import trace
    # Initialize tracer
    tracer = trace.get_tracer(__name__)
except ImportError:
    trace = None
    tracer = None


class Settings:
    # ─ App ───────────────────────────────────────────────────────
    APP_NAME:     str = os.getenv("APP_NAME",     "WhatsApp CRM SA")
    APP_URL:      str = os.getenv("APP_URL",      "http://localhost:8000")
    ENVIRONMENT:  str = os.getenv("ENVIRONMENT",  "development")   # development | staging | production
    DEBUG:       bool = os.getenv("DEBUG",       "true").lower()  == "true"
    SECRET_KEY:   str = os.getenv("SECRET_KEY",   os.urandom(32).hex())
    SA_TIMEZONE:  str = os.getenv("SA_TIMEZONE",  "Africa/Johannesburg")

    # ─ Admin auth ────────────────────────────────────────────────
    # Set ADMIN_PASSWORD in your environment or .env.
    # Login: POST /api/auth/login {"password":"<ADMIN_PASSWORD>"}
    # Returns a JWT valid for 24 h.  Pass it as Authorization: Bearer to every admin route.
    # Pick a strong, unique password and rotate SECRET_KEY too.

    # ─ Database ──────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./whatsapp_crm.db")

    # ─ WhatsApp provider ────────────────────────────────────────
    # openwa | meta | twilio
    WHATSAPP_PROVIDER: str = os.getenv("WHATSAPP_PROVIDER", "openwa")

    # ─ Meta ──────────────────────────────────────────────────────
    META_PHONE_NUMBER_ID:         str = os.getenv("META_PHONE_NUMBER_ID",   "")
    META_ACCESS_TOKEN:            str = os.getenv("META_ACCESS_TOKEN",      "")
    META_BUSINESS_ACCOUNT_ID:     str = os.getenv("META_BUSINESS_ACCOUNT_ID","")

    # ─ Twilio ────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID:           str = os.getenv("TWILIO_ACCOUNT_SID",    "")
    TWILIO_AUTH_TOKEN:            str = os.getenv("TWILIO_AUTH_TOKEN",    "")
    TWILIO_WHATSAPP_FROM:         str = os.getenv("TWILIO_WHATSAPP_FROM", "")

    # ─ OpenWA (rmyndharis/OpenWA v0.1.4) ───────────────────────
    # https://github.com/rmyndharis/OpenWA
    OPENWA_API_URL:      str = os.getenv("OPENWA_API_URL",      "http://localhost:2785")
    OPENWA_API_KEY:      str = os.getenv("OPENWA_API_KEY",      "")
    OPENWA_SESSION_ID:   str = os.getenv("OPENWA_SESSION_ID",   "default")
    OPENWA_HMAC_KEY:     str = os.getenv("OPENWA_HMAC_KEY",     "")
    OPENWA_TIMEOUT:     int  = int(os.getenv("OPENWA_TIMEOUT",  "30"))
    OPENWA_WEBHOOK_SECRET: str = os.getenv("OPENWA_WEBHOOK_SECRET","")
    OPENWA_INSTANCE:     str = os.getenv("OPENWA_INSTANCE",     "default")

    # ─ AI ───────────────────────────────────────────────────────
    GROQ_API_KEY:          str = os.getenv("GROQ_API_KEY",          "")
    OPENROUTER_API_KEY:    str = os.getenv("OPENROUTER_API_KEY",    "")
    AI_PROVIDER:           str = os.getenv("AI_PROVIDER",           "auto")

    # ─ Africa's Talking ──────────────────────────────────────────
    AFRICASTALKING_API_KEY:    str = os.getenv("AFRICASTALKING_API_KEY",   "")
    AFRICASTALKING_USERNAME:   str = os.getenv("AFRICASTALKING_USERNAME",  "")
    SMS_SENDER_ID:             str = os.getenv("SMS_SENDER_ID",            "")

    # ─ Email ─────────────────────────────────────────────────────
    SMTP_HOST:               str = os.getenv("SMTP_HOST",               "smtp.gmail.com")
    SMTP_PORT:              int = int(os.getenv("SMTP_PORT",            "587"))
    SMTP_USER:               str = os.getenv("SMTP_USER",               "")
    SMTP_PASSWORD:           str = os.getenv("SMTP_PASSWORD",           "")
    NOTIFICATION_EMAIL:      str = os.getenv("NOTIFICATION_EMAIL",      "")

    # ─ Payments (PayFast) ───────────────────────────────────────
    PAYFAST_MERCHANT_ID:     str = os.getenv("PAYFAST_MERCHANT_ID",    "")
    PAYFAST_MERCHANT_KEY:    str = os.getenv("PAYFAST_MERCHANT_KEY",   "")
    PAYFAST_PASSPHRASE:      str = os.getenv("PAYFAST_PASSPHRASE",     "")

    # ─ Storage ───────────────────────────────────────────────────
    SUPABASE_URL:            str = os.getenv("SUPABASE_URL",           "")
    SUPABASE_ANON_KEY:       str = os.getenv("SUPABASE_ANON_KEY",      "")
    SUPABASE_STORAGE_URL:    str = os.getenv("SUPABASE_STORAGE_URL",   "")
    SUPABASE_SERVICE_KEY:    str = os.getenv("SUPABASE_SERVICE_KEY",   "")

    # ─ Rate limits ───────────────────────────────────────────────
    # PRODUCTION RATE LIMITS
    MAX_CONVERSATIONS_PER_DAY:    int = int(os.getenv("MAX_CONVERSATIONS_PER_DAY",    "200"))
    MAX_MESSAGES_PER_CONVERSATION: int = int(os.getenv("MAX_MESSAGES_PER_CONVERSATION", "50"))
    AI_RATE_LIMIT_PER_MINUTE:     int = int(os.getenv("AI_RATE_LIMIT_PER_MINUTE",     "18"))
    BUSINESS_HOURS_START:         int = int(os.getenv("BUSINESS_HOURS_START",        "8"))
    BUSINESS_HOURS_END:           int = int(os.getenv("BUSINESS_HOURS_END",          "18"))
    AUTO_REPLY_ENABLED:           bool = os.getenv("AUTO_REPLY_ENABLED",    "true").lower() == "true"
    MESSAGE_DELAY_MIN:          float = float(os.getenv("MESSAGE_DELAY_MIN","1"))
    AUTO_REPLY_TYPING_DELAY:      int = int(os.getenv("AUTO_REPLY_TYPING_DELAY","2"))

    # ─ Computed ──────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    # ─ Validation ───────────────────────────────────────────────
    def validate(self):
        warnings = []
        errors   = []

        if len(self.SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be at least 32 characters")

        if not self.GROQ_API_KEY and not self.OPENROUTER_API_KEY:
            warnings.append("No AI API key set — AI auto-reply will use templates only")

        # Only validate WhatsApp provider in production or when explicitly configured
        if self.ENVIRONMENT == "production" or self.WHATSAPP_PROVIDER != "openwa":
            if self.WHATSAPP_PROVIDER == "openwa":
                for var, desc in [
                    ("OPENWA_API_KEY",     "OpenWA API key from dashboard → Settings → API Access"),
                    ("OPENWA_SESSION_ID",  "OpenWA session name (created in your dashboard)"),
                ]:
                    if not getattr(self, var):
                        errors.append(f"{var} is required when WHATSAPP_PROVIDER=openwa  ({desc})")

            elif self.WHATSAPP_PROVIDER == "meta":
                if not self.META_ACCESS_TOKEN:
                    errors.append("META_ACCESS_TOKEN required when WHATSAPP_PROVIDER=meta")
                if not self.META_PHONE_NUMBER_ID:
                    errors.append("META_PHONE_NUMBER_ID required when WHATSAPP_PROVIDER=meta")

            elif self.WHATSAPP_PROVIDER == "twilio":
                if not self.TWILIO_ACCOUNT_SID:
                    errors.append("TWILIO_ACCOUNT_SID required when WHATSAPP_PROVIDER=twilio")
                if not self.TWILIO_WHATSAPP_FROM:
                    errors.append("TWILIO_WHATSAPP_FROM required when WHATSAPP_PROVIDER=twilio")
        else:
            warnings.append("WhatsApp provider not fully configured — using development mode")

        for w in warnings:
            print(f"WARNING: {w}")

        if errors:
            raise ValueError("Config validation failed:\n  " + "\n  ".join(errors))


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validate()
    return s


settings = get_settings()
