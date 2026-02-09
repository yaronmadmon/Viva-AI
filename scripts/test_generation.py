"""Quick E2E test for the dissertation generation pipeline."""
import httpx
import json
import sys
import time

BASE = "http://localhost:8000/api/v1"

# Login
r = httpx.post(f"{BASE}/auth/login", json={"email": "yaronmadmon@gmail.com", "password": "Test1234!"}, timeout=10)
if r.status_code != 200:
    r = httpx.post(f"{BASE}/auth/login", json={"email": "test_e2e@example.com", "password": "Test1234!"}, timeout=10)
print(f"Login: {r.status_code}")
if r.status_code != 200:
    print(r.text[:300])
    sys.exit(1)

token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create a project
r = httpx.post(
    f"{BASE}/projects",
    json={
        "title": "Machine Learning Applications in Clinical Healthcare Diagnostics",
        "description": (
            "Investigating the efficacy and reliability of deep learning models for "
            "automated medical image analysis, focusing on early detection of cancer "
            "using convolutional neural networks in radiology settings."
        ),
        "discipline_type": "stem",
    },
    headers=headers,
    timeout=30,
)
print(f"Create project: {r.status_code}")
if r.status_code != 201:
    print(r.text[:500])
    sys.exit(1)

data = r.json()
pid = data["id"]
print(f"  Project ID: {pid}")
print(f"  Artifact count: {data['artifact_count']}")

# Check generation status
def check_status():
    r = httpx.get(f"{BASE}/projects/{pid}/generation-status", headers=headers, timeout=10)
    if r.status_code != 200:
        print(f"  Generation status error: {r.status_code}")
        return None
    gs = r.json()
    print(f"  Total sections: {gs['total_sections']}, Generated: {gs['generated_sections']}, Words: {gs['total_words']}")
    for s in gs["sections"]:
        mark = "Y" if s["is_generated"] else "N"
        print(f"    [{mark}] {s['title']}: {s['word_count']} words")
    return gs

print("\n--- Immediate check ---")
gs = check_status()

# Wait and poll
for i in range(6):
    print(f"\n--- Waiting 10s (poll {i+1}/6) ---")
    time.sleep(10)
    gs = check_status()
    if gs and gs["all_generated"]:
        print("\nAll sections generated!")
        break

# Show a snippet of the document
r = httpx.get(f"{BASE}/projects/{pid}/document", headers=headers, timeout=10)
if r.status_code == 200:
    doc = r.json()
    print(f"\n--- Document preview ---")
    for art in doc["artifacts"][:3]:
        content = art["content"][:300]
        print(f"\n## {art['title']}")
        print(content)
        print("..." if len(art["content"]) > 300 else "")
