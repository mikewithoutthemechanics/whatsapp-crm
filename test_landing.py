import httpx

BASE = "http://127.0.0.1:8000"

# 1. Test landing page loads
r = httpx.get(f"{BASE}/landing", follow_redirects=True)
landing_ok = "WhatsApp CRM" in r.text
print(f"1. Landing page: {'PASS' if landing_ok else 'FAIL'} | Status: {r.status_code}")

# 2. Submit lead via form API
r = httpx.post(f"{BASE}/api/leads/capture", json={
    "whatsapp_number": "0829998877",
    "first_name": "Nomsa",
    "last_name": "Zulu",
    "email": "nomsa@business.co.za",
    "source": "landing_page",
    "utm_source": "google",
    "utm_medium": "cpc",
    "utm_campaign": "winter_sale",
})
data = r.json()
print(f"2. Lead capture: {data.get('success')} | Score: {data.get('lead_score')}")

# 3. Verify lead in DB
r = httpx.get(f"{BASE}/api/contacts/")
contacts = r.json()["data"]
nomsa = [c for c in contacts if c.get("whatsapp_number") == "27829998877"]
print(f"3. In DB: {'YES' if nomsa else 'NO'} | Total contacts: {r.json()['pagination']['total']}")

# 4. Check lead details
if nomsa:
    cid = nomsa[0]["id"]
    r = httpx.get(f"{BASE}/api/contacts/{cid}")
    data = r.json()
    print(f"4. Lead: {data.get('first_name')} {data.get('last_name')} | Status: {data.get('lead_status')} | Score: {data.get('lead_score')}")

# 5. Dashboard reflects new lead
r = httpx.get(f"{BASE}/api/dashboard/summary")
print(f"5. Dashboard leads today: {r.json().get('new_leads_today')}")
