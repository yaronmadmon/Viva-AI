"""Delete old projects and create a fresh one with rich scaffold content."""
import httpx

BASE = "http://localhost:8000/api/v1"
client = httpx.Client(timeout=30)

# Login
r = client.post(f"{BASE}/auth/login", json={
    "email": "yaronmadmon@gmail.com",
    "password": "Test123!",
})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"Logged in as: {r.json()['user']['full_name']}")

# List existing projects
r = client.get(f"{BASE}/projects", headers=headers)
projects = r.json()
print(f"Found {len(projects)} existing project(s)")

# Delete all existing projects
for p in projects:
    r = client.delete(f"{BASE}/projects/{p['id']}", headers=headers)
    print(f"  Deleted '{p['title']}': {r.status_code}")

# Create fresh project with rich scaffold
r = client.post(f"{BASE}/projects", json={
    "title": "Impact of AI on Academic Integrity in Higher Education",
    "description": "Investigating how generative AI tools affect plagiarism detection, student learning outcomes, and institutional policies across universities.",
    "discipline_type": "social_sciences",
}, headers=headers)
print(f"\nCreated project: {r.status_code}")
if r.status_code in (200, 201):
    project = r.json()
    print(f"  Title: {project['title']}")
    print(f"  ID: {project['id']}")
    print(f"  Discipline: {project['discipline_type']}")
    print(f"  Artifacts: {project['artifact_count']}")

    # Verify tree
    r = client.get(f"{BASE}/artifacts/projects/{project['id']}/tree", headers=headers)
    if r.status_code == 200:
        tree = r.json()
        print(f"\n  Sections ({tree['total_count']}):")
        for art in tree.get("root_artifacts", []):
            # Fetch content
            r2 = client.get(f"{BASE}/artifacts/{art['id']}", headers=headers)
            content_len = len(r2.json().get("content", "")) if r2.status_code == 200 else 0
            print(f"    [{art['artifact_type']}] {art['title']} ({content_len} chars)")
else:
    print(f"  Error: {r.text}")

print("\nDone! Refresh http://localhost:3000/student")
