"""Display the full generated dissertation."""
import sys
sys.path.insert(0, ".")
import httpx

BASE = "http://localhost:8000/api/v1"
r = httpx.post(BASE + "/auth/login", json={"email": "yaronmadmon@gmail.com", "password": "Test1234!"}, timeout=10)
token = r.json()["access_token"]
h = {"Authorization": "Bearer " + token}

pid = "c2c96966-ea68-4019-9fcc-8ba0468c78a8"
r = httpx.get(f"{BASE}/projects/{pid}/document", headers=h, timeout=10)
doc = r.json()

total_words = 0
for art in doc["artifacts"]:
    wc = len(art["content"].split())
    total_words += wc

print(f"TOTAL: {total_words:,} words across {len(doc['artifacts'])} sections")
print("=" * 70)

for art in doc["artifacts"]:
    wc = len(art["content"].split())
    print(f"\n{'=' * 70}")
    print(f"  {art['title']} ({wc:,} words)")
    print(f"{'=' * 70}\n")
    print(art["content"])
