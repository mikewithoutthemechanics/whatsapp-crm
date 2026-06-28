# Knowledge Base

## FAQ

### Setup Issues
- **How do I connect OpenWA?**
  Add domain to .env with `OPENWA_WEBHOOK_URL=http://your-crm:8000/api/webhooks/openwa`
  Ensure port 8000 is open through your firewall

- **Why isn't my AI responding?**
  Check GROQ/OpenRouter API keys in `.env`. Temp fix: enable fallback providers

- **Problems with Drip Campaigns?**
  Verify trigger event matches customer actions. Check campaign status at `/api/campaigns`

### Account Management
- **How do I reset my admin password?**
  Update `ADMIN_PASSWORD` in `.env` securely
  Run `docker compose down -v` and `docker compose up -d` to reset containers

### Pricing & Upgrades
- **How to upgrade plans?**
  Use `/api/downgrade` or `/api/upgrade` endpoints
  Proof of payment via email required

## Troubleshooting

### Common Errors
- `Connection refused (911)`
  Ensure OpenWA port 8080 is open
  Check Docker network configuration

- `AI request limit exceeded`
  Upgrade Groq plan or use OpenRouter fallback

- `No session found (730)`
  Verify `OPENWA_SESSION_ID` matches your OpenWA session name

### Log Locations
- OpenWA: `docker logs openwa`
- CRM: `docker logs app`
- Vercel logs: https://vercel.com/michael-s-projects-1c4584cf/whatsapp-crm/logs

## Ticket Routing Guide

To create a support ticket:
1. Go to `https://whatsapp-crm.vercel.app/support`
2. Fill out: Issue Type | Description | Your Contact Info
3. Select: Priority (Low/Medium/High) | SLA (24h/48h/72h)
4. Attach screenshots if needed

Tickets are assigned to:
- **Point A**: General inquiries (1-2 days)
- **Point B**: Technical issues (24h SLA)
- ** Point C**: Sales questions (1-2 days)

Priority tickets bypass queue and go to senior support.