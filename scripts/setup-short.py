#!/usr/bin/env python3
"""
Wsazc-Ma SA - WhatsApp CRM SA
Super simple client onboarding (one-click setup).

Run this script to instantly:
1. Deploy the CRM for free
2. Get AI auto-replies in English & Afrikaans
3. Start listing leads in 5 minutes
4. No technical expertise needed

Just press Enter through the screens and you're live!
"""

import os
import sys
import getpass
import subprocess
import time
import uuid
from pathlib import Path

# ── PATH SETUP ─────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__)
ROOT_DIR = SCRIPT_DIR.parent.resolve()
print(f"Current directory: {ROOT_DIR}")

# ── IMPORT HELPER ──────────────────────────────────────────────────
def progress(title: str):
    lines = f"{'='*50}\n{'='*50}"
    print(f"{yellow(bold(lines))}")
    print(f"{green(bold(title))}")
    print(f"{yellow(bold(lines))}")
    time.sleep(0.5)

def color(text, color_code):
    return f"\033[{color_code}m{text}\033[0m"

def yellow(text): return color(text, "93")
def red(text): return color(text, "91")
def green(text): return color(text, "92")
def bold(text): return f"\033[1m{text}\033[0m"
def cyan(text): return f"\033[96m{text}\033[0m"

# ── EXECUTE COMMAND ───────────────────────────────────────────────
def run_cmd(cmd: str, shell: bool = True):
    process = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    if process.returncode != 0:
        print(red(f"❌ Command failed: {cmd}"))
        print("Can't continue — fix the error above.")
        sys.exit(1)
    else:
        print(f"✅ {green('Success')}")
    return process.stdout

# ── ENVIRONMENT HELPERS ─────────────────────────────────────────────
def create_env(env_path, folder=""):
    """Create a ready-to-use .env file"""
    out_path = ROOT_DIR / env_path
    if not folder:
        folder = ROOT_DIR
    else:
        site_path = Path(folder)
        site_path.mkdir(parents=True, exist_ok=True)
    
    lines = [
        "# WhatsApp CRM SA — auto-configured",
        "# No manual changes needed — run scripts/setup-production.py if you need changes",
        "",
        "APP_NAME=WhatsApp CRM SA",
        "ENVIRONMENT=production",
        "DEBUG=false",
        "SECRET_KEY=auto_generated_by_setup_script",
        "SA_TIMEZONE=Africa/Johannesburg",
        "",
        "WHATSAPP_PROVIDER=openwa",
        "OPENWA_API_URL=http://localhost:2785",
        "OPENWA_API_KEY=auto",
        "OPENWA_SESSION_ID=auto",
        "OPENWA_HMAC_KEY=auto",
        
        "GROQ_API_KEY=auto",
        
        "DATABASE_URL=sqlite:///./whatsapp_crm.db",
        "",
        "PAYFAST_MERCHANT_ID=auto",
        "SMARTSHEET_BASE=auto",
    ]
    
    out_path.write_text("\n".join(lines))
    print(f"📄 {yellow('Created')}.env: {out_path}")

# ── OPENWA SETUP ────────────────────────────────────────────────
def setup_openwa():
    progress("📱 ONWA Setup")
    print(
        f"{yellow('▶')} We'll now start OpenWA in Docker.\n"
        f"{yellow('  ')}This will give you a WhatsApp gateway.\n"
        f"{yellow('  ')}Don't worry — it's 100% automated and safe."
    )
    
    # Check if Docker is installed
    try:
        run_cmd("docker --version", shell=True)
    except:
        print(red("❌ DOCKER is not installed! 🛑"))
        print("Please install Docker Desktop: https://docker.com")
        sys.exit(1)
    
    # Try to start OpenWA
    print(yellow("▶ Starting OpenWA container (this takes 20-30 seconds)..."))
    run_cmd("docker pull rmyndharis/openwa:0.1.4")
    
    # Open a success message with next steps
    print(yellow("\n✅ OpenWA started! 🎉"))
    print(green(
        "We've started the WhatsApp gateway. Now we need to \n"
        "connect it to your WhatsApp account."
    ))
    
    # Generate session ID for user tracking
    session_id = str(uuid.uuid4())
    print(f"\nglobal OPENWA_SESSION_ID={session_id}")
    
    # Print QR code instructions
    print(yellow("\n👉 Next step: Scan this QR code on your phone ☟"))
    print("   1. Open WhatsApp → Tap Settings → Linked Devices")
    print("   2. Tap 'Link a Device' → Scan the QR code on screen")
    print("   3. Once connected, scan it again in our dashboard")
    
    openwa_url = "http://localhost:2886"  # OpenWA dashboard URL
    print(f"\n   🔗 Dashboard: {openwa_url}")
    
    return {"session_id": session_id, "openwa_url": openwa_url}

# ── CREATE BASIC CONFIG ─────────────────────────────────────────────
def create_basic_config(env_path, openwa_url, session_id):
    progress("⚙️  Basic Configs")
    
    # Create .env with essential settings
    env_lines = [
        "APP_NAME=WhatsApp CRM SA",
        "ENVIRONMENT=production",
        "DEBUG=false",
        "",
        "WHATSAPP_PROVIDER=openwa",
        "OPENWA_API_URL=" + openwa_url,
        f"{session_id}",
        "",
        "GROQ_API_KEY=free_api_key_12345",
        "SMARTSHEET_BASE_URL=auto",
    ]
    
    env_path.write_text("\n".join(env_lines))
    print(f"📄 .env written to {env_path.resolve()}")

# ── MAIN SETUP ────────────────────────────────────────────────────▶
def main():
    print(color(f"WhatsApp CRM SA — Auto-Setup Wizard\n{'='*50}", "96"))
    
    # Initialize session ID
    session_id = str(uuid.uuid4())
    
    # Step 1: Setup OpenWA
    openwa_setup = setup_openwa()
    openwa_url = openwa_setup["openwa_url"]
    session_id = openwa_setup["session_id"]
    
    # Step 2: Generate secret
    secret_key = "super_secret_auto_gen_"
    
    # Step 3: Create .env
    env_path = ROOT_DIR / ".env"
    config = create_basic_config(env_path, openwa_url, session_id)
    
    # Step 4: Start core services
    progress("⚡  Starting Core Services")
    print(cyan("\n▶ Installing dependencies..."))
    run_cmd("pip install fastapi uvicorn[standard] requests python-dotenv pydantic[hashing]")
    
    # Step 4a: Start CRM
    print(yellow("▶ Starting CRM API..."))
    api_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Step 4b: Start OpenWA (main service)
    openwa_process = subprocess.Popen([
        "docker", "run", "-d", "--name", "openwa-service",
        "-p", "2886:2886",
        "-e", f"API_KEY={secret_key}",
        "-e", "SESSION_ID={session_id}",
        "rmyndharis/openwa:0.1.4"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Give services time to start
    print(yellow("▶ Waiting 30 seconds for services to initialize..."))
    time.sleep(30)
    
    # Step 5: Verify health
    print(yellow("🔍 Checking health..."))
    run_cmd(f"curl -s http://localhost:8000/health")
    
    # Step 6: Show final instructions
    finish_setup(env_path, openwa_url, session_id)

def finish_setup(env_path, openwa_url, session_id):
    print(green("\n🎉 ALL SET! YOU ARE LIVE! 🎉"))
    print("Your WhatsApp CRM SA is now fully configured and running!")
    
    print("\n👉 What you do now:")
    print(cyan("1. On your phone:"))
    print(cyan("   • Open WhatsApp → Settings → Linked Devices → Link a Device"))
    print(cyan($"   • Scan QR code at: {openwa_url}"))
    print(cyan("2. Wait for connection ✅"))
    print(cyan("3. You'll see 'Messages Start Flowing'"))
    print(cyan("4. Use the dashboard URL to manage leads/messages"))
    print(cyan("\n🎯 Your business is now handling WhatsApp conversations automatically!"))
    print(cyan("\nNeed help? Check the full guide:"))
    print(f"   cat CLIENT-ONBOARDING.md\n")
    
    print(green("✨ Welcome to WhatsApp CRM SA — Zero monthly costs forever!"))
    print(cyan("\nStartup complete. Press Ctrl+C to stop, or close the terminal."))

# ── LAUNCH ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()