import httpx, time
BASE = "http://localhost:8000/api/v1"
c = httpx.Client(timeout=60)
r = c.post(f"{BASE}/auth/login", json={"email":"yaronmadmon@gmail.com","password":"Test1234!"})
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}
pid = "5e87d22c-8639-482a-8b65-d6e044a27927"
print("Triggering generation explicitly...")
r = c.post(f"{BASE}/projects/{pid}/generate", headers=h)
print(f"Trigger: {r.status_code} {r.json()}")
print("Waiting 60s...")
time.sleep(60)
r = c.get(f"{BASE}/projects/{pid}/generation-status", headers=h)
gs = r.json()
print(f"Words: {gs['total_words']}, Generated: {gs['generated_sections']}/{gs['total_sections']}")
for s in gs.get("sections", []):
    print(f"  {s['title']}: {s['word_count']} words")
