"""
Full test: trigger generation with OpenAI, wait for completion, run quality audit.
Uses the existing project or creates a new one.
"""
import httpx
import json
import sys
import time
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = "http://localhost:8000/api/v1"


def main():
    client = httpx.Client(timeout=30)

    # Login
    print("Authenticating...")
    r = client.post(f"{BASE}/auth/login", json={
        "email": "yaronmadmon@gmail.com", "password": "Test1234!",
    })
    if r.status_code != 200:
        r = client.post(f"{BASE}/auth/login", json={
            "email": "test_e2e@example.com", "password": "TestPass123!",
        })
    if r.status_code != 200:
        print(f"FAIL login: {r.status_code}")
        sys.exit(1)

    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  OK")

    # Use the project we created earlier, or create a new one
    pid = "5bfe7e0d-465e-4cbb-afea-7a751e124986"

    # Check if it exists
    r = client.get(f"{BASE}/projects/{pid}", headers=headers)
    if r.status_code != 200:
        print("Previous project not found, creating new one...")
        r = client.post(f"{BASE}/projects", json={
            "title": "Deep Learning for Early Cancer Detection: CNN vs Transformer Architectures",
            "description": (
                "This dissertation critically evaluates CNN and vision transformer "
                "architectures for automated cancer detection in chest X-ray and CT "
                "imaging, challenging the assumption that larger models produce more "
                "clinically reliable predictions."
            ),
            "discipline_type": "stem",
        }, headers=headers)
        if r.status_code not in (200, 201):
            print(f"FAIL create: {r.text[:300]}")
            sys.exit(1)
        pid = r.json()["id"]
        print(f"  Created: {pid}")
        # Wait a moment for scaffold
        time.sleep(2)

    print(f"\nProject: {pid}")

    # Trigger explicit generation
    print("\nTriggering AI generation (OpenAI + real papers)...")
    r = client.post(f"{BASE}/projects/{pid}/generate", headers=headers)
    print(f"  Trigger: {r.status_code} - {r.json().get('message', '')}")

    # Poll for generation
    print("\nWaiting for generation (this takes 1-3 minutes with OpenAI)...")
    for i in range(30):
        time.sleep(10)
        r = client.get(f"{BASE}/projects/{pid}/generation-status", headers=headers)
        if r.status_code != 200:
            print(f"  Poll {i+1}: status error {r.status_code}")
            continue
        gs = r.json()
        gen = gs.get("generated_sections", 0)
        total = gs.get("total_sections", 0)
        words = gs.get("total_words", 0)
        print(f"  Poll {i+1}/30: {gen}/{total} sections, {words} total words")

        # Show per-section status
        for s in gs.get("sections", []):
            mark = "+" if s["is_generated"] else "-"
            print(f"    [{mark}] {s['title']}: {s['word_count']} words")

        if gs.get("all_generated"):
            print("\n  ALL SECTIONS GENERATED!")
            break
    else:
        print("\n  Timeout -- continuing with whatever was generated")

    # Fetch document
    print("\n" + "=" * 60)
    print("FETCHING GENERATED DOCUMENT")
    print("=" * 60)
    r = client.get(f"{BASE}/projects/{pid}/document", headers=headers)
    if r.status_code != 200:
        print(f"FAIL: {r.status_code}")
        sys.exit(1)

    doc = r.json()
    artifacts = doc.get("artifacts", [])
    total_words = 0
    sections = {}
    for art in artifacts:
        content = art.get("content", "")
        wc = len(content.split())
        total_words += wc
        title = art.get("title", "untitled")
        sections[title] = content
        print(f"  {title}: {wc} words")
        # Preview first 200 chars
        preview = content[:200].replace("\n", " ")
        print(f"    Preview: {preview}...")

    print(f"\n  TOTAL: {total_words} words across {len(artifacts)} sections")

    # Run quality engines
    print("\n" + "=" * 60)
    print("RUNNING QUALITY AUDIT")
    print("=" * 60)

    def find_section(keyword):
        for t, c in sections.items():
            if keyword.lower() in t.lower():
                return c
        return ""

    # 1. Claim audit on full text
    all_text = "\n\n".join(sections.values())
    print("\n--- Claim Discipline Audit ---")
    r = client.post(f"{BASE}/projects/{pid}/quality/claim-audit", json={
        "text": all_text[:8000],
        "section_title": "Full Dissertation",
    }, headers=headers)
    if r.status_code == 200:
        d = r.json()
        print(f"  Sentences: {d['total_sentences']}")
        print(f"  Descriptive: {d['descriptive_count']} | Inferential: {d['inferential_count']} | Speculative: {d['speculative_count']}")
        print(f"  Overreach: {d['overreach_count']} | Unhedged: {d['unhedged_inferential_count']}")
        print(f"  Certainty Score: {d['certainty_score']} | PASSED: {d['passed']}")
        for f in d['flags'][:5]:
            print(f"    [{f['severity']}] {f['issue'][:80]}")
    else:
        print(f"  ERROR: {r.status_code}")

    # 2. Methodology
    meth = find_section("method")
    print("\n--- Methodology Stress Test ---")
    if meth:
        r = client.post(f"{BASE}/projects/{pid}/quality/methodology-stress-test", json={
            "text": meth[:8000], "section_title": "Methodology",
        }, headers=headers)
        if r.status_code == 200:
            d = r.json()
            print(f"  Rejected alternatives: {d['has_rejected_alternatives']}")
            print(f"  Failure conditions: {d['has_failure_conditions']}")
            print(f"  Boundary conditions: {d['has_boundary_conditions']}")
            print(f"  Justification: {d['has_justification']}")
            print(f"  Defensibility: {d['defensibility_score']} | PASSED: {d['passed']}")
            for q in d['examiner_questions'][:3]:
                print(f"    Q: {q['question'][:80]}")
    else:
        print("  No methodology section")

    # 3. Contribution
    concl = find_section("conclusion")
    print("\n--- Contribution Validator ---")
    if concl:
        r = client.post(f"{BASE}/projects/{pid}/quality/contribution-check", json={
            "text": concl[:8000], "section_title": "Conclusion",
        }, headers=headers)
        if r.status_code == 200:
            d = r.json()
            print(f"  Claims: {d['claim_count']} | Before/After: {d['has_before_after']}")
            print(f"  Falsifiability: {d['has_falsifiability']} | Broad: {d['broad_claim_count']}")
            print(f"  Precision: {d['precision_score']} | PASSED: {d['passed']}")
    else:
        print("  No conclusion section")

    # 4. Literature tension
    lit = find_section("literature") or find_section("review")
    print("\n--- Literature Tension ---")
    if lit:
        r = client.post(f"{BASE}/projects/{pid}/quality/literature-tension", json={
            "text": lit[:8000], "section_title": "Literature Review",
        }, headers=headers)
        if r.status_code == 200:
            d = r.json()
            print(f"  Named disagreements: {d['named_disagreement_count']}")
            print(f"  Vague attributions: {d['vague_attribution_count']}")
            print(f"  Tension score: {d['tension_score']} | PASSED: {d['passed']}")
            for nd in d['named_disagreements'][:3]:
                print(f"    {nd.get('author_a', '?')} vs {nd.get('author_b', '?')}")
    else:
        print("  No lit review section")

    # 5. Full report
    print("\n--- Full Quality Report ---")
    r = client.get(f"{BASE}/projects/{pid}/quality/full-report", headers=headers)
    if r.status_code == 200:
        d = r.json()
        print(f"  Overall Score: {d['overall_score']}/100")
        print(f"  PASSED: {d['passed']}")
        print(f"  Summary: {d['summary']}")

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
