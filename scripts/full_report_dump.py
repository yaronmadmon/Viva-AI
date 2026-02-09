"""Dump the complete quality report and all engine outputs as formatted JSON."""
import httpx
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = "http://localhost:8000/api/v1"
PID = "5bfe7e0d-465e-4cbb-afea-7a751e124986"


def main():
    client = httpx.Client(timeout=120)

    # Login
    r = client.post(f"{BASE}/auth/login", json={
        "email": "yaronmadmon@gmail.com", "password": "Test1234!",
    })
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # Fetch document sections
    r = client.get(f"{BASE}/projects/{PID}/document", headers=h)
    doc = r.json()
    sections = {}
    for art in doc.get("artifacts", []):
        sections[art["title"]] = art.get("content", "")

    def find(kw):
        for t, c in sections.items():
            if kw.lower() in t.lower():
                return c
        return ""

    all_text = "\n\n".join(sections.values())

    print("=" * 70)
    print("  VIVA AI — FULL HARVARD-LEVEL QUALITY REPORT")
    print("  Project: Deep Learning for Early Cancer Detection")
    print("=" * 70)

    # 1
    print("\n\n" + "=" * 70)
    print("  1. CLAIM DISCIPLINE AUDIT")
    print("=" * 70)
    r = client.post(f"{BASE}/projects/{PID}/quality/claim-audit", json={
        "text": all_text[:8000], "section_title": "Full Dissertation",
    }, headers=h)
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))

    # 2
    print("\n\n" + "=" * 70)
    print("  2. METHODOLOGY STRESS TEST")
    print("=" * 70)
    r = client.post(f"{BASE}/projects/{PID}/quality/methodology-stress-test", json={
        "text": find("method")[:8000], "section_title": "Methodology",
    }, headers=h)
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))

    # 3
    print("\n\n" + "=" * 70)
    print("  3. CONTRIBUTION VALIDATOR")
    print("=" * 70)
    r = client.post(f"{BASE}/projects/{PID}/quality/contribution-check", json={
        "text": find("conclusion")[:8000], "section_title": "Conclusion",
    }, headers=h)
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))

    # 4
    print("\n\n" + "=" * 70)
    print("  4. LITERATURE TENSION CHECKER")
    print("=" * 70)
    r = client.post(f"{BASE}/projects/{PID}/quality/literature-tension", json={
        "text": find("literature")[:8000], "section_title": "Literature Review",
    }, headers=h)
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))

    # 5
    print("\n\n" + "=" * 70)
    print("  5. PEDAGOGICAL ANNOTATIONS")
    print("=" * 70)
    r = client.post(f"{BASE}/projects/{PID}/quality/pedagogical-annotations", json={
        "text": find("introduction")[:4000], "section_title": "Introduction",
    }, headers=h)
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))

    # 6
    print("\n\n" + "=" * 70)
    print("  6. FULL QUALITY REPORT (aggregated)")
    print("=" * 70)
    r = client.get(f"{BASE}/projects/{PID}/quality/full-report", headers=h)
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print("  END OF REPORT")
    print("=" * 70)


if __name__ == "__main__":
    main()
