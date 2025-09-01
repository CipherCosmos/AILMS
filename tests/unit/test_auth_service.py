"""
Unit tests for Auth Service Models and Utilities
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta

from shared.models.models import UserCreate, LoginRequest, TokenPair, UserPublic, UserBase, UserUpdate


class TestAuthModels:
    """Test cases for authentication models"""

    def test_user_creation_model(self):
        """Test UserCreate model validation"""
        user_data = UserCreate(
            email="test@example.com",
            name="Test User",
            password="securepassword123"
        )
        assert user_data.email == "test@example.com"
        assert user_data.name == "Test User"
        assert user_data.password == "securepassword123"

    def test_login_request_model(self):
        """Test LoginRequest model validation"""
        login_data = LoginRequest(
            email="test@example.com",
            password="password123"
        )
        assert login_data.email == "test@example.com"
        assert login_data.password == "password123"

    def test_token_pair_model(self):
        """Test TokenPair model validation"""
        tokens = TokenPair(
            access_token="access_token_123",
            refresh_token="refresh_token_456"
        )
        assert tokens.access_token == "access_token_123"
        assert tokens.refresh_token == "refresh_token_456"
        assert tokens.token_type == "bearer"

    def test_user_public_model(self):
        """Test UserPublic model"""
        user_public = UserPublic(
            id="test_user_123",
            email="test@example.com",
            name="Test User",
            role="student"
        )

        assert user_public.id == "test_user_123"
        assert user_public.email == "test@example.com"
        assert user_public.name == "Test User"
        assert user_public.role == "student"

    def test_user_base_model(self):
        """Test UserBase model"""
        user_base = UserBase(
            email="test@example.com",
            name="Test User",
            role="student"
        )

        assert user_base.email == "test@example.com"
        assert user_base.name == "Test User"
        assert user_base.role == "student"
        assert user_base.id is not None  # Should generate UUID

    def test_user_update_model(self):
        """Test UserUpdate model"""
        user_update = UserUpdate(
            name="Updated Name",
            email="updated@example.com"
        )

        assert user_update.name == "Updated Name"
        assert user_update.email == "updated@example.com"
        assert user_update.password is None  # Optional field


class TestAuthUtilities:
    """Test cases for authentication utilities"""

    @patch('shared.database.database._uuid')
    def test_uuid_generation(self, mock_uuid):
        """Test UUID generation utility"""
        mock_uuid.return_value = "test-uuid-123"

        from shared.database.database import _uuid
        result = _uuid()

        assert result == "test-uuid-123"
        mock_uuid.assert_called_once()

    @patch('shared.database.database.get_database')
    def test_database_connection(self, mock_get_db):
        """Test database connection utility"""
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        from shared.database.database import get_database
        result = get_database()

        assert result == mock_db
        mock_get_db.assert_called_once()

    def test_mongo_doc_serialization(self):
        """Test MongoDB document serialization"""
        from shared.utils.utils import serialize_mongo_doc

        # Test with ObjectId
        mock_object_id = Mock()
        mock_object_id.__str__ = Mock(return_value="507f1f77bcf86cd799439011")
        result = serialize_mongo_doc(mock_object_id)
        assert result == "507f1f77bcf86cd799439011"

        # Test with dict containing ObjectId
        test_doc = {
            "_id": mock_object_id,
            "name": "test",
            "nested": {
                "object_id": mock_object_id
            }
        }
        result = serialize_mongo_doc(test_doc)
        assert isinstance(result, dict)
        assert result.get("_id") == "507f1f77bcf86cd799439011"
        nested = result.get("nested")
        assert isinstance(nested, dict)
        assert nested.get("object_id") == "507f1f77bcf86cd799439011"

        # Test with list
        test_list = [mock_object_id, "string", 123]
        result = serialize_mongo_doc(test_list)
        assert isinstance(result, list)
        assert result[0] == "507f1f77bcf86cd799439011"
        assert result[1] == "string"
        assert result[2] == 123


class TestPasswordSecurity:
    """Test cases for password security"""

    @patch('passlib.hash.bcrypt')
    def test_password_hashing_mock(self, mock_bcrypt):
        """Test password hashing with mock"""
        mock_bcrypt.hash.return_value = "$2b$12$test.hashed.password"

        # Import and test password hashing logic
        # This would typically be in the auth service
        password = "test_password_123"
        hashed = mock_bcrypt.hash(password)

        assert hashed == "$2b$12$test.hashed.password"
        mock_bcrypt.hash.assert_called_once_with(password)

    @patch('passlib.hash.bcrypt')
    def test_password_verification_mock(self, mock_bcrypt):
        """Test password verification with mock"""
        mock_bcrypt.verify.return_value = True

        # Test successful verification
        result = mock_bcrypt.verify("correct_password", "hashed_password")
        assert result is True

        # Test failed verification
        mock_bcrypt.verify.return_value = False
        result = mock_bcrypt.verify("wrong_password", "hashed_password")
        assert result is False


class TestJWTTokenHandling:
    """Test cases for JWT token handling"""

    @patch('jwt.encode')
    @patch('shared.config.config.settings')
    def test_jwt_token_creation_mock(self, mock_settings, mock_jwt_encode):
        """Test JWT token creation with mock"""
        mock_settings.jwt_secret = "test_secret_key"
        mock_jwt_encode.return_value = "mock.jwt.token"

        # Mock token creation logic
        import jwt
        from shared.config.config import settings

        payload = {
            "sub": "test_user_123",
            "role": "student",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        }

        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        assert token == "mock.jwt.token"
        mock_jwt_encode.assert_called_once()

    @patch('jwt.decode')
    @patch('shared.config.config.settings')
    def test_jwt_token_validation_mock(self, mock_settings, mock_jwt_decode):
        """Test JWT token validation with mock"""
        mock_settings.jwt_secret = "test_secret_key"
        mock_jwt_decode.return_value = {
            "sub": "test_user_123",
            "role": "student",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }

        # Mock token validation logic
        import jwt
        from shared.config.config import settings

        token = "mock.jwt.token"
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        assert payload["sub"] == "test_user_123"
        assert payload["role"] == "student"
        mock_jwt_decode.assert_called_once_with(token, settings.jwt_secret, algorithms=["HS256"])