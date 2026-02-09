"""Retroactively add scaffold sections to existing projects that don't have them."""
import sqlite3, hashlib, uuid

conn = sqlite3.connect("viva_dev.db")
c = conn.cursor()

project_id = "9b60ab9c2d4c4d0b9453de7aa54f978e"
user_id = "73011e241f93469fb5dc92a0430266af"

# Check what artifacts already exist
c.execute("SELECT id, artifact_type, title FROM artifacts WHERE project_id=? AND deleted_at IS NULL", (project_id,))
existing = c.fetchall()
print(f"Existing artifacts: {len(existing)}")
for a in existing:
    print(f"  {a}")

# Check if scaffold already exists
scaffold_titles = {"Introduction", "Literature Review", "Methodology", "Results / Analysis", "Discussion", "Conclusion", "References"}
has_scaffold = any(a[2] in scaffold_titles for a in existing if a[2])
if has_scaffold:
    print("Scaffold already exists, skipping")
else:
    print("Adding scaffold sections...")

    sections = [
        ("Introduction", "section", "Introduce the research problem, questions, and objectives."),
        ("Literature Review", "section", "Review existing work and identify the gap your research addresses."),
        ("Methodology", "method", "Describe your research approach, methods, and data sources."),
        ("Results / Analysis", "result", "Present your findings or analysis."),
        ("Discussion", "discussion", "Interpret results, discuss implications, and compare with prior work."),
        ("Conclusion", "section", "Summarize key contributions, limitations, and future directions."),
        ("References", "source", "List all cited sources."),
    ]

    c.execute("SELECT COALESCE(MAX(position),0) FROM artifacts WHERE project_id=? AND deleted_at IS NULL", (project_id,))
    max_pos = c.fetchone()[0] or 0

    for i, (title, artifact_type, placeholder) in enumerate(sections):
        art_id = uuid.uuid4().hex
        content_hash = hashlib.sha256(placeholder.encode()).hexdigest()
        position = max_pos + i + 1

        c.execute(
            """INSERT INTO artifacts (id, project_id, artifact_type, title, content, content_hash, position, version, internal_state, contribution_category, ai_modification_ratio, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'draft', 'primarily_human', 0.0, datetime('now'), datetime('now'))""",
            (art_id, project_id, artifact_type, title, placeholder, content_hash, position),
        )

        ver_id = uuid.uuid4().hex
        c.execute(
            """INSERT INTO artifact_versions (id, artifact_id, version_number, title, content, content_hash, created_by, contribution_category, created_at)
               VALUES (?, ?, 1, ?, ?, ?, ?, 'primarily_human', datetime('now'))""",
            (ver_id, art_id, title, placeholder, content_hash, user_id),
        )

        print(f"  Created: [{artifact_type}] {title}")

    conn.commit()
    print("Done! Scaffold sections added.")

# Verify
c.execute("SELECT id, artifact_type, title, position FROM artifacts WHERE project_id=? AND deleted_at IS NULL ORDER BY position", (project_id,))
all_arts = c.fetchall()
print(f"\nAll artifacts now ({len(all_arts)}):")
for a in all_arts:
    t = a[2] if a[2] else "(untitled)"
    print(f"  pos={a[3]}: [{a[1]}] {t}")

conn.close()
