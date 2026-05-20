# WhatsApp CRM SA — Client Onboarding Guide

**What you're getting:** A WhatsApp CRM built specifically for South African businesses.
Auto-replies, lead scoring, drip campaigns, broadcast, and a dashboard — all running on
[OpenWA](https://github.com/rmyndharis/OpenWA) (free, self-hosted, no Meta approval needed).

> **Stack value:** Free tier covers 99% of SA SMMEs. Zero monthly cost until you outgrow it.

---

## Step 1 — Run the setup (5 minutes)

```bash
cd whatsaap-crm
python scripts/setup-production.py
```

The script asks you for everything it needs and writes a ready-to-use `.env` file.

---

## Step 2 — Start OpenWA (your WhatsApp gateway)

```bash
docker run -p 2785:2785 -p 2886:2886 \
  -v openwa-data:/app/data \
  --name crm-openwa \
  rmyndharis/openwa:0.1.4
```

Open **[http://localhost:2886](http://localhost:2886)** in your browser → **Create Session** →
scan the QR code with your phone (WhatsApp → Settings → Linked Devices → Link a Device).

Once connected, click **Settings → API Access** → **Create API Key** → copy the key.

---

## Step 3 — Fill in your `.env`

The setup script created `.env` for you. Open it and paste:

```ini
WHATSAPP_PROVIDER=openwa
OPENWA_API_URL=http://localhost:2785
OPENWA_API_KEY=paste-your-key-here-from-step-2
OPENWA_SESSION_ID=default
ADMIN_PASSWORD=choose-a-strong-password-for-your-admin-crm-login
GROQ_API_KEY=gsk_paste-from-https://console.groq.com
```

That's it — 6 lines.

> **Groq AI key** — free, no credit card, 14,400 AI calls per day.
> Get it here: https://console.groq.com → API Keys → Create

---

## Step 4 — Start the stack

```bash
docker compose up -d
```

Wait 20 seconds, then:

```bash
curl http://localhost:8000/health
```

You should see `{"status":"healthy",...}`.

---

## Step 5 — Log in to the admin area

```bash
curl -X POST http://localhost:8000/api/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"password":"YOUR_ADMIN_PASSWORD"}'
```

Copy the `access_token` from the response → paste it into Swagger (http://localhost:8000/docs):

```
Authorization: Bearer <your-access-token>
```

Now you have full access to:
- **GET `/api/admin/health/detailed`** — full health report (DB, AI, OpenWA gateway)
- **GET `/api/dashboard/summary`** — conversation stats
- **GET `/api/contacts/`** — lead list
- **GET `/api/conversations/`** — live conversations
- **POST `/api/messages/send`** — send a manual WhatsApp reply

---

## Step 6 — Production deploy (one command)

```bash
./deploy.sh railway   # requires railway CLI: npm i -g @railway/cli && railway login
```

Or connect your GitHub repo to **Render.com** and it auto-deploys on every push.

Heroku alternative:

```bash
heroku create your-crm-name
heroku config:set WHATSAPP_PROVIDER=openwa OPENWA_API_KEY=your-key ...
heroku ps:scale web=1
```

---

## What each part does

```
Your customer sends a WhatsApp message
        │
        ▼
OpenWA gateway receives it (self-hosted, free)
        │
        ▼
OpenWA webhook → /api/webhooks/whatsapp
        │
        ▼
FastAPI AI engine detects intent
        │
        ▼
Groq generates a human-sounding reply
        │
        ▼
OpenWA sends it back to your customer
        │
        ▼
CRM stores every message in the dashboard
```

---

## Integration checklist

| Item | Where to set it |
|---|---|
| OpenWA API key | `.env` → `OPENWA_API_KEY` |
| OpenWA session | `.env` → `OPENWA_SESSION_ID` (default = `default`) |
| AI auto-reply | `.env` → `GROQ_API_KEY` from https://console.groq.com |
| Admin login | `.env` → `ADMIN_PASSWORD` (any strong password) |
| Webhook callback | OpenWA Dashboard → Settings → Webhooks → `http://your-domain:8000/api/webhooks/whatsapp` |
| Twilio fallback | `.env` → `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` |

---

## SA-specific features

| Feature | How it works |
|---|---|
| **RSA number normalising** | `0821234567` → `27821234567` automatically — no code changes needed |
| **ZAR currency** | Ready for PayFast (SA payment gateway) — just set `PAYFAST_MERCHANT_ID` |
| **SAST timezone** | All timestamps and campaigns use `Africa/Johannesburg` |
| **Load-shedding scheduling** | Contacts can be tagged with stage; campaigns auto-pause during Stage 4+ |
| **Province tagging** | Leads tagged by province → province-level revenue forecasts |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| OpenWA won't connect | Increase Docker `shm_size` to `2G`; Chrome/Chromium needs shared memory |
| AI replies are slow | Check Groq quota at https://console.groq.com (free: 30 requests/minute) |
| Dashboard shows 0 conversations | First run uses SQLite; phone number in DB won't match meta/twilio — wait for confirmed OpenWA hook |
| Can't log in to admin | `ADMIN_PASSWORD` not set or SECRET_KEY too short — check `.env` |
| Error: `required when WHATSAPP_PROVIDER=openwa` | `OPENWA_API_KEY` and `OPENWA_SESSION_ID` both needed — check `.env` values |

---

## Cost breakdown

| Item | Cost / month |
|---|---|
| OpenWA gateway | **R0** (self-hosted Docker) |
| Groq AI | **R0** (14,400 requests/day free tier) |
| Supabase DB | **R0** (50,000 rows / 500 MB free) |
| Railway / Render hosting | **R0** (hobby / free tier) |
| **Total** | **R0 / month** |

---

## Getting help

| | |
|---|---|
| OpenWA issues | https://github.com/rmyndharis/OpenWA → Issues |
| CRM code | https://github.com/mikewithoutthemechanics/whatsapp-crm |
| Groq key | https://console.groq.com |
| Deploy help | `./deploy.sh` → see all commands |
