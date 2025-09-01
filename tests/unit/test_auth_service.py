"""
Unit tests for Auth Service
"""
import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from shared.config.config import settings


class TestAuthService:
    """Test cases for authentication service functionality"""

    @pytest.fixture
    def auth_service(self):
        """Auth service instance fixture"""
        from services.auth_service.app.services.auth_service import AuthService
        return AuthService()

    @pytest.fixture
    def test_user(self):
        """Test user data"""
        return {
            "email": "test@example.com",
            "name": "Test User",
            "password": "hashed_password",
            "role": "student",
            "is_active": True
        }

    def test_password_hashing(self, auth_service):
        """Test password hashing functionality"""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)

        assert hashed != password
        assert auth_service.verify_password(password, hashed)
        assert not auth_service.verify_password("wrong_password", hashed)

    def test_jwt_token_creation(self, auth_service, test_user):
        """Test JWT token creation"""
        token = auth_service.create_access_token(test_user["email"])

        assert token is not None
        assert isinstance(token, str)

        # Decode and verify token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        assert payload["sub"] == test_user["email"]
        assert "exp" in payload
        assert "iat" in payload

    def test_jwt_token_expiry(self, auth_service, test_user):
        """Test JWT token expiry"""
        # Create token that expires in 1 second
        expires_delta = timedelta(seconds=1)
        token = auth_service.create_access_token(
            test_user["email"],
            expires_delta=expires_delta
        )

        # Token should be valid immediately
        assert auth_service.verify_token(token) is not None

        # Wait for expiry (simulate by mocking time)
        import time
        time.sleep(2)

        # Token should be expired
        with pytest.raises(Exception):  # JWTExpiredError
            auth_service.verify_token(token)

    def test_user_registration_validation(self, auth_service):
        """Test user registration input validation"""
        # Valid user data
        valid_user = {
            "email": "valid@example.com",
            "name": "Valid User",
            "password": "ValidPass123!",
            "role": "student"
        }

        # Should not raise exception
        auth_service.validate_registration_data(valid_user)

        # Invalid email
        invalid_user = valid_user.copy()
        invalid_user["email"] = "invalid-email"
        with pytest.raises(ValueError):
            auth_service.validate_registration_data(invalid_user)

        # Invalid password
        invalid_user = valid_user.copy()
        invalid_user["password"] = "weak"
        with pytest.raises(ValueError):
            auth_service.validate_registration_data(invalid_user)

        # Invalid role
        invalid_user = valid_user.copy()
        invalid_user["role"] = "invalid_role"
        with pytest.raises(ValueError):
            auth_service.validate_registration_data(invalid_user)

    @pytest.mark.asyncio
    async def test_user_creation(self, auth_service, test_user):
        """Test user creation in database"""
        with patch('services.auth_service.app.database.auth_db') as mock_db:
            mock_collection = AsyncMock()
            mock_db.users = mock_collection

            # Mock successful insertion
            mock_collection.insert_one.return_value = AsyncMock()
            mock_collection.insert_one.return_value.inserted_id = "test_user_id"

            result = await auth_service.create_user(test_user)

            assert result["id"] == "test_user_id"
            assert result["email"] == test_user["email"]
            mock_collection.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_authentication(self, auth_service, test_user):
        """Test user authentication"""
        with patch('services.auth_service.app.database.auth_db') as mock_db:
            mock_collection = AsyncMock()
            mock_db.users = mock_collection

            # Mock user found in database
            mock_collection.find_one.return_value = test_user

            # Test successful authentication
            result = await auth_service.authenticate_user(
                test_user["email"],
                "TestPassword123!"
            )

            assert result is not None
            assert result["email"] == test_user["email"]

            # Test wrong password
            result = await auth_service.authenticate_user(
                test_user["email"],
                "wrong_password"
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_user_lookup(self, auth_service, test_user):
        """Test user lookup by email"""
        with patch('services.auth_service.app.database.auth_db') as mock_db:
            mock_collection = AsyncMock()
            mock_db.users = mock_collection
            mock_collection.find_one.return_value = test_user

            result = await auth_service.get_user_by_email(test_user["email"])

            assert result is not None
            assert result["email"] == test_user["email"]
            mock_collection.find_one.assert_called_once_with(
                {"email": test_user["email"]}
            )

    def test_role_validation(self, auth_service):
        """Test role validation"""
        valid_roles = [
            "super_admin", "org_admin", "dept_admin", "instructor",
            "teaching_assistant", "content_author", "student", "auditor",
            "parent_guardian", "proctor", "support_moderator",
            "career_coach", "marketplace_manager", "industry_reviewer", "alumni"
        ]

        for role in valid_roles:
            assert auth_service.validate_role(role)

        invalid_roles = ["invalid_role", "admin", "user", ""]
        for role in invalid_roles:
            assert not auth_service.validate_role(role)

    @pytest.mark.asyncio
    async def test_password_reset_token(self, auth_service, test_user):
        """Test password reset token generation and validation"""
        # Generate reset token
        token = auth_service.generate_password_reset_token(test_user["email"])

        assert token is not None
        assert isinstance(token, str)

        # Validate token
        email = auth_service.verify_password_reset_token(token)
        assert email == test_user["email"]

        # Test expired token (simulate by creating expired token)
        expired_token = auth_service.generate_password_reset_token(
            test_user["email"],
            expires_delta=timedelta(seconds=-1)
        )

        with pytest.raises(Exception):  # TokenExpiredError
            auth_service.verify_password_reset_token(expired_token)

    def test_account_lockout_logic(self, auth_service):
        """Test account lockout logic"""
        # Test successful login resets attempts
        auth_service.reset_failed_attempts("test@example.com")
        assert auth_service.get_failed_attempts("test@example.com") == 0

        # Test failed attempts increment
        for i in range(5):
            auth_service.record_failed_attempt("test@example.com")
            assert auth_service.get_failed_attempts("test@example.com") == i + 1

        # Test account lockout
        assert auth_service.is_account_locked("test@example.com")

        # Test unlock
        auth_service.unlock_account("test@example.com")
        assert not auth_service.is_account_locked("test@example.com")
        assert auth_service.get_failed_attempts("test@example.com") == 0

    @pytest.mark.asyncio
    async def test_session_management(self, auth_service, test_user):
        """Test user session management"""
        with patch('services.auth_service.app.database.auth_db') as mock_db:
            mock_collection = AsyncMock()
            mock_db.sessions = mock_collection

            session_data = {
                "user_id": "test_user_id",
                "token": "session_token",
                "expires_at": datetime.utcnow() + timedelta(hours=1)
            }

            # Mock session creation
            mock_collection.insert_one.return_value = AsyncMock()
            mock_collection.insert_one.return_value.inserted_id = "session_id"

            result = await auth_service.create_session(session_data)

            assert result["id"] == "session_id"
            mock_collection.insert_one.assert_called_once()

            # Test session validation
            mock_collection.find_one.return_value = session_data
            valid_session = await auth_service.validate_session("session_token")
            assert valid_session is not None

            # Test session invalidation
            mock_collection.delete_one.return_value = AsyncMock()
            await auth_service.invalidate_session("session_token")
            mock_collection.delete_one.assert_called_once()

    def test_security_headers_generation(self, auth_service):
        """Test security headers generation"""
        headers = auth_service.get_security_headers()

        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers

        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-XSS-Protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_audit_logging(self, auth_service, test_user):
        """Test audit logging functionality"""
        with patch('services.auth_service.app.database.auth_db') as mock_db:
            mock_collection = AsyncMock()
            mock_db.audit_logs = mock_collection

            audit_data = {
                "user_id": test_user.get("id"),
                "action": "login",
                "ip_address": "192.168.1.1",
                "user_agent": "Test Browser",
                "details": {"successful": True}
            }

            mock_collection.insert_one.return_value = AsyncMock()

            await auth_service.log_audit_event(audit_data)

            mock_collection.insert_one.assert_called_once()
            call_args = mock_collection.insert_one.call_args[0][0]

            assert call_args["user_id"] == audit_data["user_id"]
            assert call_args["action"] == audit_data["action"]
            assert call_args["ip_address"] == audit_data["ip_address"]
            assert call_args["user_agent"] == audit_data["user_agent"]
            assert call_args["details"] == audit_data["details"]
            assert "timestamp" in call_args

    def test_rate_limiting_logic(self, auth_service):
        """Test rate limiting logic"""
        client_ip = "192.168.1.1"
        endpoint = "/auth/login"

        # Test initial state
        assert not auth_service.is_rate_limited(client_ip, endpoint)

        # Simulate requests
        for i in range(10):
            auth_service.record_request(client_ip, endpoint)

        # Should be rate limited after threshold
        assert auth_service.is_rate_limited(client_ip, endpoint)

        # Test rate limit reset
        auth_service.reset_rate_limit(client_ip, endpoint)
        assert not auth_service.is_rate_limited(client_ip, endpoint)

    @pytest.mark.asyncio
    async def test_user_profile_updates(self, auth_service, test_user):
        """Test user profile update functionality"""
        with patch('services.auth_service.app.database.auth_db') as mock_db:
            mock_collection = AsyncMock()
            mock_db.users = mock_collection

            update_data = {
                "name": "Updated Name",
                "email": "updated@example.com"
            }

            mock_collection.update_one.return_value = AsyncMock()
            mock_collection.update_one.return_value.modified_count = 1

            result = await auth_service.update_user_profile(
                test_user["email"],
                update_data
            )

            assert result is True
            mock_collection.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_user_operations(self, auth_service):
        """Test bulk user operations"""
        with patch('services.auth_service.app.database.auth_db') as mock_db:
            mock_collection = AsyncMock()
            mock_db.users = mock_collection

            # Mock bulk user data
            users_data = [
                {"email": f"user{i}@example.com", "name": f"User {i}"}
                for i in range(5)
            ]

            mock_collection.insert_many.return_value = AsyncMock()
            mock_collection.insert_many.return_value.inserted_ids = [
                f"user_{i}_id" for i in range(5)
            ]

            result = await auth_service.bulk_create_users(users_data)

            assert len(result) == 5
            mock_collection.insert_many.assert_called_once()

    def test_password_policy_enforcement(self, auth_service):
        """Test password policy enforcement"""
        # Test valid passwords
        valid_passwords = [
            "ValidPass123!",
            "Complex@Password#456",
            "Str0ng!P@ssw0rd"
        ]

        for password in valid_passwords:
            assert auth_service.enforce_password_policy(password)

        # Test invalid passwords
        invalid_passwords = [
            "weak",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecial123"  # No special characters
        ]

        for password in invalid_passwords:
            assert not auth_service.enforce_password_policy(password)

    @pytest.mark.asyncio
    async def test_user_deactivation(self, auth_service, test_user):
        """Test user deactivation functionality"""
        with patch('services.auth_service.app.database.auth_db') as mock_db:
            mock_collection = AsyncMock()
            mock_db.users = mock_collection

            mock_collection.update_one.return_value = AsyncMock()
            mock_collection.update_one.return_value.modified_count = 1

            result = await auth_service.deactivate_user(test_user["email"])

            assert result is True
            mock_collection.update_one.assert_called_once()

            # Verify correct update operation
            call_args = mock_collection.update_one.call_args
            assert call_args[0][0] == {"email": test_user["email"]}
            assert call_args[0][1]["$set"]["is_active"] is False

    @pytest.mark.asyncio
    async def test_user_search_and_filtering(self, auth_service):
        """Test user search and filtering functionality"""
        with patch('services.auth_service.app.database.auth_db') as mock_db:
            mock_collection = AsyncMock()
            mock_db.users = mock_collection

            # Mock search results
            mock_users = [
                {"email": "student1@example.com", "name": "Student One", "role": "student"},
                {"email": "student2@example.com", "name": "Student Two", "role": "student"}
            ]

            mock_collection.find.return_value = mock_collection
            mock_collection.sort.return_value = mock_collection
            mock_collection.skip.return_value = mock_collection
            mock_collection.limit.return_value = mock_collection
            mock_collection.to_list.return_value = mock_users

            # Test search by role
            results = await auth_service.search_users(role="student")

            assert len(results) == 2
            assert all(user["role"] == "student" for user in results)

            # Test search by name
            mock_collection.reset_mock()
            mock_collection.find.return_value = mock_collection
            mock_collection.to_list.return_value = [mock_users[0]]

            results = await auth_service.search_users(name="Student One")
            assert len(results) == 1
            assert results[0]["name"] == "Student One"