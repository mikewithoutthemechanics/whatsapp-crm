#!/usr/bin/env python3
"""
WhatsApp CRM SA — Setup Wizard
================================
Interactive setup for non-technical users.
Run: python scripts/setup_wizard.py
"""

import questionary
from pathlib import Path
import os
import sys

def main():
    print("🚀 WhatsApp CRM SA Setup Wizard")
    print("=" * 40)
    
    # 1. AI Provider
    ai = questionary.select(
        "Choose AI provider (for auto-replies):",
        choices=[
            "Template only (no API key needed - basic responses)",
            "Groq (free, 14,400 req/day)",
            "OpenRouter (free, 20 RPM)",
            "Both - automatic failover"
        ]
    ).ask()
    
    ai_provider = "template"
    groq_key = ""
    or_key = ""
    
    if "Groq" in ai:
        groq_key = questionary.password(
            "Enter Groq API key (get from https://console.groq.com):"
        ).ask() or ""
        ai_provider = "groq"
    
    if "OpenRouter" in ai:
        or_key = questionary.password(
            "Enter OpenRouter API key (get from https://openrouter.ai):"
        ).ask() or ""
        ai_provider = "openrouter" if ai_provider == "template" else "auto"
    
    # 2. WhatsApp Provider
    wa = questionary.select(
        "Choose WhatsApp connection:",
        choices=[
            "OpenWA - Connect your personal phone (RECOMMENDED)",
            "Meta Business API - Requires Facebook approval",
            "Twilio WhatsApp"
        ]
    ).ask()
    
    wa_provider = "openwa"
    openwa_session = "wavi-main"
    
    if "OpenWA" in wa:
        openwa_session = questionary.text(
            "Session name:",
            default="wavi-main"
        ).ask() or "wavi-main"
        wa_provider = "openwa"
    elif "Meta" in wa:
        wa_provider = "meta"
    else:
        wa_provider = "twilio"
    
    # 3. Business Info
    business_name = questionary.text(
        "Business name:",
    ).ask() or "Your Business"
    
    business_type = questionary.select(
        "Business type:",
        choices=["Retail", "Services", "Healthcare", "Education", "Other"]
    ).ask() or "Services"
    
    # 4. Admin Password
    admin_pw = questionary.password(
        "Create admin password (for dashboard login):"
    ).ask() or "changeme"
    
    # 5. Create .env
    env_content = f"""# WhatsApp CRM SA - Auto-generated .env
# ================================

# Core
ENVIRONMENT=development
DEBUG=true
SECRET_KEY={''.join(os.urandom(32).hex())}
ADMIN_PASSWORD={admin_pw}

# AI
AI_PROVIDER={ai_provider}
GROQ_API_KEY={groq_key}
OPENROUTER_API_KEY={or_key}

# WhatsApp
WHATSAPP_PROVIDER={wa_provider}
OPENWA_SESSION_ID={openwa_session}
OPENWA_API_URL=http://localhost:2785
OPENWA_API_KEY=changeme

# Business
BUSINESS_NAME={business_name}
BUSINESS_TYPE={business_type}
BUSINESS_HOURS_START=8
BUSINESS_HOURS_END=18
"""
    
    env_path = Path(".env")
    env_path.write_text(env_content)
    
    print("\n✅ Configuration saved to .env")
    print("\nNext steps:")
    print("  1. Run: python scripts/start_all.py")
    print("  2. Scan QR code with WhatsApp")
    print("  3. Open http://localhost:8000 in your browser")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        sys.exit(0)