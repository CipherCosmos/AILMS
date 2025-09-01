"""
Pytest configuration and fixtures for LMS microservices tests
"""
import pytest
import asyncio
from typing import Dict, Any
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Test settings fixture"""
    # Override settings for testing
    original_env = settings.environment
    settings.environment = "test"
    yield settings
    settings.environment = original_env


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User",
        "role": "student"
    }


@pytest.fixture
def sample_course_data():
    """Sample course data for testing"""
    return {
        "id": "test_course_123",
        "title": "Test Course",
        "audience": "beginners",
        "difficulty": "intermediate",
        "owner_id": "test_user_123"
    }


@pytest.fixture
def sample_lesson_data():
    """Sample lesson data for testing"""
    return {
        "id": "test_lesson_123",
        "title": "Test Lesson",
        "content": "This is test lesson content",
        "course_id": "test_course_123"
    }


@pytest.fixture
def auth_headers(sample_user_data):
    """Mock authentication headers"""
    return {
        "Authorization": f"Bearer test_token_{sample_user_data['id']}",
        "X-User-ID": sample_user_data["id"],
        "X-User-Role": sample_user_data["role"]
    }


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token for testing"""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Cleanup test data after each test"""
    yield
    # Add cleanup logic here if needed