"""
WhatsApp CRM SA — Configuration
=================================
All settings loaded from environment (.env file).
Supports three WhatsApp providers: openwa | meta | twilio.

OpenWA is the default and recommended provider for SA SMMEs.
"""

import os
from functools import lru_cache


class Settings:
    """Application settings loaded from environment."""

    # ── App ───────────────────────────────────────────────────
    APP_NAME: str                  = os.getenv("APP_NAME",                  "WhatsApp CRM SA")
    APP_URL: str                   = os.getenv("APP_URL",                   "http://localhost:8000")
    ENVIRONMENT: str               = os.getenv("ENVIRONMENT",               "development")
    DEBUG: bool                    = os.getenv("DEBUG",                      "true").lower() == "true"
    SECRET_KEY: str                = os.getenv("SECRET_KEY",                 os.urandom(32).hex())
    SA_TIMEZONE: str               = os.getenv("SA_TIMEZONE",                "Africa/Johannesburg")

    # ── Database (Supabase / PostgreSQL) ───────────────────────
    DATABASE_URL: str              = os.getenv("DATABASE_URL",               "sqlite:///./whatsapp_crm.db")

    # ── WhatsApp provider ──────────────────────────────────────
    # openwa | meta | twilio
    WHATSAPP_PROVIDER: str         = os.getenv("WHATSAPP_PROVIDER",          "openwa")

    # ── Meta WhatsApp Business API ─────────────────────────────
    META_PHONE_NUMBER_ID:          str = os.getenv("META_PHONE_NUMBER_ID",   "")
    META_ACCESS_TOKEN:             str = os.getenv("META_ACCESS_TOKEN",      "")
    META_BUSINESS_ACCOUNT_ID:      str = os.getenv("META_BUSINESS_ACCOUNT_ID","")

    # ── Twilio WhatsApp ────────────────────────────────────────
    TWILIO_ACCOUNT_SID:            str = os.getenv("TWILIO_ACCOUNT_SID",    "")
    TWILIO_AUTH_TOKEN:             str = os.getenv("TWILIO_AUTH_TOKEN",     "")
    TWILIO_WHATSAPP_FROM:          str = os.getenv("TWILIO_WHATSAPP_FROM",  "")

    # ── OpenWA (recommended default — open source, self-hosted) ─
    # Official repo: https://github.com/rmyndharis/OpenWA
    # Docker:           docker run -p 2785:2785 -p 2886:2886 --name openwa rmyndharis/openwa:0.1.4
    # Dashboard:        http://localhost:2886
    # Swagger:          http://localhost:2785/api/docs
    OPENWA_API_URL:            str = os.getenv("OPENWA_API_URL",       "http://localhost:2785")
    OPENWA_API_KEY:            str = os.getenv("OPENWA_API_KEY",       "")
    OPENWA_SESSION_ID:         str = os.getenv("OPENWA_SESSION_ID",    "default")
    OPENWA_HMAC_KEY:           str = os.getenv("OPENWA_HMAC_KEY",      "")
    OPENWA_TIMEOUT:          int  = int(os.getenv("OPENWA_TIMEOUT",   "30"))
    OPENWA_WEBHOOK_SECRET:    str = os.getenv("OPENWA_WEBHOOK_SECRET","")
    OPENWA_INSTANCE:          str = os.getenv("OPENWA_INSTANCE",      "default")

    # ── AI Backend ─────────────────────────────────────────────
    GROQ_API_KEY:                  str = os.getenv("GROQ_API_KEY",          "")
    OPENROUTER_API_KEY:            str = os.getenv("OPENROUTER_API_KEY",    "")
    AI_PROVIDER:                   str = os.getenv("AI_PROVIDER",           "auto")

    # ── Africa's Talking (SMS fallback) ────────────────────────
    AFRICASTALKING_API_KEY:        str = os.getenv("AFRICASTALKING_API_KEY",     "")
    AFRICASTALKING_USERNAME:       str = os.getenv("AFRICASTALKING_USERNAME",    "")
    SMS_SENDER_ID:                 str = os.getenv("SMS_SENDER_ID",              "")

    # ── Email ──────────────────────────────────────────────────
    SMTP_HOST:                     str = os.getenv("SMTP_HOST",               "smtp.gmail.com")
    SMTP_PORT:                  int = int(os.getenv("SMTP_PORT",           "587"))
    SMTP_USER:                     str = os.getenv("SMTP_USER",               "")
    SMTP_PASSWORD:                 str = os.getenv("SMTP_PASSWORD",           "")
    NOTIFICATION_EMAIL:            str = os.getenv("NOTIFICATION_EMAIL",      "")

    # ── Payments (PayFast — SA ZAR) ───────────────────────────
    PAYFAST_MERCHANT_ID:           str = os.getenv("PAYFAST_MERCHANT_ID",        "")
    PAYFAST_MERCHANT_KEY:          str = os.getenv("PAYFAST_MERCHANT_KEY",       "")
    PAYFAST_PASSPHRASE:            str = os.getenv("PAYFAST_PASSPHRASE",         "")

    # ── Media Storage ──────────────────────────────────────────
    SUPABASE_STORAGE_URL:          str = os.getenv("SUPABASE_STORAGE_URL",       "")
    SUPABASE_SERVICE_KEY:          str = os.getenv("SUPABASE_SERVICE_KEY",       "")

    # ── Rate limits & business rules ───────────────────────────
    MAX_CONVERSATIONS_PER_DAY:    int = int(os.getenv("MAX_CONVERSATIONS_PER_DAY",    "200"))
    MAX_MESSAGES_PER_CONVERSATION:int = int(os.getenv("MAX_MESSAGES_PER_CONVERSATION", "50"))
    AI_RATE_LIMIT_PER_MINUTE:     int = int(os.getenv("AI_RATE_LIMIT_PER_MINUTE",     "18"))
    BUSINESS_HOURS_START:         int = int(os.getenv("BUSINESS_HOURS_START",        "8"))
    BUSINESS_HOURS_END:           int = int(os.getenv("BUSINESS_HOURS_END",          "18"))
    AUTO_REPLY_ENABLED:           bool = os.getenv("AUTO_REPLY_ENABLED",          "true").lower() == "true"
    MESSAGE_DELAY_MIN:          float = float(os.getenv("MESSAGE_DELAY_MIN",        "1"))
    AUTO_REPLY_TYPING_DELAY:      int = int(os.getenv("AUTO_REPLY_TYPING_DELAY",    "2"))

    # ── Computed ───────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    # ── Validation ────────────────────────────────────────────
    def validate(self):
        errors = []

        if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be at least 32 characters")

        if not self.GROQ_API_KEY and not self.OPENROUTER_API_KEY:
            print("⚠️  No AI API key set. AI auto-reply will use templates only.")

        if self.WHATSAPP_PROVIDER == "openwa":
            if not self.OPENWA_API_KEY:
                errors.append(
                    "OPENWA_API_KEY is required when WHATSAPP_PROVIDER=openwa"
                )
            if not self.OPENWA_SESSION_ID:
                errors.append(
                    "OPENWA_SESSION_ID is required when WHATSAPP_PROVIDER=openwa "
                    "(set via the OpenWA dashboard → Sessions)"
                )

        elif self.WHATSAPP_PROVIDER == "meta":
            if not self.META_ACCESS_TOKEN:
                errors.append(
                    "META_ACCESS_TOKEN required when WHATSAPP_PROVIDER=meta"
                )

        elif self.WHATSAPP_PROVIDER == "twilio":
            if not self.TWILIO_ACCOUNT_SID:
                errors.append(
                    "TWILIO_ACCOUNT_SID required when WHATSAPP_PROVIDER=twilio"
                )

        if errors:
            raise ValueError("Config validation failed:\n  " + "\n  ".join(errors))


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton; validates on first load."""
    s = Settings()
    s.validate()
    return s


settings = get_settings()
