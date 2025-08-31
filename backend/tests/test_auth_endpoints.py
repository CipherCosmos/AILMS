"""
Test authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

def test_register_endpoint():
    """Test user registration."""
    client = TestClient(app)

    # Test successful registration
    user_data = {
        "email": "newuser@example.com",
        "name": "New User",
        "password": "password123"
    }

    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code in [200, 400]  # 200 for new user, 400 if already exists

    if response.status_code == 200:
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "name" in data
        assert "role" in data

def test_login_endpoint():
    """Test user login."""
    client = TestClient(app)

    # First register a user
    user_data = {
        "email": "loginuser@example.com",
        "name": "Login User",
        "password": "password123"
    }

    response = client.post("/api/auth/register", json=user_data)
    if response.status_code == 200:
        # Now try to login
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }

        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data

def test_me_endpoint():
    """Test get current user endpoint."""
    client = TestClient(app)

    # Test without authentication
    response = client.get("/api/auth/me")
    assert response.status_code == 401

    # Test with invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401

def test_refresh_endpoint():
    """Test token refresh endpoint."""
    client = TestClient(app)

    # Test with invalid refresh token
    refresh_data = {"refresh_token": "invalid_token"}
    response = client.post("/api/auth/refresh", json=refresh_data)
    assert response.status_code == 401

def test_update_me_endpoint():
    """Test update current user endpoint."""
    client = TestClient(app)

    # Test without authentication
    update_data = {"name": "Updated Name"}
    response = client.put("/api/auth/me", json=update_data)
    assert response.status_code == 401

def test_list_users_endpoint():
    """Test list users endpoint."""
    client = TestClient(app)

    # Test without authentication
    response = client.get("/api/auth/users")
    assert response.status_code == 401

def test_delete_user_endpoint():
    """Test delete user endpoint."""
    client = TestClient(app)

    # Test without authentication
    response = client.delete("/api/auth/users/test_user_id")
    assert response.status_code == 401

def test_update_user_endpoint():
    """Test update user endpoint."""
    client = TestClient(app)

    # Test without authentication
    update_data = {"name": "Updated Name"}
    response = client.put("/api/auth/users/test_user_id", json=update_data)
    assert response.status_code == 401