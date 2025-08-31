"""
Integration tests for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from tests.test_base import BaseTestCase


class TestAuthEndpoints(BaseTestCase):
    """Integration tests for authentication endpoints."""

    def test_register_new_user(self):
        """Test user registration endpoint."""
        user_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "securepassword123"
        }

        response = self.client.post("/api/auth/register", json=user_data)
        assert response.status_code == 200

        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert "id" in data
        assert "role" in data

    def test_register_duplicate_email(self):
        """Test registration with duplicate email."""
        user_data = {
            "email": "test@example.com",  # This email already exists from seed data
            "name": "Duplicate User",
            "password": "password123"
        }

        response = self.client.post("/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self):
        """Test registration with invalid email."""
        user_data = {
            "email": "invalid-email",
            "name": "Test User",
            "password": "password123"
        }

        response = self.client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error

    def test_login_success(self):
        """Test successful login."""
        login_data = {
            "email": "alice.johnson@student.edu",  # From seed data
            "password": "password"
        }

        response = self.client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        login_data = {
            "email": "alice.johnson@student.edu",
            "password": "wrongpassword"
        }

        response = self.client.post("/api/auth/login", json=login_data)
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self):
        """Test login with nonexistent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password"
        }

        response = self.client.post("/api/auth/login", json=login_data)
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()

    def test_refresh_token_success(self):
        """Test successful token refresh."""
        # First login to get tokens
        login_data = {
            "email": "alice.johnson@student.edu",
            "password": "password"
        }

        login_response = self.client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # Now refresh the token
        refresh_data = {
            "refresh_token": refresh_token
        }

        response = self.client.post("/api/auth/refresh", json=refresh_data)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self):
        """Test refresh with invalid token."""
        refresh_data = {
            "refresh_token": "invalid_refresh_token"
        }

        response = self.client.post("/api/auth/refresh", json=refresh_data)
        assert response.status_code == 401
        assert "invalid refresh token" in response.json()["detail"].lower()

    def test_get_current_user_authenticated(self):
        """Test getting current user when authenticated."""
        # Login first
        login_data = {
            "email": "alice.johnson@student.edu",
            "password": "password"
        }

        login_response = self.client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Get current user
        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["email"] == "alice.johnson@student.edu"
        assert data["name"] == "Alice Johnson"
        assert data["role"] == "student"

    def test_get_current_user_unauthenticated(self):
        """Test getting current user without authentication."""
        response = self.client.get("/api/auth/me")
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = self.client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_update_current_user(self):
        """Test updating current user profile."""
        # Login first
        login_data = {
            "email": "alice.johnson@student.edu",
            "password": "password"
        }

        login_response = self.client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Update user
        update_data = {
            "name": "Alice Johnson Updated"
        }

        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.client.put("/api/auth/me", json=update_data, headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Alice Johnson Updated"
        assert data["email"] == "alice.johnson@student.edu"

    def test_update_current_user_email(self):
        """Test updating current user email."""
        # Login first
        login_data = {
            "email": "bob.wilson@student.edu",
            "password": "password"
        }

        login_response = self.client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Update email
        update_data = {
            "email": "bob.wilson.updated@student.edu"
        }

        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.client.put("/api/auth/me", json=update_data, headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["email"] == "bob.wilson.updated@student.edu"

    def test_update_current_user_duplicate_email(self):
        """Test updating to duplicate email."""
        # Login first
        login_data = {
            "email": "alice.johnson@student.edu",
            "password": "password"
        }

        login_response = self.client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Try to update to existing email
        update_data = {
            "email": "bob.wilson@student.edu"  # This email already exists
        }

        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.client.put("/api/auth/me", json=update_data, headers=headers)
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"].lower()

    def test_list_users_as_admin(self):
        """Test listing all users as admin."""
        # Login as admin
        login_data = {
            "email": "admin@lms.com",
            "password": "admin123"
        }

        login_response = self.client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # List users
        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.client.get("/api/auth/users", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 7  # At least the seeded users

        # Check that each user has required fields
        for user in data:
            assert "id" in user
            assert "email" in user
            assert "name" in user
            assert "role" in user

    def test_list_users_as_non_admin(self):
        """Test listing users as non-admin (should fail)."""
        # Login as student
        login_data = {
            "email": "alice.johnson@student.edu",
            "password": "password"
        }

        login_response = self.client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Try to list users
        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.client.get("/api/auth/users", headers=headers)
        assert response.status_code == 403
        assert "insufficient permissions" in response.json()["detail"].lower()

    def test_delete_user_as_admin(self):
        """Test deleting a user as admin."""
        # First create a test user to delete
        user_data = {
            "email": "todelete@example.com",
            "name": "To Delete",
            "password": "password123"
        }

        create_response = self.client.post("/api/auth/register", json=user_data)
        assert create_response.status_code == 200
        user_id = create_response.json()["id"]

        # Login as admin
        login_data = {
            "email": "admin@lms.com",
            "password": "admin123"
        }

        login_response = self.client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Delete the user
        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.client.delete(f"/api/auth/users/{user_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_user_self(self):
        """Test that admin cannot delete themselves."""
        # Login as admin
        login_data = {
            "email": "admin@lms.com",
            "password": "admin123"
        }

        login_response = self.client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        admin_data = login_response.json()

        # Try to delete self
        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.client.delete(f"/api/auth/users/{admin_data['id']}", headers=headers)
        assert response.status_code == 400
        assert "cannot delete yourself" in response.json()["detail"].lower()

    def test_update_user_as_admin(self):
        """Test updating another user as admin."""
        # Login as admin
        login_data = {
            "email": "admin@lms.com",
            "password": "admin123"
        }

        login_response = self.client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Get a user to update (use Alice)
        headers = {"Authorization": f"Bearer {access_token}"}
        users_response = self.client.get("/api/auth/users", headers=headers)
        alice = next(user for user in users_response.json() if user["email"] == "alice.johnson@student.edu")

        # Update the user
        update_data = {
            "name": "Alice Johnson (Updated by Admin)"
        }

        response = self.client.put(f"/api/auth/users/{alice['id']}", json=update_data, headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "updated"

    def test_update_user_as_non_admin(self):
        """Test updating user as non-admin (should fail)."""
        # Login as student
        login_data = {
            "email": "alice.johnson@student.edu",
            "password": "password"
        }

        login_response = self.client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Try to update another user
        update_data = {
            "name": "Hacked Name"
        }

        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.client.put("/api/auth/users/some_user_id", json=update_data, headers=headers)
        assert response.status_code == 403
        assert "insufficient permissions" in response.json()["detail"].lower()


class TestAuthSecurity:
    """Security tests for authentication endpoints."""

    def test_sql_injection_attempt(self):
        """Test protection against SQL injection in login."""
        login_data = {
            "email": "admin@lms.com' OR '1'='1",
            "password": "wrongpassword"
        }

        response = self.client.post("/api/auth/login", json=login_data)
        assert response.status_code == 401
        # Should not bypass authentication

    def test_xss_attempt_in_registration(self):
        """Test protection against XSS in user registration."""
        user_data = {
            "email": "test@example.com",
            "name": "<script>alert('xss')</script>",
            "password": "password123"
        }

        response = self.client.post("/api/auth/register", json=user_data)
        assert response.status_code == 200

        data = response.json()
        # Name should be stored as-is (XSS protection should be handled at display time)
        assert data["name"] == "<script>alert('xss')</script>"

    def test_brute_force_protection(self):
        """Test that system handles multiple failed login attempts."""
        login_data = {
            "email": "alice.johnson@student.edu",
            "password": "wrongpassword"
        }

        # Try multiple failed logins
        for _ in range(10):
            response = self.client.post("/api/auth/login", json=login_data)
            assert response.status_code == 401

        # System should still work (no rate limiting implemented yet, but should not crash)
        correct_login = {
            "email": "alice.johnson@student.edu",
            "password": "password"
        }

        response = self.client.post("/api/auth/login", json=correct_login)
        assert response.status_code == 200

    def test_token_expiry_simulation(self):
        """Test behavior with expired tokens (simulated)."""
        # This would require mocking time, but for now just test invalid token
        headers = {"Authorization": "Bearer expired_token_123"}
        response = self.client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401