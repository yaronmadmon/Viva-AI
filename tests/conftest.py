"""
Pytest fixtures for RAMP tests.
"""

import asyncio
import uuid
from datetime import datetime
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.kernel.models.base import Base
from src.kernel.models.user import User, UserRole
from src.kernel.models.project import ResearchProject, ProjectStatus, DisciplineType
from src.kernel.models.artifact import Artifact, ArtifactType, compute_content_hash
from src.kernel.models.mastery import UserMasteryProgress, CheckpointAttempt
from src.kernel.models.verification import ContentVerificationRequest
from src.kernel.identity.password import hash_password
from src.kernel.identity.jwt import JWTManager


# Test database URL (use separate test database)
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/viva_research_test"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email="testuser@example.com",
        password_hash=hash_password("TestPassword123"),
        full_name="Test User",
        role=UserRole.STUDENT,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_advisor(db_session: AsyncSession) -> User:
    """Create a test advisor user."""
    user = User(
        id=uuid.uuid4(),
        email="advisor@example.com",
        password_hash=hash_password("AdvisorPass123"),
        full_name="Test Advisor",
        role=UserRole.ADVISOR,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        password_hash=hash_password("AdminPass123"),
        full_name="Test Admin",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user: User) -> ResearchProject:
    """Create a test research project."""
    project = ResearchProject(
        id=uuid.uuid4(),
        title="Test Research Project",
        description="A test project for unit tests",
        discipline_type=DisciplineType.STEM,
        status=ProjectStatus.ACTIVE,
        owner_id=test_user.id,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_artifact(
    db_session: AsyncSession,
    test_project: ResearchProject,
) -> Artifact:
    """Create a test artifact."""
    content = "This is test content for the artifact."
    artifact = Artifact(
        id=uuid.uuid4(),
        project_id=test_project.id,
        artifact_type=ArtifactType.SECTION,
        title="Test Section",
        content=content,
        content_hash=compute_content_hash(content),
        version=1,
    )
    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)
    return artifact


@pytest.fixture
def jwt_manager() -> JWTManager:
    """Create a JWT manager for tests."""
    return JWTManager(
        secret_key="test-secret-key-for-testing-only",
        algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )


@pytest.fixture
def auth_headers(test_user: User, jwt_manager: JWTManager) -> dict:
    """Create authentication headers for a test user."""
    token, _, _ = jwt_manager.create_access_token(
        user_id=test_user.id,
        email=test_user.email,
        role=test_user.role.value,
    )
    return {"Authorization": f"Bearer {token}"}


# Sample test data fixtures

@pytest.fixture
def sample_citation_data() -> dict:
    """Sample citation data for validation tests."""
    return {
        "type": "journal",
        "title": "A Study on Test-Driven Development",
        "authors": ["Smith, John", "Doe, Jane"],
        "journal": "Journal of Software Engineering",
        "year": 2024,
        "doi": "10.1234/example.2024.001",
    }


@pytest.fixture
def sample_ai_suggestion() -> dict:
    """Sample AI suggestion data."""
    return {
        "suggestion_type": "outline",
        "content": "I. Introduction\nII. Methods\nIII. Results\nIV. Discussion",
        "confidence": 0.85,
    }
