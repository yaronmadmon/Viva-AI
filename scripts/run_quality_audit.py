"""
Run quality audit on an already-generated project.
Skips generation (data is already in DB from OpenAI).
"""
import httpx
import json
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = "http://localhost:8000/api/v1"
PID = "5bfe7e0d-465e-4cbb-afea-7a751e124986"


def safe(s):
    """Strip non-ASCII for safe console printing."""
    return s.encode("ascii", errors="replace").decode("ascii") if s else ""


def main():
    client = httpx.Client(timeout=60)

    # Login
    print("Authenticating...")
    r = client.post(f"{BASE}/auth/login", json={
        "email": "yaronmadmon@gmail.com", "password": "Test1234!",
    })
    if r.status_code != 200:
        print(f"FAIL login: {r.status_code} {r.text[:200]}")
        sys.exit(1)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  OK\n")

    # Check generation status
    print("=" * 60)
    print("GENERATION STATUS")
    print("=" * 60)
    r = client.get(f"{BASE}/projects/{PID}/generation-status", headers=headers)
    if r.status_code != 200:
        print(f"FAIL: {r.status_code}")
        sys.exit(1)
    gs = r.json()
    print(f"  Total words: {gs['total_words']}")
    print(f"  Sections: {gs['generated_sections']}/{gs['total_sections']}")
    for s in gs.get("sections", []):
        mark = "+" if s["is_generated"] else "-"
        print(f"    [{mark}] {safe(s['title'])}: {s['word_count']} words")

    # Fetch document
    print("\n" + "=" * 60)
    print("FETCHING DOCUMENT")
    print("=" * 60)
    r = client.get(f"{BASE}/projects/{PID}/document", headers=headers)
    if r.status_code != 200:
        print(f"FAIL: {r.status_code}")
        sys.exit(1)

    doc = r.json()
    artifacts = doc.get("artifacts", [])
    sections = {}
    total_words = 0
    for art in artifacts:
        content = art.get("content", "")
        wc = len(content.split())
        total_words += wc
        title = art.get("title", "untitled")
        sections[title] = content
        preview = safe(content[:150].replace("\n", " "))
        print(f"  {safe(title)}: {wc} words")
        print(f"    {preview}...")

    print(f"\n  TOTAL: {total_words} words across {len(artifacts)} sections")

    def find_section(keyword):
        for t, c in sections.items():
            if keyword.lower() in t.lower():
                return c
        return ""

    # === Quality Engines ===
    print("\n" + "=" * 60)
    print("QUALITY AUDIT (Harvard-level engines)")
    print("=" * 60)

    # 1. Claim Discipline Audit
    all_text = "\n\n".join(sections.values())
    print("\n--- 1. CLAIM DISCIPLINE AUDIT ---")
    r = client.post(f"{BASE}/projects/{PID}/quality/claim-audit", json={
        "text": all_text[:8000],
        "section_title": "Full Dissertation",
    }, headers=headers, timeout=120)
    if r.status_code == 200:
        d = r.json()
        print(f"  Total sentences: {d['total_sentences']}")
        print(f"  Descriptive:     {d['descriptive_count']}")
        print(f"  Inferential:     {d['inferential_count']}")
        print(f"  Speculative:     {d['speculative_count']}")
        print(f"  Overreach:       {d['overreach_count']}")
        print(f"  Unhedged infer:  {d['unhedged_inferential_count']}")
        print(f"  Certainty Score: {d['certainty_score']}/100")
        print(f"  PASSED:          {d['passed']}")
        if d.get("flags"):
            print(f"  Flags ({len(d['flags'])} total):")
            for f in d['flags'][:5]:
                print(f"    [{f['severity']}] {safe(f['issue'][:100])}")
    else:
        print(f"  ERROR: {r.status_code} - {safe(r.text[:200])}")

    # 2. Methodology Stress Test
    meth = find_section("method")
    print("\n--- 2. METHODOLOGY STRESS TEST ---")
    if meth:
        r = client.post(f"{BASE}/projects/{PID}/quality/methodology-stress-test", json={
            "text": meth[:8000], "section_title": "Methodology",
        }, headers=headers, timeout=120)
        if r.status_code == 200:
            d = r.json()
            print(f"  Rejected alternatives: {d['has_rejected_alternatives']}")
            print(f"  Failure conditions:    {d['has_failure_conditions']}")
            print(f"  Boundary conditions:   {d['has_boundary_conditions']}")
            print(f"  Justification:         {d['has_justification']}")
            print(f"  Defensibility Score:   {d['defensibility_score']}/100")
            print(f"  PASSED:                {d['passed']}")
            if d.get("examiner_questions"):
                print(f"  Examiner Questions ({len(d['examiner_questions'])}):")
                for q in d['examiner_questions'][:5]:
                    print(f"    Q: {safe(q.get('question', '')[:100])}")
        else:
            print(f"  ERROR: {r.status_code} - {safe(r.text[:200])}")
    else:
        print("  (No methodology section found)")

    # 3. Contribution Validator
    concl = find_section("conclusion")
    print("\n--- 3. CONTRIBUTION VALIDATOR ---")
    if concl:
        r = client.post(f"{BASE}/projects/{PID}/quality/contribution-check", json={
            "text": concl[:8000], "section_title": "Conclusion",
        }, headers=headers, timeout=120)
        if r.status_code == 200:
            d = r.json()
            print(f"  Claim count:     {d['claim_count']}")
            print(f"  Before/After:    {d['has_before_after']}")
            print(f"  Falsifiability:  {d['has_falsifiability']}")
            print(f"  Broad claims:    {d['broad_claim_count']}")
            print(f"  Precision Score: {d['precision_score']}/100")
            print(f"  PASSED:          {d['passed']}")
        else:
            print(f"  ERROR: {r.status_code} - {safe(r.text[:200])}")
    else:
        print("  (No conclusion section found)")

    # 4. Literature Tension
    lit = find_section("literature") or find_section("review")
    print("\n--- 4. LITERATURE TENSION CHECKER ---")
    if lit:
        r = client.post(f"{BASE}/projects/{PID}/quality/literature-tension", json={
            "text": lit[:8000], "section_title": "Literature Review",
        }, headers=headers, timeout=120)
        if r.status_code == 200:
            d = r.json()
            print(f"  Named disagreements:   {d['named_disagreement_count']}")
            print(f"  Vague attributions:    {d['vague_attribution_count']}")
            print(f"  Tension Score:         {d['tension_score']}/100")
            print(f"  PASSED:                {d['passed']}")
            if d.get("named_disagreements"):
                print(f"  Disagreements found:")
                for nd in d['named_disagreements'][:5]:
                    a = safe(nd.get('author_a', '?'))
                    b = safe(nd.get('author_b', '?'))
                    print(f"    {a} vs {b}")
        else:
            print(f"  ERROR: {r.status_code} - {safe(r.text[:200])}")
    else:
        print("  (No literature review section found)")

    # 5. Pedagogical Annotations
    intro = find_section("introduction")
    print("\n--- 5. PEDAGOGICAL ANNOTATOR ---")
    if intro:
        r = client.post(f"{BASE}/projects/{PID}/quality/pedagogical-annotations", json={
            "text": intro[:4000], "section_title": "Introduction",
        }, headers=headers, timeout=120)
        if r.status_code == 200:
            d = r.json()
            print(f"  Total annotations: {d['annotation_count']}")
            if d.get("annotations"):
                for ann in d['annotations'][:5]:
                    print(f"    [{safe(ann.get('annotation_type', ''))}] {safe(ann.get('annotation', '')[:80])}")
        else:
            print(f"  ERROR: {r.status_code} - {safe(r.text[:200])}")
    else:
        print("  (No introduction section found)")

    # 6. Full Quality Report
    print("\n--- 6. FULL QUALITY REPORT ---")
    r = client.get(f"{BASE}/projects/{PID}/quality/full-report", headers=headers, timeout=120)
    if r.status_code == 200:
        d = r.json()
        print(f"  Overall Score: {d['overall_score']}/100")
        print(f"  PASSED:        {d['passed']}")
        print(f"  Summary:       {safe(d.get('summary', ''))}")

        # Sub-scores
        for key in ["claim_discipline", "methodology_defensibility", "contribution_precision", "literature_tension"]:
            if key in d:
                sub = d[key]
                if isinstance(sub, dict):
                    score = sub.get("score", sub.get("certainty_score", sub.get("precision_score", sub.get("tension_score", sub.get("defensibility_score", "?")))))
                    passed = sub.get("passed", "?")
                    print(f"    {key}: score={score}, passed={passed}")
    else:
        print(f"  ERROR: {r.status_code} - {safe(r.text[:200])}")

    # 7. Avatar Chat (bonus)
    print("\n--- 7. AVATAR CHAT ---")
    r = client.post(f"{BASE}/projects/{PID}/avatar/chat", json={
        "message": "What are the main strengths and weaknesses of my methodology section?",
    }, headers=headers, timeout=120)
    if r.status_code == 200:
        d = r.json()
        print(f"  Model: {d.get('model_used', 'unknown')}")
        print(f"  Reply: {safe(d.get('reply', '')[:300])}")
    else:
        print(f"  ERROR: {r.status_code} - {safe(r.text[:200])}")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
