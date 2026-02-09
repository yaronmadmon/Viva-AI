"""
One-off script: register a user, create a project, verify it exists.
Run with the Viva AI server already running (e.g. port 8000).
Usage: python scripts/create_and_verify_project.py
"""
import sys
import httpx

BASE = "http://127.0.0.1:8000/api/v1"
EMAIL = "e2e-test@example.com"
PASSWORD = "TestPassword123"
FULL_NAME = "E2E Test User"
PROJECT_TITLE = "E2E Created Project"
PROJECT_DESC = "Created and verified by create_and_verify_project.py"


def main():
    with httpx.Client(timeout=30.0) as client:
        # 1. Health check
        r = client.get("http://127.0.0.1:8000/health")
        if r.status_code != 200:
            print("Server not ready:", r.status_code, r.text)
            sys.exit(1)
        print("Server OK:", r.json())

        # 2. Register (may 400 if user exists - then login)
        r = client.post(
            f"{BASE}/auth/register",
            json={"email": EMAIL, "password": PASSWORD, "full_name": FULL_NAME},
        )
        if r.status_code == 201:
            data = r.json()
            token = data["access_token"]
            print("Registered and got token")
        elif r.status_code == 400 and "already" in r.text.lower():
            r2 = client.post(
                f"{BASE}/auth/login",
                json={"email": EMAIL, "password": PASSWORD},
            )
            if r2.status_code != 200:
                print("Login failed:", r2.status_code, r2.text)
                sys.exit(1)
            token = r2.json()["access_token"]
            print("User exists, logged in")
        else:
            print("Register failed:", r.status_code, r.text)
            sys.exit(1)

        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create project
        r = client.post(
            f"{BASE}/projects",
            headers=headers,
            json={
                "title": PROJECT_TITLE,
                "description": PROJECT_DESC,
                "discipline_type": "mixed",
            },
        )
        if r.status_code != 201:
            print("Create project failed:", r.status_code, r.text)
            sys.exit(1)
        created = r.json()
        project_id = created["id"]
        print("Project created:", project_id, created.get("title"))

        # 4. Verify: get by id (definitive check that project exists)
        r = client.get(f"{BASE}/projects/{project_id}", headers=headers)
        if r.status_code != 200:
            print("Get project failed:", r.status_code, r.text)
            sys.exit(1)
        got = r.json()
        if got["id"] != project_id or got["title"] != PROJECT_TITLE:
            print("Get project mismatch:", got)
            sys.exit(1)
        print("Get by ID OK:", got["title"], "status:", got["status"])

        # 5. Verify: list projects (optional; may hit server issues)
        r = client.get(f"{BASE}/projects", headers=headers)
        if r.status_code == 200:
            projects = r.json()
            found = [p for p in projects if p["id"] == project_id]
            if found:
                print("Project found in list:", found[0]["title"])
            else:
                print("Project not in list (list returned", len(projects), "items)")
        else:
            print("List projects returned:", r.status_code, "(project already verified via GET)")

    print("\nDone. Project was created and verified.")


if __name__ == "__main__":
    main()
