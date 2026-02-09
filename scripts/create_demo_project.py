"""Log in as the user and create a demo project with scaffolded sections."""
import httpx, json

BASE = "http://localhost:8000/api/v1"
client = httpx.Client(timeout=15)

# Login
r = client.post(f"{BASE}/auth/login", json={
    "email": "yaronmadmon@gmail.com",
    "password": "Test123!",
})
print(f"Login: {r.status_code}")
if r.status_code != 200:
    print(f"  Body: {r.text}")
    exit(1)

data = r.json()
token = data["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"Logged in as: {data['user']['full_name']}")

# Create project
r = client.post(f"{BASE}/projects", json={
    "title": "Impact of AI on Academic Integrity in Higher Education",
    "description": "Investigating how generative AI tools affect plagiarism detection, student learning outcomes, and institutional policies across universities.",
    "discipline_type": "social_sciences",
}, headers=headers)
print(f"\nCreate project: {r.status_code}")
if r.status_code not in (200, 201):
    print(f"  Body: {r.text}")
    exit(1)

project = r.json()
print(f"Project: {project['title']}")
print(f"ID: {project['id']}")
print(f"Discipline: {project['discipline_type']}")
print(f"Artifacts: {project['artifact_count']}")

# Fetch tree
r = client.get(f"{BASE}/artifacts/projects/{project['id']}/tree", headers=headers)
print(f"\nArtifact tree: {r.status_code}")
if r.status_code == 200:
    tree = r.json()
    print(f"Total: {tree['total_count']} sections")
    for art in tree.get("root_artifacts", []):
        print(f"  [{art['artifact_type']}] {art['title']}")

# List all projects
r = client.get(f"{BASE}/projects", headers=headers)
print(f"\nAll projects: {r.status_code}")
if r.status_code == 200:
    for p in r.json():
        print(f"  - {p['title']} ({p['discipline_type']}) - {p['artifact_count']} artifacts")

print("\nDone! Refresh your browser at http://localhost:3000/student to see the project.")
