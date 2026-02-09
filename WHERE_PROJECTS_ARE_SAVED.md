# Where projects are saved

## Storage location

Projects are stored in the **database**, not in individual files.

- **If you use SQLite** (e.g. in `.env`: `DATABASE_URL=sqlite+aiosqlite:///./ramp_dev.db`):
  - The database file is **`ramp_dev.db`** in the project root: **`c:\Viva AI\ramp_dev.db`**
  - (The path is relative to where you start the backend. If you run the server from `c:\Viva AI`, the file is created there.)
- **If you use PostgreSQL** (e.g. `DATABASE_URL=postgresql+asyncpg://...`):
  - Projects are stored in that PostgreSQL server in the `research_projects` table (and related tables). There is no local `.db` file.

Your current `.env` uses SQLite: `DATABASE_URL=sqlite+aiosqlite:///./ramp_dev.db`, so projects are in **`c:\Viva AI\ramp_dev.db`**.

---

## Why you don’t see the project I created

The project created by the script was created **by a specific test user**. The app only shows you **projects you own** (or that were shared with you).

- **Test user:** `e2e-test@example.com`
- **Password:** `TestPassword123`

So:

1. **To see that project:** Log in with **`e2e-test@example.com`** / **`TestPassword123`** in the frontend (with the backend running and using the **same** database where the script ran). Then open the Student dashboard; the project “E2E Created Project” should appear.
2. **If you use a different account:** You will only see projects that account owns. Create a new project from the UI (Student dashboard → “New project”) and it will be saved in the same database and appear for your user.

---

## Quick checklist

- Backend is running (e.g. `uvicorn` on port 8000) and loads the same DB (e.g. your `.env` with `ramp_dev.db`).
- Frontend is running (e.g. `npm run dev` in `frontend/`) and points at that backend (e.g. `NEXT_PUBLIC_API_URL` or default `http://localhost:8000/api/v1`).
- You’re logged in as **`e2e-test@example.com`** if you want to see the script-created project; otherwise use your own account and create a project from the UI.
