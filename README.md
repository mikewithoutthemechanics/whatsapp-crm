# WhatsApp CRM SA

**A free WhatsApp CRM for South African SMMEs.** AI-powered auto-replies, lead management, drip campaigns, and broadcasting — all built for the SA market.

> **v0.1.4** — OpenWA integration added. Self-hosted WhatsApp gateway — no Meta approval, no vendor lock-in, completely free.

## ✨ Features

| Feature | Description |
|---|---|
| **AI Auto-Reply** | Groq (14,400 req/day) + OpenRouter fallback. Handles greetings, pricing, bookings |
| **Lead Management** | SA-specific scoring, tags, pipeline stages (new → contacted → qualified → converted) |
| **Drip Campaigns** | Automated message sequences triggered by events (new lead, inactivity, purchase) |
| **Broadcast Messages** | Send to targeted audience segments by tag, industry, or province |
| **OpenWA Self-hosted** | **Recommended:** zero-per-message-cost WhatsApp via [OpenWA v0.1.4](https://github.com/rmyndharis/OpenWA) |
| **Dashboard** | Real-time stats, conversation queue, pipeline Viz |
| **SA-Ready** | ZAR currency, SAST timezone, RSA phone numbers, load-shedding scheduling |

---

## Quick Start — OpenWA (Recommended, 5 min)

This is the fastest way to get your own WhatsApp number working — **zero cost, no Meta/Business Manager approval needed**.

### Step 1 — Stack up OpenWA

```bash
# Pull the OpenWA container image
docker run -p 2785:2785 -p 2886:2886 --name openwa -v openwa-data:/app/data rmyndharis/openwa:0.1.4

# Or use the dev compose stack from this repo:
docker compose up -d openwa db
```

Access the dashboard: **[http://localhost:2886](http://localhost:2886)**

### Step 2 — Pair your phone

1. Open http://localhost:2886 in your browser
2. Click **Create Session** → name it anything (e.g. `default`)
3. A QR code appears — open WhatsApp → Settings → Linked Devices → **Link a Device**
4. Scan the QR code
5. ✅ Session is connected — you'll see your own WhatsApp number listed

### Step 3 — Get the OpenWA API key

In the OpenWA dashboard:
1. Click ⚙️ **Settings** → **API Access**
2. Create a new API key → copy it

### Step 4 — Set up this CRM

```bash
git clone git@github.com:mikewithoutthemechanics/whatsapp-crm.git
cd whatsapp-crm
cp .env.example .env
```

Edit `.env` and set:

```ini
WHATSAPP_PROVIDER=openwa
OPENWA_API_KEY=paste-your-openwa-api-key-here
OPENWA_SESSION_ID=default           # must match your session name in OpenWA
GROQ_API_KEY=gsk_xxx                # free at https://console.groq.com
```

Then start both containers:

```bash
docker compose up -d
```

The CRM FastAPI service will be at **http://localhost:8000**  
The OpenWA REST API is at **http://localhost:2785/api**  
The OpenWA web dashboard is at **http://localhost:2886**

---

## 🐳 Full Docker Compose (CRM + OpenWA + PostgreSQL)

```bash
# 1. Start the OpenWA gateway first (so it's ready before CRM connects)
docker compose up -d openwa db

# 2. Visit OpenWA dashboard → scan QR → copy API key (see above)

# 3. Start the CRM backend
docker compose up -d app

# 4. Check everything is healthy
docker compose ps
docker compose logs -f app

# 5. Test — is OpenWA reachable from CRM?
curl http://localhost:8000/health
```

---

## 🗃️ Project Structure

```
whatsapp-crm/
├── app/
│   ├── main.py                 ← FastAPI entry point
│   ├── config.py               ← Environment config (all env vars validated here)
│   ├── models/__init__.py      ← SQLAlchemy ORM models (20+ tables)
│   ├── services/
│   │   ├── ai_service.py       ← Groq / OpenRouter AI engine
│   │   ├── whatsapp_service.py ← WhatsApp provider abstraction
│   │   │                         ├── OpenWAService (Recommended — self-hosted)
│   │   │                         ├── MetaWhatsAppService (Meta Business API)
│   │   │                         └── TwilioWhatsAppService (Twilio)
│   │   └── campaign_service.py ← Drip campaign engine
│   └── api/router.py           ← REST API endpoints (contacts / messages / campaigns / webhooks)
├── web/pages/
│   └── dashboard.html          ← Admin dashboard (static)
├── scripts/
│   └── setup.py                ← Setup & dependency checker
├── tests/
│   └── test_all.py             ← Full test suite
├── .env.example                ← Environment variable template
├── requirements.txt
├── Dockerfile                  ← FastAPI runtime image
├── docker-compose.yml          ← Full stack: CRM + OpenWA + PostgreSQL
└── README.md
```

---

## 🔌 WhatsApp Providers

| Provider | Cost | Funnel | Setup | Viability |
|---|---|---|---:|---:|
| **OpenWA** ⭐ | Free (self-host) | Self-host WhatsApp | 5 min | ✅ Recommended |
| Meta Cloud API | Free tier | Meta approval required | 2 days | 🟡 |
| Twilio WhatsApp | Pay-per-message | Buy number | 15 min | 🟡 |
| WhatsApp.io | Pay-per-message | Easiest | 5 min | 🟡 |

Set with `WHATSAPP_PROVIDER=openwa|meta|twilio` in `.env`.

---

## 🤖 How AI Auto-Reply Works

```
Customer sends WhatsApp message
        │
        ▼
OpenWA delivers message via webhook → /api/webhooks/openwa
  (see gateway health check at /api/webhooks/openwa/health)
        │
        ▼
FastAPI Wwebhook handler extracts message
        │
        ▼
  ai_service.detect_intent() → classification
        │
        ▼
  ai_service.generate_response() → Groq / OpenRouter
        │
        ▼
  whatsapp_service.send_text() → OpenWA REST API
        │
        ▼
  Customer receives AI auto-reply
```

The CRM sets `WA_HEALTH_URL=/api/webhooks/openwa/health` so that
*other tools* (like OpenClaw) can probe `GET wa://{instance}/health`
and get back `{"status":"healthy","provider":"openwa","message":"..."}`.

---

## Free API Keys Needed

| Service | Why | Fee | Sign-up |
|---|---|:---:|---|
| **Groq** | AI auto-reply engine | Free (14K req/day) | https://console.groq.com |
| **OpenRouter** | AI fallback / backup | Free tier | https://openrouter.ai |
| **OpenWA** | WhatsApp gateway | Free (self-hosted) | https://github.com/rmyndharis/OpenWA |
| **Supabase** | CRM database | Free (50K rows) | https://supabase.com |

---

## Pricing: $0/month to Start

Complete SA SMME WhatsApp CRM stack — **free tiers only**:

| Item | Cost |
|---|---|
| Groq AI | $0 (14,400 req/day) |
| OpenWA gateway | $0 (self-hosted, Docker) |
| Supabase database | $0 (50,000 rows / 500 MB) |
| Railway / Render hosting | $0 (free tier / hobby plan) |
| **Total** | **$0 / month** |

Scale: upgrade to Groq Pro ($99/mo) or run on a VPS (R799/mo) when ready.

---

## SA-Specific Design Decisions

| Decision | Why |
|---|---|
| `Africa/Johannesburg` timezone | All timestamps and campaigns use SAST |
| RSA number detection | Auto-fixes `0821234567` → `27821234567` via code-point normalisation |
| ZAR currency throughout | Ready for PayFast → no ZAR→USD conversion friction |
| Load-shedding schedule field | Contacts can store load-shedding slots; campaigns auto-off during Stage 4+ |
| ph no. billing by Province | Leads tagged by province = province-level revenue forecasts |

---

## Getting Started (meta / twilio providers)

If you prefer Meta's Cloud API or Twilio, just flip the provider in `.env`:

```bash
# Meta Cloud API
WHATSAPP_PROVIDER=meta
META_PHONE_NUMBER_ID=your-waba-phone-num-id
META_ACCESS_TOKEN=your-meta-permanent-access-token

# Twilio
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=ACxxxxxx
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

### OpenWA Webhook (CRM sends → OpenWA receives)

Point your OpenWA instance's `Webhook URL` to:

```
http://your-crm-host:8000/api/webhooks/openwa
```

Set `OPENWA_WEBHOOK_SECRET` to match the HMAC key configured in OpenWA so
incoming events are verified with `X-Audit-HMAC`.

Computed health alias consumed by OpenWA and any other agent probing it:

```
GET http://your-crm:8000/api/webhooks/openwa/health
→ {"status":"healthy","openwa":true,"timestamp":1234567890}
```

Then use the runtime docs aliased from the nest of `/api/webhooks/openwa/resources/*`.

Use the staged path `/api/webhooks/openwa/resources/docs` to cache on your own runtime docs FTW.
Probe `/api/webhooks/openwa/resources/health` first, cache the schema, and wire OpenWA event callbacks into your devloop internals before putting them into production.

---

## Security

- **Rate Limiting**: Max 200 conversations per day, 50 messages per conversation
- **JWT Authentication**: HMAC-signed tokens for admin routes
- **Secure Cookies**: HttpOnly, SameSite=Lax with Secure flag in production
- **API Key Validation**: Required fields checked on startup
- **Circuit Breakers**: AI services protected against cascading failures
- **Input Sanitization**: Search queries sanitized against injection attacks

---

## Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Database**: PostgreSQL (Supabase) with SQLite fallback
- **WhatsApp**: OpenWA (self-hosted, free) · Meta · Twilio
- **AI**: Groq (primary) → OpenRouter (fallback)
- **Scheduling**: APScheduler
- **Container**: Docker + Docker Compose

---

## Contributing

PRs welcome. This project follows the [Conventional Commits](https://www.conventionalcommits.org/) spec.

```
switch to the branch
  git checkout -b feature/openwa-image-send
  git push origin feature/openwa-image-send
```

## License

MIT — see `LICENSE`.
