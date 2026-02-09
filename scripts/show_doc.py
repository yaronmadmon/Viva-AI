"""Show generated document content."""
import httpx

BASE = "http://localhost:8000/api/v1"
r = httpx.post(f"{BASE}/auth/login", json={"email": "yaronmadmon@gmail.com", "password": "Test1234!"}, timeout=10)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

r = httpx.get(f"{BASE}/projects/8d012524-e52b-4110-89fa-cc743f9e7ff6/document", headers=headers, timeout=10)
doc = r.json()
for art in doc["artifacts"]:
    wc = len(art["content"].split())
    print(f"\n{'='*60}")
    print(f"  {art['title']} ({wc} words)")
    print(f"{'='*60}")
    print(art["content"][:800])
    if len(art["content"]) > 800:
        print("\n  [...truncated...]")
