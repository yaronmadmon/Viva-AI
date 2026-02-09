"""
Test the v2 dissertation generator -- full PhD-quality output.
Creates a new project and triggers multi-pass generation.
"""
import httpx
import json
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = "http://localhost:8000/api/v1"


def safe(s):
    return s.encode("ascii", errors="replace").decode("ascii") if s else ""


def main():
    client = httpx.Client(timeout=60)

    # Login
    print("Authenticating...")
    r = client.post(f"{BASE}/auth/login", json={
        "email": "yaronmadmon@gmail.com", "password": "Test1234!",
    })
    if r.status_code != 200:
        print(f"FAIL: {r.status_code}")
        sys.exit(1)
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    print("  OK\n")

    # Create new project for v2 test
    print("Creating new project for v2 generation...")
    r = client.post(f"{BASE}/projects", json={
        "title": "Deep Learning for Early Cancer Detection: CNN vs Transformer Architectures",
        "description": (
            "This dissertation critically evaluates CNN and vision transformer "
            "architectures for automated cancer detection in chest X-ray and CT "
            "imaging. It challenges the prevailing assumption that larger models "
            "inherently produce more clinically reliable predictions, investigating "
            "the trade-offs between raw accuracy, interpretability, and calibration "
            "in safety-critical medical deployment contexts."
        ),
        "discipline_type": "stem",
    }, headers=h)

    if r.status_code not in (200, 201):
        print(f"FAIL create: {r.status_code} {safe(r.text[:300])}")
        sys.exit(1)

    pid = r.json()["id"]
    print(f"  Project ID: {pid}")
    print("  Generation triggered automatically (v2 multi-pass pipeline)")

    # Poll for generation (this takes 15-30 min for full PhD)
    print("\nPolling generation status...")
    print("  (v2 generates 25+ subsections with targeted paper search)")
    print("  (Expected: 50,000+ words, 100+ papers, 15-30 minutes)\n")

    start_time = time.time()
    last_words = 0

    for i in range(180):  # up to 30 minutes
        time.sleep(10)
        elapsed = int(time.time() - start_time)
        mins = elapsed // 60
        secs = elapsed % 60

        r = client.get(f"{BASE}/projects/{pid}/generation-status", headers=h)
        if r.status_code != 200:
            print(f"  [{mins:02d}:{secs:02d}] Status error: {r.status_code}")
            continue

        gs = r.json()
        gen = gs.get("generated_sections", 0)
        total = gs.get("total_sections", 0)
        words = gs.get("total_words", 0)
        new_words = words - last_words
        last_words = words

        print(f"  [{mins:02d}:{secs:02d}] {gen}/{total} sections | "
              f"{words:,} words (+{new_words:,})")

        # Show per-section detail
        for s in gs.get("sections", []):
            mark = "+" if s["is_generated"] else "."
            print(f"    [{mark}] {safe(s['title'])}: {s['word_count']:,} words")

        if gs.get("all_generated"):
            print(f"\n  ALL SECTIONS GENERATED in {mins}m {secs}s!")
            break
    else:
        elapsed = int(time.time() - start_time)
        print(f"\n  Timeout after {elapsed // 60}m — continuing with current state")

    # Fetch and summarize
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    r = client.get(f"{BASE}/projects/{pid}/generation-status", headers=h)
    if r.status_code == 200:
        gs = r.json()
        print(f"  Total words: {gs['total_words']:,}")
        print(f"  Generated sections: {gs['generated_sections']}/{gs['total_sections']}")
        for s in gs.get("sections", []):
            mark = "DONE" if s["is_generated"] else "pending"
            print(f"    [{mark}] {safe(s['title'])}: {s['word_count']:,} words")

    # Fetch actual content preview
    r = client.get(f"{BASE}/projects/{pid}/document", headers=h)
    if r.status_code == 200:
        doc = r.json()
        print(f"\n  Document sections: {len(doc.get('artifacts', []))}")
        total = 0
        for art in doc.get("artifacts", []):
            content = art.get("content", "")
            wc = len(content.split())
            total += wc
            # Check for student markers
            student_markers = content.count("<!-- STUDENT:")
            marker_text = f" [{student_markers} student input markers]" if student_markers else ""
            print(f"    {safe(art['title'])}: {wc:,} words{marker_text}")
            # Preview
            preview = safe(content[:200].replace("\n", " "))
            print(f"      {preview}...")
        print(f"\n  TOTAL CONTENT: {total:,} words")

    # Run quality report
    print("\n" + "=" * 60)
    print("QUALITY REPORT")
    print("=" * 60)
    r = client.get(f"{BASE}/projects/{pid}/quality/full-report", headers=h, timeout=120)
    if r.status_code == 200:
        d = r.json()
        print(f"  Overall Score: {d['overall_score']}/100")
        print(f"  Passed: {d['passed']}")
        print(f"  Summary: {safe(d.get('summary', ''))}")

    print(f"\n  Project ID: {pid}")
    print(f"  View in browser: http://localhost:3000/student/projects/{pid}")
    print(f"  Quality report: http://localhost:3000/student/projects/{pid}/quality")

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
