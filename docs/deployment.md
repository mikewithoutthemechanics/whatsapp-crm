# Deployment Guide

## Vercel Deployment
1. Connect repository to Vercel.
2. Set environment variables: `GROQ_API_KEY`, `OPENWA_API_KEY`, `SECRET_KEY`, etc.
3. Deploy to production.

## Docker Deployment
```bash
# Start OpenWA and database
docker compose up -d openwa db

# Start CRM application
docker compose up -d app

# Verify health
curl http://localhost:8000/health
```

## Environment Variables
Create `.env` from `.env.example` and configure:
- `WHATSAPP_PROVIDER=openwa` (or `meta`, `twilio`)
- `OPENWA_API_KEY=your-openwa-api-key`
- `OPENWA_SESSION_ID=your-session-name`
- `GROQ_API_KEY=your-groq-api-key`
- `ADMIN_PASSWORD=admin-secret`