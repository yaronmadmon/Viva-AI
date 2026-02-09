"""Check what actual data exists in the project."""
import httpx, json

BASE = "http://localhost:8000/api/v1"
client = httpx.Client(timeout=15)

# Login
r = client.post(f"{BASE}/auth/login", json={
    "email": "yaronmadmon@gmail.com",
    "password": "Test123!",
})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get project list
r = client.get(f"{BASE}/projects", headers=headers)
projects = r.json()
print(f"=== {len(projects)} project(s) ===\n")

for p in projects:
    print(f"Project: {p['title']}")
    print(f"  ID: {p['id']}")
    print(f"  Discipline: {p['discipline_type']}")
    print(f"  Status: {p['status']}")
    print(f"  Artifacts: {p['artifact_count']}")
    print(f"  Description: {p.get('description', '(none)')}")
    
    # Get tree
    r2 = client.get(f"{BASE}/artifacts/projects/{p['id']}/tree", headers=headers)
    if r2.status_code == 200:
        tree = r2.json()
        print(f"\n  Artifact tree ({tree['total_count']} items):")
        for art in tree.get("root_artifacts", []):
            print(f"    [{art['artifact_type']}] {art.get('title') or '(untitled)'} (id: {art['id'][:8]}...)")
            
            # Fetch each artifact's content
            r3 = client.get(f"{BASE}/artifacts/{art['id']}", headers=headers)
            if r3.status_code == 200:
                detail = r3.json()
                content = detail.get("content", "")
                print(f"      Content: {repr(content[:100]) if content else '(empty)'}")
            else:
                print(f"      Fetch failed: {r3.status_code} - {r3.text[:100]}")
    print()
