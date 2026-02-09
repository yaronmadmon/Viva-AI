import sqlite3
conn = sqlite3.connect("viva_dev.db")
c = conn.cursor()
c.execute("SELECT id, artifact_type, title, position FROM artifacts WHERE project_id='9b60ab9c2d4c4d0b9453de7aa54f978e' AND deleted_at IS NULL ORDER BY position")
arts = c.fetchall()
print(f"Original project artifacts ({len(arts)}):")
for a in arts:
    t = a[2] if a[2] else "(untitled)"
    print(f"  pos={a[3]}: [{a[1]}] {t}")
conn.close()
