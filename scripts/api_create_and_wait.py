"""Create a project via API and monitor the v2 background generation."""
import httpx
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = "http://localhost:8000/api/v1"

def s(text):
    return text.encode("ascii", errors="replace").decode("ascii") if text else ""

def main():
    c = httpx.Client(timeout=120)

    # Login
    print("Authenticating...")
    r = c.post(f"{BASE}/auth/login", json={
        "email": "yaronmadmon@gmail.com", "password": "Test1234!",
    })
    if r.status_code != 200:
        print(f"Login failed: {r.status_code}")
        sys.exit(1)
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    print("  OK")

    # Create project
    print("\nCreating project...")
    r = c.post(f"{BASE}/projects", json={
        "title": "Deep Learning for Early Cancer Detection: CNN vs Transformer Architectures",
        "description": (
            "This dissertation critically evaluates CNN and vision transformer "
            "architectures for automated cancer detection in chest X-ray and CT "
            "imaging. It challenges the prevailing assumption that larger models "
            "inherently produce more clinically reliable predictions."
        ),
        "discipline_type": "stem",
    }, headers=h)

    if r.status_code not in (200, 201):
        print(f"Create failed: {r.status_code} {s(r.text[:300])}")
        sys.exit(1)

    pid = r.json()["id"]
    print(f"  Project: {pid}")
    print(f"  URL: http://localhost:3000/student/projects/{pid}")
    print(f"\nMonitoring generation (this takes 15-20 minutes)...")

    start = time.time()
    last_words = 0

    for _ in range(200):
        time.sleep(15)
        elapsed = int(time.time() - start)
        mm, ss = divmod(elapsed, 60)

        try:
            r = c.get(f"{BASE}/projects/{pid}/generation-status", headers=h)
        except Exception as e:
            print(f"  [{mm:02d}:{ss:02d}] Connection error: {e}")
            continue

        if r.status_code != 200:
            print(f"  [{mm:02d}:{ss:02d}] Status: {r.status_code}")
            continue

        gs = r.json()
        words = gs.get("total_words", 0)
        gen = gs.get("generated_sections", 0)
        total = gs.get("total_sections", 0)
        delta = words - last_words
        last_words = words

        print(f"  [{mm:02d}:{ss:02d}] {gen}/{total} sections | "
              f"{words:,} words (+{delta:,})")

        if gs.get("all_generated") and words > 5000:
            print(f"\n  DONE in {mm}m {ss}s!")
            break

    # Final report
    print("\n" + "=" * 60)
    r = c.get(f"{BASE}/projects/{pid}/generation-status", headers=h)
    if r.status_code == 200:
        gs = r.json()
        for sec in gs.get("sections", []):
            mark = "+" if sec["is_generated"] else "."
            print(f"  [{mark}] {s(sec['title'])}: {sec['word_count']:,} words")
        print(f"\n  Total: {gs['total_words']:,} words")

    print(f"\n  View: http://localhost:3000/student/projects/{pid}")
    print(f"  Quality: http://localhost:3000/student/projects/{pid}/quality")

if __name__ == "__main__":
    main()
