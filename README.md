# WhatsApp CRM SA

**A free WhatsApp CRM for South African SMMEs.** AI-powered auto-replies, lead management, drip campaigns, and broadcasting — all built for the SA market.

## Features

| Feature | Description |
|---|---|
| **AI Auto-Reply** | Groq (14,400 free req/day) + OpenRouter fallback. Handles greetings, pricing inquiries, bookings |
| **Lead Management** | Track leads with SA-specific scoring, tags, and pipeline stages |
| **Drip Campaigns** | Automated message sequences triggered by events (new lead, purchase, inactivity) |
| **Broadcast Messages** | Send to targeted audience segments by tag, industry, or province |
| **Dashboard** | Real-time stats, conversation queue, pipeline visualization |
| **SA-Ready** | ZAR currency, SAST timezone, RSA phone numbers, load-shedding scheduling |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run setup
python scripts/setup.py

# 3. Edit .env with your credentials
nano .env

# 4. Start the server
python app/main.py
# or with uvicorn:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Free API Keys You Need

1. **Groq AI** (free, no credit card): https://console.groq.com
2. **WhatsApp Business API**: Choose Meta or Twilio
   - Meta (free): https://developers.facebook.com/docs/whatsapp/cloud-api
   - Twilio (pay-per-message): https://www.twilio.com/docs/whatsapp
3. **Supabase** (free tier): https://supabase.com

## Architecture

```
WhatsApp Business API (Meta/Twilio)
        │
        ▼
┌───────────────────────┐
│   FastAPI Application  │
│       (app/main.py)    │
├───────────────────────┤
│  AI Engine     │  WhatsApp  │
│  (ai_service)  │  Service   │
│                │(whatsapp_) │
│                │ service)   │
├───────────────────────┤
│  Campaign      │  Database  │
│  Engine        │  (Postgres/│
│ (campaign_svc) │   SQLite)  │
├───────────────────────┤
│  REST API +    │  Dashboard │
│  Webhooks      │  (static)  │
└───────────────────────┘
```

## Pricing: $0 to Start

- Groq: 14,400 req/day free
- OpenRouter: 50 req/day free (1,000 with $10 credit)
- WhatsApp: Meta is free, Twilio is pay-per-use
- Supabase: 500MB free
- Hosting: Run on a free-tier VPS or Railway/Render

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (Supabase) with SQLite fallback
- **AI**: Groq (primary) → OpenRouter (fallback) → Templates (offline)
- **WhatsApp**: Meta Business API / Twilio
- **Dashboard**: HTML + Tailwind CSS + Chart.js
- **Scheduling**: APScheduler
- **Deployment**: Docker-ready, Railway/Vercel/Railway compatible

## Project Structure

```
whatsapp-crm/
├── app/
│   ├── main.py                 ← FastAPI entry point
│   ├── config.py               ← Environment configuration
│   ├── models/                 ← Database models (SQLAlchemy)
│   │   └── __init__.py
│   ├── services/
│   │   ├── ai_service.py       ← AI response engine
│   │   ├── whatsapp_service.py ← WhatsApp API integration
│   │   └── campaign_service.py ← Drip campaign engine
│   ├── api/
│   │   └── router.py           ← REST API endpoints
│   └── crons/                  ← Scheduled tasks
├── web/
│   └── pages/
│       └── dashboard.html      ← Admin dashboard (static)
├── scripts/
│   └── setup.py                ← Setup & dependency checker
├── tests/                      ← Test suite
├── .env.example                ← Environment template
├── requirements.txt
├── docker-compose.yml
└── README.md
```