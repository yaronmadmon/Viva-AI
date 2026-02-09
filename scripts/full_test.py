"""Create project and poll for AI generation with real OpenAI key."""
import sys, time
sys.path.insert(0, ".")
import httpx

BASE = "http://localhost:8000/api/v1"

# Login
r = httpx.post(BASE + "/auth/login", json={"email": "yaronmadmon@gmail.com", "password": "Test1234!"}, timeout=10)
print(f"Login: {r.status_code}")
token = r.json()["access_token"]
h = {"Authorization": "Bearer " + token}

# Create project
r = httpx.post(BASE + "/projects", json={
    "title": "Deep Learning for Early Cancer Detection in Medical Imaging",
    "description": "Investigating convolutional neural networks and transformer architectures for automated detection of malignant tumors in radiology scans.",
    "discipline_type": "stem",
}, headers=h, timeout=30)
print(f"Create: {r.status_code}")
d = r.json()
pid = d["id"]
print(f"Project ID: {pid}")

# Poll for generation
for i in range(30):  # Up to 5 minutes
    time.sleep(10)
    r = httpx.get(f"{BASE}/projects/{pid}/generation-status", headers=h, timeout=10)
    gs = r.json()
    gen = gs["generated_sections"]
    total = gs["total_sections"]
    words = gs["total_words"]
    pct = round(gen / total * 100) if total else 0
    print(f"\nPoll {i+1}: {gen}/{total} sections ({pct}%), {words:,} words total")
    for s in gs["sections"]:
        mark = "Y" if s["is_generated"] else "."
        print(f"  [{mark}] {s['title']}: {s['word_count']:,}w")
    if gs["all_generated"]:
        print("\n=== ALL SECTIONS GENERATED! ===")
        # Show first section preview
        r = httpx.get(f"{BASE}/projects/{pid}/document", headers=h, timeout=10)
        doc = r.json()
        art = doc["artifacts"][0]
        wc = len(art["content"].split())
        print(f"\nPreview of '{art['title']}' ({wc} words):")
        print(art["content"][:2000])
        break
