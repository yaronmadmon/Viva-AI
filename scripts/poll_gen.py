"""Poll generation status until complete."""
import sys, time
sys.path.insert(0, ".")
import httpx

BASE = "http://localhost:8000/api/v1"
r = httpx.post(BASE + "/auth/login", json={"email": "yaronmadmon@gmail.com", "password": "Test1234!"}, timeout=10)
token = r.json()["access_token"]
h = {"Authorization": "Bearer " + token}
pid = "395d1dae-6348-4bac-8a8b-92c84c39f1ed"

for i in range(18):
    time.sleep(10)
    r = httpx.get(BASE + "/projects/" + pid + "/generation-status", headers=h, timeout=10)
    gs = r.json()
    gen = gs["generated_sections"]
    total = gs["total_sections"]
    words = gs["total_words"]
    pct = round(gen / total * 100) if total else 0
    print(f"Poll {i+1}: {gen}/{total} sections ({pct}%), {words} words total")
    for s in gs["sections"]:
        mark = "Y" if s["is_generated"] else "."
        print(f"  [{mark}] {s['title']}: {s['word_count']}w")
    if gs["all_generated"]:
        print("\nALL SECTIONS GENERATED!")
        # Show preview
        r = httpx.get(BASE + "/projects/" + pid + "/document", headers=h, timeout=10)
        doc = r.json()
        for art in doc["artifacts"][:2]:
            wc = len(art["content"].split())
            print(f"\n{'='*60}")
            print(f"  {art['title']} ({wc} words)")
            print(f"{'='*60}")
            print(art["content"][:1000])
            if len(art["content"]) > 1000:
                print("\n  [...truncated...]")
        break
