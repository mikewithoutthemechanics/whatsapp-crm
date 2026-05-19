Whatsapp CRM SA — Setup Guide
===============================

1. Install dependencies
   pip install -r requirements.txt

2. Run setup script
   python scripts/setup.py

3. Configure environment
   nano .env
   - Add Groq API key (free at https://console.groq.com)
   - Add WhatsApp Business API credentials
   - Configure database URL

4. Initialize database
   python scripts/migrate.py

5. Start the server
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

6. Run tests
   pytest tests/ -v