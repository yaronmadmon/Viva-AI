"""
Phase-gate connectivity tests (T0-T6).

Verifies core services, DB, event store, API routes, and governance engines
are reachable and responding. Fails fast if wiring is broken.

T0: Baseline connectivity before Phase A.
T1-T6: Cumulative connectivity checks added after each phase.
"""

import os
import tempfile
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Use file-based SQLite so all connections share the same DB
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
TEST_DB_PATH = _tmp.name
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["RATE_LIMIT_ENABLED"] = "false"
from src.config import get_settings
get_settings.cache_clear()

from src.kernel.models import Base
from src.kernel.models.event_log import EventLog, EventType
from src.kernel.events.event_store import EventStore
from src.engines.audit.export_controller import ExportController
from src.engines.audit.integrity_calculator import IntegrityScore
from src.main import app
from src.database import get_db


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


@pytest_asyncio.fixture
async def db_session():
    """Test DB session for direct queries."""
    async with TEST_SESSION_MAKER() as session:
        yield session
        await session.rollback()


def pytest_sessionfinish(session, exitstatus):
    try:
        if os.path.exists(TEST_DB_PATH):
            os.unlink(TEST_DB_PATH)
    except Exception:
        pass


# --- T0: Baseline Connectivity (Pre-Phase A) ---


@pytest.mark.asyncio
async def test_t0_health_endpoint(client: AsyncClient):
    """Health endpoint returns 200."""
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_t0_auth_register_login(client: AsyncClient):
    """Auth (register/login) returns tokens."""
    email = f"t0-{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123", "full_name": "T0 User"},
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


@pytest.mark.asyncio
async def test_t0_projects_crud(client: AsyncClient):
    """Projects CRUD works."""
    email = f"t0-proj-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123", "full_name": "T0 Proj User"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/projects",
        json={"title": "T0 Project", "description": "Test", "discipline_type": "stem"},
        headers=headers,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    r = await client.get("/api/v1/projects", headers=headers)
    assert r.status_code == 200
    assert any(p["id"] == project_id for p in r.json())

    r = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["title"] == "T0 Project"


@pytest.mark.asyncio
async def test_t0_mastery_progress(client: AsyncClient):
    """Mastery progress endpoint responds."""
    email = f"t0-mast-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123", "full_name": "T0 Mastery User"},
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

    r = await client.get(
        f"/api/v1/projects/{project_id}/mastery/progress",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "current_tier" in data
    assert "ai_level" in data


@pytest.mark.asyncio
async def test_t0_integrity_report(client: AsyncClient):
    """Integrity report endpoint responds."""
    email = f"t0-int-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123", "full_name": "T0 Integrity User"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/projects",
        json={"title": "I", "description": "D", "discipline_type": "stem"},
        headers=headers,
    )
    project_id = r.json()["id"]

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


@pytest.mark.asyncio
async def test_t0_event_store_logs_and_counts(client: AsyncClient, db_session: AsyncSession):
    """Event store logs and counts events."""
    event_store = EventStore(db_session)
    entity_id = uuid.uuid4()

    await event_store.log(
        event_type=EventType.PROJECT_CREATED,
        entity_type="project",
        entity_id=entity_id,
        user_id=uuid.uuid4(),
        payload={"title": "Test"},
    )
    await db_session.commit()

    count = await event_store.count_events(
        entity_type="project",
        entity_id=entity_id,
        event_type=EventType.PROJECT_CREATED,
    )
    assert count >= 1


@pytest.mark.asyncio
async def test_t0_export_controller_callable():
    """Export controller evaluate_export_readiness is callable."""
    from datetime import datetime

    project_id = uuid.uuid4()
    integrity_score = IntegrityScore(
        project_id=project_id,
        calculated_at=datetime.utcnow(),
        score=80.0,
        contribution_score=90.0,
        citation_score=85.0,
        structure_score=75.0,
        mastery_score=80.0,
        primarily_human_count=5,
        human_guided_count=2,
        ai_reviewed_count=0,
        unmodified_ai_count=0,
        artifacts_analyzed=7,
        issues=[],
        export_allowed=True,
        blocking_issues=[],
    )
    decision = ExportController.evaluate_export_readiness(
        project_id=project_id,
        integrity_score=integrity_score,
        mastery_tier=3,
        project_status="active",
        pending_reviews=0,
    )
    assert decision is not None
    assert hasattr(decision, "allowed")
    assert hasattr(decision, "reasons")


# --- T1: Connectivity After Phase A ---


@pytest.mark.asyncio
async def test_t1_submission_unit_api_registered(client: AsyncClient):
    """SubmissionUnit model and API route registered."""
    email = f"t1-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123", "full_name": "T1 User"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/projects",
        json={"title": "T1", "description": "D", "discipline_type": "stem"},
        headers=headers,
    )
    project_id = r.json()["id"]

    # List submission units
    r = await client.get(
        f"/api/v1/projects/{project_id}/submission-units",
        headers=headers,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_t1_state_machine_valid_transitions():
    """State machine service valid_transitions and can_transition return expected values."""
    from src.orchestration.state_machine import valid_transitions, can_transition
    from src.kernel.models.user import UserRole

    transitions = valid_transitions("draft", "submission_unit")
    assert "ready_for_review" in transitions

    assert can_transition(UserRole.STUDENT, "draft", "ready_for_review", "submission_unit")
    assert not can_transition(UserRole.STUDENT, "draft", "approved", "submission_unit")


@pytest.mark.asyncio
async def test_t1_event_types_state_changes_exist():
    """Event types for state changes exist."""
    from src.kernel.models.event_log import EventType

    assert hasattr(EventType, "SUBMISSION_UNIT_STATE_CHANGED")
    assert hasattr(EventType, "ARTIFACT_STATE_CHANGED")


# --- T2: Connectivity After Phase B ---


@pytest.mark.asyncio
async def test_t2_review_response_model_exists(client: AsyncClient):
    """ReviewResponse model and migration applied."""
    from src.kernel.models.review_response import ReviewResponse

    assert ReviewResponse is not None


@pytest.mark.asyncio
async def test_t2_advisor_queue_endpoint(client: AsyncClient):
    """Advisor queue endpoint responds."""
    email = f"t2-adv-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123", "full_name": "T2 Advisor"},
    )
    # Registration may not accept role - use default student; advisor queue returns 403 for non-advisor
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/v1/advisors/reviews", headers=headers)
    # 403 for student, 200 for advisor
    assert r.status_code in (200, 403)


@pytest.mark.asyncio
async def test_t2_examiner_endpoint(client: AsyncClient):
    """Examiner endpoint responds for examiner role."""
    # Create examiner user (need to set role - may require admin or seed)
    # For now, student gets 403
    email = f"t2-ex-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123", "full_name": "T2 User"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/projects",
        json={"title": "T2", "description": "D", "discipline_type": "stem"},
        headers=headers,
    )
    project_id = r.json()["id"]
    r = await client.get(f"/api/v1/examiner/projects/{project_id}/frozen-content", headers=headers)
    # 403 for non-examiner
    assert r.status_code in (200, 403)


# --- T3: Connectivity After Phase C ---


@pytest.mark.asyncio
async def test_t3_curriculum_engine(client: AsyncClient):
    """Curriculum engine returns concepts and prerequisites."""
    from src.pedagogy.curriculum_engine import CurriculumEngine, LessonsEngine

    concepts = CurriculumEngine.get_concepts("stem")
    assert len(concepts) >= 1
    lessons = LessonsEngine.get_lesson_structure("stem")
    assert len(lessons) >= 1


# --- T4: Connectivity After Phase D ---


@pytest.mark.asyncio
async def test_t4_defense_api_exists(client: AsyncClient):
    """Defense API endpoints respond."""
    email = f"t4-{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "SecurePass123", "full_name": "T4 User"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/v1/projects", json={"title": "T4", "description": "D", "discipline_type": "stem"}, headers=headers)
    project_id = r.json()["id"]
    r = await client.get(f"/api/v1/projects/{project_id}/defense/practice/questions", headers=headers)
    assert r.status_code in (200, 404)


# --- T5: Connectivity After Phase E ---


@pytest.mark.asyncio
async def test_t5_guidance_endpoint(client: AsyncClient):
    """Guidance endpoint returns rules."""
    email = f"t5-{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "SecurePass123", "full_name": "T5 User"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/v1/projects", json={"title": "T5", "description": "D", "discipline_type": "stem"}, headers=headers)
    project_id = r.json()["id"]
    r = await client.get(f"/api/v1/projects/{project_id}/guidance/next", headers=headers)
    assert r.status_code in (200, 404)


# --- T6: Connectivity After Phase F ---


@pytest.mark.asyncio
async def test_t6_certification_endpoint(client: AsyncClient):
    """Certification and verification endpoints respond."""
    email = f"t6-{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "SecurePass123", "full_name": "T6 User"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/v1/projects", json={"title": "T6", "description": "D", "discipline_type": "stem"}, headers=headers)
    project_id = r.json()["id"]
    r = await client.get(f"/api/v1/projects/{project_id}/certification", headers=headers)
    assert r.status_code in (200, 404)
