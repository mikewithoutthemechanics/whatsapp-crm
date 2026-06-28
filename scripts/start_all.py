#!/usr/bin/env python3
"""
WhatsApp CRM SA — One-Click Startup
====================================
Starts all services: FastAPI + OpenWA + ngrok tunnel.
Run: python scripts/start_all.py
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def start_openwa():
    """Start OpenWA WhatsApp gateway."""
    log("Starting OpenWA WhatsApp gateway...")
    port = os.getenv("OPENWA_API_URL", "http://localhost:2785").split(":")[-1].rstrip("/")
    session = os.getenv("OPENWA_SESSION_ID", "wavi-main")
    
    cmd = ["openwa", "--port", "2785", "--session", session]
    if Path("/dev/null").exists():  # Unix-like
        cmd.append("--headless")
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.wait()
    except FileNotFoundError:
        log("OpenWA not installed. Install with: npm install -g openwa")
        log("Or download from: https://github.com/rmyndharis/OpenWA")
        return

def start_ngrok():
    """Start ngrok tunnel for webhooks."""
    import time
    time.sleep(5)  # Wait for OpenWA to start
    
    log("Starting ngrok tunnel...")
    try:
        subprocess.run([
            "ngrok", "http", "2785",
            "--log", "stdout",
            "--log-format", "logfmt"
        ])
    except FileNotFoundError:
        log("ngrok not installed. Install from: https://ngrok.com/download")

def start_api():
    """Start FastAPI server."""
    log("Starting CRM API server...")
    subprocess.run([
        "uvicorn", "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])

def show_qr_code():
    """Display QR code for initial WhatsApp connection."""
    time.sleep(8)  # Wait for QR to be available
    log("Open http://localhost:8000/setup to connect your phone")

def main():
    print("=" * 50)
    print("🚀 WhatsApp CRM SA - One-Click Startup")
    print("=" * 50)
    
    # Check if .env exists
    if not Path(".env").exists():
        print("⚠️  No .env found. Run: python scripts/setup_wizard.py")
        return
    
    threads = [
        threading.Thread(target=start_openwa, daemon=True),
        threading.Thread(target=start_ngrok, daemon=True),
        threading.Thread(target=show_qr_code, daemon=True),
    ]
    
    for t in threads:
        t.start()
    
    try:
        start_api()
    except KeyboardInterrupt:
        log("\nShutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()