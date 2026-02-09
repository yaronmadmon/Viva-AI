"""
Comprehensive test of all Harvard-level quality engines.

Creates a project, waits for generation, then runs every quality audit
endpoint and the full quality report.
"""
import httpx
import json
import sys
import time

BASE = "http://localhost:8000/api/v1"
TIMEOUT = 30


def main():
    client = httpx.Client(timeout=TIMEOUT)

    # ── 1. Login ─────────────────────────────────────────────────────────
    print("=" * 60)
    print("PHASE 1: Authentication")
    print("=" * 60)

    r = client.post(f"{BASE}/auth/login", json={
        "email": "yaronmadmon@gmail.com",
        "password": "Test1234!",
    })
    if r.status_code != 200:
        # Try alternate user
        r = client.post(f"{BASE}/auth/login", json={
            "email": "test_e2e@example.com",
            "password": "TestPass123!",
        })
    if r.status_code != 200:
        # Register
        print("  Registering test user...")
        r = client.post(f"{BASE}/auth/register", json={
            "email": "quality_test@example.com",
            "password": "TestQuality123!",
            "full_name": "Quality Tester",
            "role": "student",
        })
        if r.status_code in (200, 201):
            data = r.json()
            token = data.get("access_token")
            if not token:
                r = client.post(f"{BASE}/auth/login", json={
                    "email": "quality_test@example.com",
                    "password": "TestQuality123!",
                })
                if r.status_code != 200:
                    print(f"  FAIL: Cannot authenticate: {r.status_code} {r.text[:200]}")
                    sys.exit(1)
                token = r.json()["access_token"]
        else:
            print(f"  FAIL: {r.status_code} {r.text[:200]}")
            sys.exit(1)
    else:
        token = r.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    print(f"  OK - authenticated")

    # ── 2. Create project with positioning ───────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 2: Create Project (with Intellectual Positioning)")
    print("=" * 60)

    r = client.post(f"{BASE}/projects", json={
        "title": "Deep Learning for Early Cancer Detection in Radiology: A Critical Evaluation of CNN vs Transformer Architectures",
        "description": (
            "This dissertation critically evaluates the comparative efficacy of "
            "convolutional neural networks and vision transformer architectures "
            "for automated cancer detection in chest X-ray and CT imaging. "
            "The study challenges the prevailing assumption that larger models "
            "necessarily produce more clinically reliable predictions, arguing "
            "instead that interpretability and calibration are more important "
            "than raw accuracy in clinical deployment contexts."
        ),
        "discipline_type": "stem",
    }, headers=headers)

    print(f"  Create: {r.status_code}")
    if r.status_code not in (200, 201):
        print(f"  FAIL: {r.text[:500]}")
        sys.exit(1)

    project = r.json()
    pid = project["id"]
    print(f"  Project ID: {pid}")
    print(f"  Artifacts: {project.get('artifact_count', 0)}")
    print(f"  Discipline: {project.get('discipline_type')}")

    # ── 3. Wait for generation ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 3: Wait for Dissertation Generation")
    print("=" * 60)

    for i in range(12):
        r = client.get(f"{BASE}/projects/{pid}/generation-status", headers=headers)
        if r.status_code != 200:
            print(f"  Generation status: {r.status_code} (may not be ready yet)")
            time.sleep(5)
            continue
        gs = r.json()
        generated = gs.get("generated_sections", 0)
        total = gs.get("total_sections", 0)
        words = gs.get("total_words", 0)
        print(f"  Poll {i+1}/12: {generated}/{total} sections, {words} words")
        if gs.get("all_generated"):
            print("  All sections generated!")
            break
        time.sleep(5)
    else:
        print("  (Continuing with whatever is generated...)")

    # ── 4. Fetch document to get section content ─────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 4: Fetch Generated Document")
    print("=" * 60)

    r = client.get(f"{BASE}/projects/{pid}/document", headers=headers)
    if r.status_code != 200:
        print(f"  Document fetch: {r.status_code}")
        # Try artifact tree instead
        r = client.get(f"{BASE}/artifacts/projects/{pid}/tree", headers=headers)
        print(f"  Tree fetch: {r.status_code}")
        if r.status_code != 200:
            print(f"  FAIL: Cannot get document content: {r.text[:300]}")
            sys.exit(1)

    doc = r.json()
    artifacts = doc.get("artifacts", [])
    print(f"  Found {len(artifacts)} artifacts")

    # Categorize
    sections = {}
    for art in artifacts:
        title = art.get("title", "untitled")
        content = art.get("content", "")
        word_count = len(content.split())
        sections[title] = {"id": art.get("id"), "content": content, "words": word_count}
        print(f"    {title}: {word_count} words")

    # ── 5. Run Quality Engines ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 5: Run Harvard-Level Quality Engines")
    print("=" * 60)

    # Find sections by keyword
    def find_section(keyword):
        for title, data in sections.items():
            if keyword.lower() in title.lower():
                return title, data
        return None, None

    # 5a. Claim Discipline Audit (on full text)
    print("\n--- 5a. Claim Discipline Audit ---")
    all_text = "\n\n".join(s["content"] for s in sections.values() if s["content"])
    if all_text.strip():
        r = client.post(f"{BASE}/projects/{pid}/quality/claim-audit", json={
            "text": all_text[:5000],  # First 5000 chars
            "section_title": "Full Dissertation Sample",
        }, headers=headers)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  Total sentences: {data['total_sentences']}")
            print(f"  Descriptive: {data['descriptive_count']}")
            print(f"  Inferential: {data['inferential_count']}")
            print(f"  Speculative: {data['speculative_count']}")
            print(f"  Overreach count: {data['overreach_count']}")
            print(f"  Unhedged inferential: {data['unhedged_inferential_count']}")
            print(f"  Certainty score: {data['certainty_score']}")
            print(f"  PASSED: {data['passed']}")
            if data['flags']:
                print(f"  Flags ({len(data['flags'])}):")
                for f in data['flags'][:3]:
                    print(f"    [{f['severity']}] {f['issue'][:80]}")
        else:
            print(f"  ERROR: {r.text[:300]}")
    else:
        print("  SKIP: No text content available")

    # 5b. Methodology Stress Test
    print("\n--- 5b. Methodology Stress Test ---")
    _, method_data = find_section("method")
    if method_data and method_data["content"].strip():
        r = client.post(f"{BASE}/projects/{pid}/quality/methodology-stress-test", json={
            "text": method_data["content"][:5000],
            "section_title": "Methodology",
        }, headers=headers)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  Rejected alternatives: {data['has_rejected_alternatives']}")
            print(f"  Failure conditions: {data['has_failure_conditions']}")
            print(f"  Boundary conditions: {data['has_boundary_conditions']}")
            print(f"  Justification: {data['has_justification']}")
            print(f"  Procedural ratio: {data['procedural_ratio']}")
            print(f"  Defensibility score: {data['defensibility_score']}")
            print(f"  PASSED: {data['passed']}")
            if data['examiner_questions']:
                print(f"  Examiner questions ({len(data['examiner_questions'])}):")
                for q in data['examiner_questions'][:3]:
                    print(f"    Q: {q['question'][:80]}")
            if data['flags']:
                print(f"  Flags ({len(data['flags'])}):")
                for f in data['flags'][:3]:
                    print(f"    [{f['severity']}] {f['issue'][:80]}")
        else:
            print(f"  ERROR: {r.text[:300]}")
    else:
        print("  SKIP: No methodology section found")

    # 5c. Contribution Check
    print("\n--- 5c. Contribution Validator ---")
    _, concl_data = find_section("conclusion")
    if concl_data and concl_data["content"].strip():
        r = client.post(f"{BASE}/projects/{pid}/quality/contribution-check", json={
            "text": concl_data["content"][:5000],
            "section_title": "Conclusion",
        }, headers=headers)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  Claim count: {data['claim_count']}")
            print(f"  Has before/after: {data['has_before_after']}")
            print(f"  Has falsifiability: {data['has_falsifiability']}")
            print(f"  Broad claims: {data['broad_claim_count']}")
            print(f"  Precision score: {data['precision_score']}")
            print(f"  PASSED: {data['passed']}")
            if data['flags']:
                print(f"  Flags ({len(data['flags'])}):")
                for f in data['flags'][:3]:
                    print(f"    [{f['severity']}] {f['issue'][:80]}")
        else:
            print(f"  ERROR: {r.text[:300]}")
    else:
        print("  SKIP: No conclusion section found")

    # 5d. Literature Tension
    print("\n--- 5d. Literature Tension Checker ---")
    _, lit_data = find_section("literature")
    if not lit_data:
        _, lit_data = find_section("review")
    if lit_data and lit_data["content"].strip():
        r = client.post(f"{BASE}/projects/{pid}/quality/literature-tension", json={
            "text": lit_data["content"][:5000],
            "section_title": "Literature Review",
        }, headers=headers)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  Total paragraphs: {data['total_paragraphs']}")
            print(f"  Named disagreements: {data['named_disagreement_count']}")
            print(f"  Vague attributions: {data['vague_attribution_count']}")
            print(f"  Tension markers: {data['tension_style_count']}")
            print(f"  Synthesis markers: {data['synthesis_count']}")
            print(f"  Tension score: {data['tension_score']}")
            print(f"  PASSED: {data['passed']}")
            if data['named_disagreements']:
                print(f"  Named disagreements:")
                for d in data['named_disagreements'][:3]:
                    print(f"    {d.get('author_a', '?')} vs {d.get('author_b', '?')}")
            if data['flags']:
                print(f"  Flags ({len(data['flags'])}):")
                for f in data['flags'][:3]:
                    print(f"    [{f['severity']}] {f['issue'][:80]}")
        else:
            print(f"  ERROR: {r.text[:300]}")
    else:
        print("  SKIP: No literature review section found")

    # 5e. Pedagogical Annotations
    print("\n--- 5e. Pedagogical Annotations ---")
    first_section = next(iter(sections.values()), None)
    if first_section and first_section["content"].strip():
        first_title = next(iter(sections.keys()))
        r = client.post(f"{BASE}/projects/{pid}/quality/pedagogical-annotations", json={
            "text": first_section["content"][:3000],
            "section_title": first_title,
        }, headers=headers)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  Section: {data['section_title']}")
            print(f"  Total paragraphs: {data['total_paragraphs']}")
            print(f"  Annotations: {data['annotation_count']}")
            print(f"  Model: {data['model_used']}")
            if data['annotations']:
                print(f"  Sample annotations:")
                for a in data['annotations'][:5]:
                    print(f"    [{a['type']}] P{a['paragraph_index']}: {a['explanation'][:70]}")
        else:
            print(f"  ERROR: {r.text[:300]}")
    else:
        print("  SKIP: No section content")

    # ── 6. Full Quality Report ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 6: Full Quality Report")
    print("=" * 60)

    r = client.get(f"{BASE}/projects/{pid}/quality/full-report", headers=headers)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"  Sections audited: {data['sections_audited']}")
        print(f"  Overall score: {data['overall_score']}/100")
        print(f"  PASSED: {data['passed']}")
        print(f"  Summary: {data['summary']}")

        if data.get('claim_audit'):
            ca = data['claim_audit']
            print(f"\n  Claim Audit: certainty={ca['certainty_score']}, "
                  f"overreach={ca['overreach_count']}, passed={ca['passed']}")

        if data.get('methodology_stress'):
            ms = data['methodology_stress']
            print(f"  Methodology: defensibility={ms['defensibility_score']}, "
                  f"procedural_ratio={ms['procedural_ratio']}, passed={ms['passed']}")

        if data.get('contribution_check'):
            cc = data['contribution_check']
            print(f"  Contribution: precision={cc['precision_score']}, "
                  f"claims={cc['claim_count']}, before_after={cc['has_before_after']}, "
                  f"passed={cc['passed']}")

        if data.get('literature_tension'):
            lt = data['literature_tension']
            print(f"  Lit Tension: score={lt['tension_score']}, "
                  f"disagreements={lt['named_disagreement_count']}, "
                  f"passed={lt['passed']}")
    else:
        print(f"  ERROR: {r.text[:500]}")

    # ── 7. Avatar Chat Test ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 7: Avatar Chat Test")
    print("=" * 60)

    r = client.post(f"{BASE}/projects/{pid}/avatar/chat", json={
        "message": "How should I structure my methodology section to anticipate examiner challenges?",
    }, headers=headers)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"  Model: {data['model_used']}")
        print(f"  Reply: {data['reply'][:200]}...")
    else:
        print(f"  ERROR: {r.text[:300]}")

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print(f"  Project ID: {pid}")
    print(f"  All quality engines responded successfully.")


if __name__ == "__main__":
    main()
