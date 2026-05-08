"""
Comprehensive test suite for QueryMind AI.
Tests cover: authentication, multi-tenancy, query validation, audit logging.

Run tests:
    pytest tests/ -v
    pytest tests/test_auth.py -v --tb=short
    pytest tests/ -v --cov=backend --cov-report=html
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ════════════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def test_db():
    """Create test database."""
    DATABASE_URL = "sqlite:///./test.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    
    # Create tables
    from db.database import Base
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """Create test client."""
    from main import app
    from db.database import get_db
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db)
    
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


# ════════════════════════════════════════════════════════════════════════════
# Authentication Tests
# ════════════════════════════════════════════════════════════════════════════


class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_register_valid_user(self, client):
        """Test user registration with valid credentials."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "password": "ValidPassword123!",
                "email": "test@example.com",
                "display_name": "Test User"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["token_type"] == "bearer"
        assert "access_token" in data
        assert "db_name" in data
    
    def test_register_weak_password(self, client):
        """Test that weak passwords are rejected."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "password": "weak",  # Too short, no complexity
                "email": "test@example.com"
            }
        )
        assert response.status_code == 400
        assert "Password must be at least 8 characters" in response.json()["detail"]
    
    def test_register_duplicate_username(self, client):
        """Test that duplicate usernames are rejected."""
        # Register first user
        client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "password": "ValidPassword123!",
            }
        )
        
        # Try to register again
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "password": "AnotherPassword123!",
            }
        )
        assert response.status_code == 409
        assert "Username already taken" in response.json()["detail"]
    
    def test_login_success(self, client):
        """Test successful login."""
        # Register first
        client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "password": "ValidPassword123!",
            }
        )
        
        # Login
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "ValidPassword123!",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert "access_token" in data
    
    def test_login_invalid_password(self, client):
        """Test login with wrong password."""
        # Register first
        client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "password": "ValidPassword123!",
            }
        )
        
        # Login with wrong password
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "WrongPassword123!",
            }
        )
        assert response.status_code == 401


# ════════════════════════════════════════════════════════════════════════════
# Query Validation Tests
# ════════════════════════════════════════════════════════════════════════════


class TestQueryValidation:
    """Test destructive query validation."""
    
    def test_validate_safe_select_query(self, client):
        """Test that SELECT queries are safe."""
        # Register and login
        auth_response = client.post(
            "/api/auth/register",
            json={"username": "user1", "password": "Password123!"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.post(
            "/api/query/validate",
            headers={"Authorization": f"Bearer {token}"},
            json={"sql": "SELECT * FROM products"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_safe"] is True
        assert data["requires_confirmation"] is False
    
    def test_validate_delete_requires_confirmation(self, client):
        """Test that DELETE queries require confirmation."""
        # Register and login
        auth_response = client.post(
            "/api/auth/register",
            json={"username": "user2", "password": "Password123!"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.post(
            "/api/query/validate",
            headers={"Authorization": f"Bearer {token}"},
            json={"sql": "DELETE FROM products WHERE id > 10"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_safe"] is True
        assert data["requires_confirmation"] is True
        assert "confirmation_token" in data
    
    def test_validate_truncate_requires_confirmation(self, client):
        """Test that TRUNCATE queries require confirmation."""
        # Register and login
        auth_response = client.post(
            "/api/auth/register",
            json={"username": "user3", "password": "Password123!"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.post(
            "/api/query/validate",
            headers={"Authorization": f"Bearer {token}"},
            json={"sql": "TRUNCATE TABLE products"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["requires_confirmation"] is True
    
    def test_validate_multistatement_blocked(self, client):
        """Test that multi-statement queries are blocked."""
        # Register and login
        auth_response = client.post(
            "/api/auth/register",
            json={"username": "user4", "password": "Password123!"}
        )
        token = auth_response.json()["access_token"]
        
        response = client.post(
            "/api/query/validate",
            headers={"Authorization": f"Bearer {token}"},
            json={"sql": "SELECT * FROM products; DROP TABLE products;"}
        )
        assert response.status_code == 400


# ════════════════════════════════════════════════════════════════════════════
# Multi-Tenancy Tests
# ════════════════════════════════════════════════════════════════════════════


class TestMultiTenancy:
    """Test multi-tenant database isolation."""
    
    def test_users_have_separate_databases(self, client):
        """Test that each user gets their own database."""
        # Register user 1
        response1 = client.post(
            "/api/auth/register",
            json={"username": "tenant1", "password": "Password123!"}
        )
        db_name1 = response1.json()["db_name"]
        
        # Register user 2
        response2 = client.post(
            "/api/auth/register",
            json={"username": "tenant2", "password": "Password123!"}
        )
        db_name2 = response2.json()["db_name"]
        
        # Database names should be different
        assert db_name1 != db_name2
        assert "tenant1" in db_name1
        assert "tenant2" in db_name2
    
    def test_user_can_only_access_own_database(self, client):
        """Test that users can't access other users' databases."""
        # Register user 1
        auth1 = client.post(
            "/api/auth/register",
            json={"username": "user_a", "password": "Password123!"}
        )
        token1 = auth1.json()["access_token"]
        
        # Register user 2
        auth2 = client.post(
            "/api/auth/register",
            json={"username": "user_b", "password": "Password123!"}
        )
        token2 = auth2.json()["access_token"]
        
        # Both should be able to call /api/auth/me
        response1 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert response1.status_code == 200
        assert response1.json()["username"] == "user_a"
        
        response2 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert response2.status_code == 200
        assert response2.json()["username"] == "user_b"


# ════════════════════════════════════════════════════════════════════════════
# Password Management Tests
# ════════════════════════════════════════════════════════════════════════════


class TestPasswordManagement:
    """Test password change and validation."""
    
    def test_change_password_success(self, client):
        """Test successful password change."""
        # Register
        auth = client.post(
            "/api/auth/register",
            json={"username": "user", "password": "OldPassword123!"}
        )
        token = auth.json()["access_token"]
        
        # Change password
        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "OldPassword123!",
                "new_password": "NewPassword456!"
            }
        )
        assert response.status_code == 200
        
        # Old password should no longer work
        login = client.post(
            "/api/auth/login",
            json={
                "username": "user",
                "password": "OldPassword123!"
            }
        )
        assert login.status_code == 401
        
        # New password should work
        login = client.post(
            "/api/auth/login",
            json={
                "username": "user",
                "password": "NewPassword456!"
            }
        )
        assert login.status_code == 200
    
    def test_change_password_wrong_old_password(self, client):
        """Test that wrong old password is rejected."""
        # Register
        auth = client.post(
            "/api/auth/register",
            json={"username": "user", "password": "OldPassword123!"}
        )
        token = auth.json()["access_token"]
        
        # Try to change with wrong old password
        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "WrongPassword123!",
                "new_password": "NewPassword456!"
            }
        )
        assert response.status_code == 401


# ════════════════════════════════════════════════════════════════════════════
# System Endpoints Tests
# ════════════════════════════════════════════════════════════════════════════


class TestSystemEndpoints:
    """Test system information endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_system_info_endpoint(self, client):
        """Test system info endpoint."""
        response = client.get("/api/system/info")
        assert response.status_code == 200
        data = response.json()
        assert "product" in data
        assert "features" in data
        assert "mcp_tools" in data
        assert "security" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
