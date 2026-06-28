# API Reference

## Authentication
All admin routes require JWT authentication via cookies or Authorization header.

```bash
# Login
POST /api/auth/login
{"password": "your-admin-password"}

# Response
{"access_token": "jwt-token", "token_type": "bearer", "expires_in": 86400}
```

## Health Check
```bash
GET /health
# Response: {"status": "ok", "version": "0.1.4", ...}
```

## Contacts (Lead Management)
```bash
# List contacts
GET /api/contacts?page=1&limit=20&search=john

# Get single contact
GET /api/contacts/{contact_id}

# Create contact
POST /api/contacts
{"first_name": "John", "whatsapp_number": "27821234567", ...}

# Update contact
PUT /api/contacts/{contact_id}
{"lead_status": "qualified", ...}

# Delete contact
DELETE /api/contacts/{contact_id}
```

## Conversations
```bash
GET /api/conversations?status=active
GET /api/conversations/{conv_id}
PUT /api/conversations/{conv_id}/status
{"status": "resolved"}
```

## Messages
```bash
POST /api/messages/send
{"to": "27821234567", "content": "Hello!", "type": "text"}

POST /api/messages/quick-reply
{"reply_key": "greeting", "to": "27821234567"}
```

## AI
```bash
POST /api/ai/generate-reply?message=hello&language=en
# Response: {"reply": "generated text", "intent": "greeting"}

GET /api/ai/stats
# Response: {"provider": "groq", "groq_requests_today": 0, ...}
```

## Campaigns
```bash
GET /api/campaigns
POST /api/campaigns
{"name": "Welcome Series", "campaign_type": "drip", "trigger_event": "new_contact"}

POST /api/campaigns/{campaign_id}/activate
POST /api/campaigns/{campaign_id}/pause
POST /api/campaigns/{campaign_id}/broadcast
```

## Dashboard
```bash
GET /api/dashboard/summary
GET /api/dashboard/metrics
GET /api/dashboard/leads/pipeline
```

## Reports
```bash
GET /api/reports/lead-summary
# Response: {"total_leads": 150, "converted": 42, "ai_handled": 100, ...}
```

## Pricing
```bash
GET /api/pricing
# Response: {"plans": [{"name": "Starter", "price": 0, ...}, ...]}
```