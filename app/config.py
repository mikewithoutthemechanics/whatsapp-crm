"""
WhatsApp CRM SA — Configuration
=================================
All settings loaded from environment (.env file).
"""

import os
from functools import lru_cache


class Settings:
    """Application settings loaded from environment."""

    # App
    APP_NAME: str = os.getenv("APP_NAME", "WhatsApp CRM SA")
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", os.urandom(32).hex())
    SA_TIMEZONE: str = os.getenv("SA_TIMEZONE", "Africa/Johannesburg")

    # Database (Supabase PostgreSQL)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./whatsapp_crm.db")

    # WhatsApp
    WHATSAPP_PROVIDER: str = os.getenv("WHATSAPP_PROVIDER", "meta")

    # Meta WhatsApp Business API
    META_PHONE_NUMBER_ID: str = os.getenv("META_PHONE_NUMBER_ID", "")
    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")
    META_BUSINESS_ACCOUNT_ID: str = os.getenv("META_BUSINESS_ACCOUNT_ID", "")

    # Twilio WhatsApp
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "")

    # AI Backend
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "auto")

    # Africa's Talking (SMS fallback)
    AFRICASTALKING_API_KEY: str = os.getenv("AFRICASTALKING_API_KEY", "")
    AFRICASTALKING_USERNAME: str = os.getenv("AFRICASTALKING_USERNAME", "")
    SMS_SENDER_ID: str = os.getenv("SMS_SENDER_ID", "")

    # Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    NOTIFICATION_EMAIL: str = os.getenv("NOTIFICATION_EMAIL", "")

    # Payments (PayFast)
    PAYFAST_MERCHANT_ID: str = os.getenv("PAYFAST_MERCHANT_ID", "")
    PAYFAST_MERCHANT_KEY: str = os.getenv("PAYFAST_MERCHANT_KEY", "")
    PAYFAST_PASSPHRASE: str = os.getenv("PAYFAST_PASSPHRASE", "")

    # Media Storage
    SUPABASE_STORAGE_URL: str = os.getenv("SUPABASE_STORAGE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # Rate Limits & Business Rules
    MAX_CONVERSATIONS_PER_DAY: int = int(os.getenv("MAX_CONVERSATIONS_PER_DAY", "200"))
    MAX_MESSAGES_PER_CONVERSATION: int = int(os.getenv("MAX_MESSAGES_PER_CONVERSATION", "50"))
    AI_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "18"))
    BUSINESS_HOURS_START: int = int(os.getenv("BUSINESS_HOURS_START", "8"))
    BUSINESS_HOURS_END: int = int(os.getenv("BUSINESS_HOURS_END", "18"))
    AUTO_REPLY_ENABLED: bool = os.getenv("AUTO_REPLY_ENABLED", "true").lower() == "true"
    MESSAGE_DELAY_MIN: float = float(os.getenv("MESSAGE_DELAY_MIN", "1"))
    AUTO_REPLY_TYPING_DELAY: int = int(os.getenv("AUTO_REPLY_TYPING_DELAY", "2"))

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    def validate(self):
        """Validate critical settings on startup."""
        errors = []
        if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be at least 32 chars")
        if not self.GROQ_API_KEY and not self.OPENROUTER_API_KEY:
            print("⚠️  Warning: No AI API key set. AI auto-reply will be limited to templates.")
        if self.WHATSAPP_PROVIDER == "meta" and not self.META_ACCESS_TOKEN:
            errors.append("META_ACCESS_TOKEN required when WHATSAPP_PROVIDER=meta")
        if self.WHATSAPP_PROVIDER == "twilio" and not self.TWILIO_ACCOUNT_SID:
            errors.append("TWILIO_ACCOUNT_SID required when WHATSAPP_PROVIDER=twilio")
        if errors:
            raise ValueError("Config errors:\n  " + "\n  ".join(errors))


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    settings = Settings()
    settings.validate()
    return settings


settings = get_settings()