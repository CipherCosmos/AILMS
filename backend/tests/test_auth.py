"""
Unit tests for authentication module.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from auth import _create_tokens, _current_user, _require_role
from models import UserBase


class TestTokenCreation:
    """Test token creation functionality."""

    @pytest.mark.asyncio
    async def test_create_tokens_success(self):
        """Test successful token creation."""
        user = {
            "id": "test_user_123",
            "role": "student",
            "email": "test@example.com"
        }

        with patch('auth.jwt.encode') as mock_encode:
            mock_encode.return_value = "mock_token"
            tokens = await _create_tokens(user)

            assert tokens.access_token == "mock_token"
            assert tokens.refresh_token == "mock_token"
            assert tokens.token_type == "bearer"

            # Verify JWT calls
            assert mock_encode.call_count == 2

    @pytest.mark.asyncio
    async def test_create_tokens_with_different_roles(self):
        """Test token creation with different user roles."""
        roles = ["student", "instructor", "admin"]

        for role in roles:
            user = {
                "id": f"user_{role}",
                "role": role,
                "email": f"{role}@example.com"
            }

            with patch('auth.jwt.encode') as mock_encode:
                mock_encode.return_value = f"token_for_{role}"
                tokens = await _create_tokens(user)

                assert tokens.access_token == f"token_for_{role}"
                assert tokens.token_type == "bearer"


class TestCurrentUser:
    """Test current user retrieval functionality."""

    @pytest.mark.asyncio
    async def test_current_user_valid_token(self):
        """Test retrieving user with valid token."""
        mock_user = {
            "_id": "user_123",
            "email": "test@example.com",
            "name": "Test User",
            "role": "student"
        }

        with patch('auth.jwt.decode') as mock_decode, \
             patch('auth._find_one') as mock_find:

            mock_decode.return_value = {"sub": "user_123", "role": "student"}
            mock_find.return_value = mock_user

            user = await _current_user("valid_token")

            assert user == mock_user
            mock_decode.assert_called_once_with("valid_token", mock_decode.call_args[0][1], algorithms=["HS256"])
            mock_find.assert_called_once_with("users", {"_id": "user_123"})

    @pytest.mark.asyncio
    async def test_current_user_invalid_token(self):
        """Test handling of invalid token."""
        with patch('auth.jwt.decode') as mock_decode:
            mock_decode.side_effect = Exception("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await _current_user("invalid_token")

            assert exc_info.value.status_code == 401
            assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_current_user_missing_user(self):
        """Test handling when user is not found in database."""
        with patch('auth.jwt.decode') as mock_decode, \
             patch('auth._find_one') as mock_find:

            mock_decode.return_value = {"sub": "nonexistent_user", "role": "student"}
            mock_find.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await _current_user("valid_token")

            assert exc_info.value.status_code == 401
            assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_current_user_invalid_token_payload(self):
        """Test handling of token with invalid payload."""
        with patch('auth.jwt.decode') as mock_decode:
            mock_decode.return_value = {}  # Missing 'sub' field

            with pytest.raises(HTTPException) as exc_info:
                await _current_user("token_without_sub")

            assert exc_info.value.status_code == 401
            assert "Invalid token payload" in exc_info.value.detail


class TestRoleRequirements:
    """Test role requirement functionality."""

    def test_require_role_success(self):
        """Test successful role requirement check."""
        user = {"role": "admin"}

        # Should not raise exception
        _require_role(user, ["admin", "instructor"])

    def test_require_role_insufficient_permissions(self):
        """Test role requirement failure."""
        user = {"role": "student"}

        with pytest.raises(HTTPException) as exc_info:
            _require_role(user, ["admin", "instructor"])

        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail

    def test_require_role_multiple_allowed_roles(self):
        """Test role requirement with multiple allowed roles."""
        test_cases = [
            ({"role": "student"}, ["student", "instructor"], True),
            ({"role": "instructor"}, ["admin"], False),
            ({"role": "admin"}, ["admin", "instructor", "student"], True),
        ]

        for user, allowed_roles, should_pass in test_cases:
            if should_pass:
                _require_role(user, allowed_roles)
            else:
                with pytest.raises(HTTPException):
                    _require_role(user, allowed_roles)


class TestUserModel:
    """Test User model functionality."""

    def test_user_base_creation(self):
        """Test UserBase model creation."""
        user = UserBase(
            email="test@example.com",
            name="Test User",
            role="student"
        )

        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.role == "student"
        assert user.id is not None
        assert len(user.id) > 0

    def test_user_base_uuid_generation(self):
        """Test that UUID is generated for user ID."""
        user1 = UserBase(email="test1@example.com", name="User 1", role="student")
        user2 = UserBase(email="test2@example.com", name="User 2", role="student")

        assert user1.id != user2.id
        assert len(user1.id) == 36  # UUID4 length
        assert len(user2.id) == 36

    def test_user_base_role_validation(self):
        """Test role validation in UserBase."""
        valid_roles = ["super_admin", "org_admin", "dept_admin", "instructor", "student", "auditor"]

        for role in valid_roles:
            user = UserBase(email="test@example.com", name="Test User", role=role)
            assert user.role == role

    def test_user_base_invalid_role(self):
        """Test handling of invalid role."""
        with pytest.raises(ValueError):
            UserBase(email="test@example.com", name="Test User", role="invalid_role")


class TestAuthIntegration:
    """Integration tests for auth module."""

    @pytest.mark.asyncio
    async def test_complete_auth_flow(self):
        """Test complete authentication flow."""
        user_data = {
            "_id": "test_user_123",
            "email": "test@example.com",
            "name": "Test User",
            "role": "student"
        }

        with patch('auth.jwt.decode') as mock_decode, \
             patch('auth._find_one') as mock_find, \
             patch('auth.jwt.encode') as mock_encode:

            # Mock token decoding
            mock_decode.return_value = {"sub": "test_user_123", "role": "student"}
            mock_find.return_value = user_data
            mock_encode.return_value = "mock_access_token"

            # Test token creation
            tokens = await _create_tokens(user_data)
            assert tokens.access_token == "mock_access_token"

            # Test current user retrieval
            user = await _current_user("mock_token")
            assert user == user_data

            # Test role requirement
            _require_role(user, ["student", "instructor"])