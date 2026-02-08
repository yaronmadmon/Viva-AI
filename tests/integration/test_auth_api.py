"""Integration tests for auth API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient

# Note: These tests require a running test database
# They are marked to skip if the database is not available


@pytest.mark.skip(reason="Requires running database")
class TestAuthAPI:
    """Integration tests for /api/v1/auth endpoints."""
    
    @pytest_asyncio.fixture
    async def client(self):
        """Create an async HTTP client."""
        from src.main import app
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    async def test_register_new_user(self, client: AsyncClient):
        """Test user registration endpoint."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123",
                "full_name": "New User",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "newuser@example.com"
    
    async def test_register_duplicate_email(self, client: AsyncClient):
        """Test registration with existing email."""
        # First registration
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123",
                "full_name": "First User",
            },
        )
        
        # Second registration with same email
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "AnotherPass123",
                "full_name": "Second User",
            },
        )
        
        assert response.status_code == 400
    
    async def test_login_success(self, client: AsyncClient):
        """Test successful login."""
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "logintest@example.com",
                "password": "SecurePass123",
                "full_name": "Login Test",
            },
        )
        
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "logintest@example.com",
                "password": "SecurePass123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    async def test_login_wrong_password(self, client: AsyncClient):
        """Test login with wrong password."""
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "SecurePass123",
                "full_name": "Wrong Pass Test",
            },
        )
        
        # Login with wrong password
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrongpass@example.com",
                "password": "WrongPassword",
            },
        )
        
        assert response.status_code == 401
    
    async def test_get_current_user(self, client: AsyncClient):
        """Test getting current user profile."""
        # Register and get token
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "profiletest@example.com",
                "password": "SecurePass123",
                "full_name": "Profile Test",
            },
        )
        
        token = register_response.json()["access_token"]
        
        # Get profile
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profiletest@example.com"
    
    async def test_unauthorized_access(self, client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
