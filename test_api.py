import httpx

BASE = "http://127.0.0.1:8000"
passed = 0
total = 13

def test(n, name, ok, detail=""):
    global passed
    if ok:
        passed += 1
    status = "PASS" if ok else "FAIL"
    print(f"{status} {n}. {name}", f"| {detail}" if detail else "")

r = httpx.get(f"{BASE}/health")
test(1, "Health", r.json()["status"] == "healthy")

r = httpx.post(f"{BASE}/api/contacts/", json={
    "whatsapp_number": "0821112233", "first_name": "Thabo", "last_name": "Mokoena",
    "email": "thabo@example.com", "lead_source": "whatsapp", "province": "Gauteng",
    "city": "Johannesburg", "tags": ["new-lead"]
})
data = r.json()
test(2, "Create contact", data["success"], f'ID: {data["data"]["id"][:8]}')
cid = data["data"]["id"]

r = httpx.post(f"{BASE}/api/contacts/", json={
    "whatsapp_number": "0824445566", "first_name": "Lerato", "last_name": "Ndlovu"
})
test(3, "Create contact 2", r.json()["success"])

r = httpx.get(f"{BASE}/api/contacts/")
test(4, "List contacts", r.json()["pagination"]["total"] >= 2, f'total: {r.json()["pagination"]["total"]}')

r = httpx.get(f"{BASE}/api/contacts/{cid}")
data = r.json()
test(5, "Get contact by ID", data.get("first_name") == "Thabo", f'name: {data.get("first_name")}')

r = httpx.put(f"{BASE}/api/contacts/{cid}", json={"lead_status": "qualified", "lead_score": 50})
test(6, "Update contact", r.json()["success"])

r = httpx.post(f"{BASE}/api/leads/capture", json={
    "whatsapp_number": "0827778899", "first_name": "Sipho", "last_name": "Dlamini",
    "source": "landing_page", "utm_source": "facebook", "utm_campaign": "winter_sale"
})
data = r.json()
test(7, "Lead capture", data["success"], f'score: {data["lead_score"]}')

r = httpx.post(f"{BASE}/api/campaigns/", json={
    "name": "Welcome New Leads", "campaign_type": "drip", "trigger_event": "new_lead",
    "messages_sequence": [{"delay_hours": 0, "message": "Welcome!"}]
})
data = r.json()
test(8, "Create campaign", data["success"], f'ID: {data["data"]["id"][:8]}')
camp_id = data["data"]["id"]

r = httpx.post(f"{BASE}/api/campaigns/{camp_id}/activate")
test(9, "Activate campaign", r.status_code == 200)

r = httpx.post(f"{BASE}/api/campaigns/{camp_id}/add-subscriber?contact_id={cid}")
test(10, "Add subscriber", r.json()["success"])

r = httpx.get(f"{BASE}/api/dashboard/summary")
data = r.json()
test(11, "Dashboard", "total_contacts" in data, f'contacts: {data.get("total_contacts")}')

r = httpx.get(f"{BASE}/api/contacts/tags")
data = r.json()
test(12, "List tags", "data" in data, f'tags: {len(data["data"])}')

r = httpx.get(f"{BASE}/api/dashboard/leads/pipeline")
data = r.json()
test(13, "Lead pipeline", "pipeline" in data, f'stages: {list(data["pipeline"].keys())}')

print(f"\n{passed}/{total} tests passed")
