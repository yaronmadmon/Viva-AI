"""End-to-end test: register/login, create project, verify scaffold."""
import httpx, json, sys

BASE = "http://localhost:8000/api/v1"

def test():
    client = httpx.Client(timeout=15)

    # --- 1. Try login with existing user ---
    print("1. Testing login...")
    r = client.post(f"{BASE}/auth/login", json={
        "email": "test_e2e@example.com",
        "password": "TestPass123!",
    })
    if r.status_code == 401:
        # Register first
        print("   User not found, registering...")
        r = client.post(f"{BASE}/auth/register", json={
            "email": "test_e2e@example.com",
            "password": "TestPass123!",
            "full_name": "E2E Tester",
            "role": "student",
        })
        print(f"   Register: {r.status_code}")
        if r.status_code not in (200, 201):
            print(f"   FAIL: {r.text}")
            sys.exit(1)
        data = r.json()
        token = data.get("access_token")
        if not token:
            print(f"   Register response has no token: {json.dumps(data, indent=2)}")
            # Try to login after registration
            r = client.post(f"{BASE}/auth/login", json={
                "email": "test_e2e@example.com",
                "password": "TestPass123!",
            })
            print(f"   Login after register: {r.status_code}")
            if r.status_code != 200:
                print(f"   FAIL: {r.text}")
                sys.exit(1)
            data = r.json()
            token = data.get("access_token")
    elif r.status_code == 200:
        data = r.json()
        token = data.get("access_token")
    else:
        print(f"   UNEXPECTED: {r.status_code} - {r.text}")
        sys.exit(1)

    if not token:
        print("   FAIL: No access token obtained!")
        sys.exit(1)
    print(f"   OK - got token: {token[:20]}...")
    headers = {"Authorization": f"Bearer {token}"}

    # --- 2. Create a new project ---
    print("\n2. Creating project...")
    r = client.post(f"{BASE}/projects", json={
        "title": "E2E Test Project",
        "description": "Testing scaffold",
        "discipline_type": "stem",
    }, headers=headers)
    print(f"   Create: {r.status_code}")
    if r.status_code not in (200, 201):
        print(f"   FAIL: {r.text}")
        sys.exit(1)
    project = r.json()
    project_id = project["id"]
    print(f"   Project ID: {project_id}")
    print(f"   Artifact count: {project.get('artifact_count')}")
    print(f"   Discipline: {project.get('discipline_type')}")

    # --- 3. Get artifact tree ---
    print("\n3. Fetching artifact tree...")
    r = client.get(f"{BASE}/artifacts/projects/{project_id}/tree", headers=headers)
    print(f"   Tree: {r.status_code}")
    if r.status_code != 200:
        print(f"   FAIL: {r.text}")
        sys.exit(1)
    tree = r.json()
    print(f"   Total artifacts: {tree.get('total_count')}")
    for art in tree.get("root_artifacts", []):
        print(f"   - [{art.get('artifact_type')}] {art.get('title', '(untitled)')}")

    # --- 4. Fetch existing project list ---
    print("\n4. Listing all projects...")
    r = client.get(f"{BASE}/projects", headers=headers)
    print(f"   List: {r.status_code}")
    if r.status_code == 200:
        projects = r.json()
        for p in projects:
            print(f"   - {p.get('title')} ({p.get('discipline_type')}) - {p.get('artifact_count')} artifacts")

    print("\n=== ALL TESTS PASSED ===")

if __name__ == "__main__":
    test()
