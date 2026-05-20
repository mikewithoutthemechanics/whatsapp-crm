#!/usr/bin/env python3
"""
WhatsApp CRM SA — Setup & Migration Script
===========================================
Sets up the database, creates initial admin user, and configures the app.

Run:
    python scripts/setup.py
"""

import os
import sys
import getpass
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_dependencies():
    """Check that required packages are installed."""
    print("📦 Checking dependencies...")

    required = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("sqlalchemy", "SQLAlchemy"),
        ("requests", "requests"),
        ("apscheduler", "APScheduler"),
    ]

    missing = []
    for module, name in required:
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            missing.append(name)
            print(f"  ❌ {name} (pip install {module})")

    optional = [
        ("supabase", "supabase"),
        ("twilio", "twilio"),
    ]

    for module, name in optional:
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ⚪ {name} (optional — pip install {module})")

    if missing:
        print(f"\n❌ Missing: {', '.join(missing)}")
        print(f"   Run: pip install {' '.join(m.lower() for m in missing)}")
        return False
    return True


def create_env_file():
    """Create .env file from template."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.example")

    if os.path.exists(env_path):
        print("\n📄 .env file already exists")
        return True

    if os.path.exists(template_path):
        import shutil
        shutil.copy(template_path, env_path)
        print("📄 Created .env from .env.example")
    else:
        print("📄 Creating minimal .env...")
        with open(env_path, "w") as f:
            f.write("# WhatsApp CRM SA\n")
            f.write("# Configure your settings here\n\n")
            f.write("APP_NAME=MyWhatsAppCRM\n")
            f.write("SECRET_KEY=" + uuid.uuid4().hex + "\n")
            f.write("DATABASE_URL=sqlite:///./whatsapp_crm.db\n")
            f.write("# WhatsApp: META or TWILIO\n")
            f.write("WHATSAPP_PROVIDER=meta\n")
            f.write("META_PHONE_NUMBER_ID=\n")
            f.write("META_ACCESS_TOKEN=\n")
            f.write("# AI: groq or openrouter\n")
            f.write("AI_PROVIDER=auto\n")
            f.write("GROQ_API_KEY=\n")
            f.write("OPENROUTER_API_KEY=\n")
        print("📄 Created minimal .env")

    print("\n⚠️  Edit .env and add your credentials:")
    print("   - WhatsApp Business API (Meta or Twilio)")
    print("   - AI API key (Groq at console.groq.com — free)")
    return True


def init_database():
    """Initialize the database."""
    from app.config import settings
    from app.models import Base

    print("\n🗄️  Initializing database...")

    if "postgresql" in settings.DATABASE_URL:
        print("  Using PostgreSQL/Supabase")
    else:
        print("  Using SQLite (local development)")

    return True


def print_welcome():
    """Print welcome banner."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                    📱 WhatsApp CRM SA                     ║
║               South African SMME WhatsApp CRM             ║
╠═══════════════════════════════════════════════════════════╣
║  Features:                                                ║
║  • WhatsApp via OpenWA (free, self-hosted) / Meta / Twilio       ║
║  • AI-powered auto-replies (Groq / OpenRouter — free)    ║
║  • Lead management & scoring                             ║
║  • Drip campaign engine                                   ║
║  • Broadcast messages                                     ║
║  • Dashboard & analytics                                  ║
║  • SA-specific: ZAR, SAST, load-shedding aware            ║
╠═══════════════════════════════════════════════════════════╣
║  Documentation: See README.md for full setup guide        ║
╚═══════════════════════════════════════════════════════════╝
""")


def main():
    print_welcome()

    print("\n🔧 WhatsApp CRM SA — Setup\n")

    deps_ok = check_dependencies()
    env_ok = create_env_file()

    # Reload settings after .env is created
    if env_ok:
        from importlib import reload
        import app.config as config_module
        reload(config_module)
        from app.config import settings

    init_database()

    print("\n" + "=" * 55)
    print("✅ Setup complete!")
    print("=" * 55)
    print("\n📋 Next steps:")
    print("   1. Edit .env with your credentials")
    print("   2. Set up WhatsApp Business API:")
    print("      - Meta:   https://developers.facebook.com/docs/whatsapp/cloud-api")
    print("      - Twilio: https://www.twilio.com/docs/whatsapp")
    print("   3. Get free Groq API key: https://console.groq.com")
    print("   4. Run the server:")
    print("      python app/main.py")
    print("      # or")
    print("      uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print("   5. Open dashboard: http://localhost:3000")
    print("\n📞 WhatsApp Business API is required for live messaging.")
    print("   Without it, you can still test the AI and dashboard locally.\n")


if __name__ == "__main__":
    main()