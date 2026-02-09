import sys
sys.path.insert(0, ".")
from src.kernel.identity.password import hash_password
import sqlite3

conn = sqlite3.connect("viva_dev.db")
c = conn.cursor()
new_hash = hash_password("Test123!")
c.execute("UPDATE users SET password_hash=? WHERE email=?", (new_hash, "yaronmadmon@gmail.com"))
print(f"Updated {c.rowcount} user(s)")
conn.commit()
conn.close()
