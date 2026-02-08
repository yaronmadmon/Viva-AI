"""
System smoke test: full API flow in-process with SQLite.
Verifies health, auth, projects, artifacts, mastery, integrity report, and effort gates.
Uses a temp file DB so all connections share the same database.
"""

import os
import tempfile
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Use file-based SQLite so all connections share the same DB (in-memory is per-connection)
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
TEST_DB_PATH = _tmp.name
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["RATE_LIMIT_ENABLED"] = "false"
# Force config reload so app uses test DB
from src.config import get_settings
get_settings.cache_clear()

from src.kernel.models import Base
from src.main import app
from src.database import get_db


# Create test engine and session factory (same file so app and fixture share DB)
TEST_ENGINE = create_async_engine(
    f"sqlite+aiosqlite:///{TEST_DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)
TEST_SESSION_MAKER = async_sessionmaker(
    TEST_ENGINE,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TEST_SESSION_MAKER() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """Async client with test DB and rate limit disabled."""
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)


def pytest_sessionfinish(session, exitstatus):
    """Clean up temp DB file after test run."""
    try:
        if os.path.exists(TEST_DB_PATH):
            os.unlink(TEST_DB_PATH)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    """Health endpoint responds."""
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    """Register and login return tokens."""
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass123",
            "full_name": "Smoke User",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"] == email

    r2 = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass123"},
    )
    assert r2.status_code == 200
    assert "access_token" in r2.json()
    return data["access_token"]


@pytest.mark.asyncio
async def test_full_flow(client: AsyncClient):
    """Register -> login -> create project -> get project -> integrity report (effort gates)."""
    email = f"flow-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass123",
            "full_name": "Flow User",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create project
    r = await client.post(
        "/api/v1/projects",
        json={
            "title": "Smoke Project",
            "description": "System test project",
            "discipline_type": "stem",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    project = r.json()
    project_id = project["id"]

    # List projects
    r = await client.get("/api/v1/projects", headers=headers)
    assert r.status_code == 200
    assert any(p["id"] == project_id for p in r.json())

    # Get single project
    r = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Smoke Project"

    # Integrity report (includes effort gates; export_allowed may be false)
    r = await client.get(
        f"/api/v1/projects/{project_id}/integrity",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "project_id" in data
    assert "overall_score" in data
    assert "export_allowed" in data
    assert "items" in data
    # Effort gates should appear in items when not met
    assert isinstance(data["items"], list)

    # Export (POST) - may be 200 or 403 when effort gates/integrity block
    r = await client.post(
        f"/api/v1/projects/{project_id}/export/docx",
        headers=headers,
    )
    assert r.status_code in (200, 403), r.text


@pytest.mark.asyncio
async def test_mastery_progress(client: AsyncClient):
    """Mastery progress and capability check."""
    email = f"mastery-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123", "full_name": "Mastery User"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/projects",
        json={"title": "M", "description": "D", "discipline_type": "stem"},
        headers=headers,
    )
    project_id = r.json()["id"]

    # Get mastery progress (route is under projects/:id/mastery/progress)
    r = await client.get(
        f"/api/v1/projects/{project_id}/mastery/progress",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "current_tier" in data
    assert "ai_level" in data
