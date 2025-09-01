"""
Pytest configuration and fixtures for LMS backend testing
"""
import pytest
import asyncio
from typing import Dict, Any, AsyncGenerator
from httpx import AsyncClient
import motor.motor_asyncio
import redis.asyncio as redis
from fastapi import FastAPI
from shared.config.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_mongo_client():
    """MongoDB test client fixture"""
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_url)
    yield client
    client.close()


@pytest.fixture(scope="session")
async def test_redis_client():
    """Redis test client fixture"""
    client = redis.Redis.from_url(settings.redis_url)
    yield client
    await client.close()


@pytest.fixture(scope="session")
async def test_database(test_mongo_client):
    """Test database fixture"""
    db = test_mongo_client["lms_test"]
    yield db
    # Clean up after tests
    await test_mongo_client.drop_database("lms_test")


@pytest.fixture
async def test_app():
    """Test FastAPI application fixture"""
    from services.api_gateway.app.main import create_application
    app = create_application()
    yield app


@pytest.fixture
async def test_client(test_app):
    """HTTP test client fixture"""
    async with AsyncClient(app=test_app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def auth_headers(test_client):
    """Authentication headers fixture"""
    # This would typically create a test user and return auth headers
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
async def test_user_data():
    """Test user data fixture"""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "password": "TestPassword123!",
        "role": "student"
    }


@pytest.fixture
async def test_course_data():
    """Test course data fixture"""
    return {
        "title": "Test Course",
        "description": "A test course for testing purposes",
        "instructor_id": "test-instructor-id",
        "category": "Test Category",
        "difficulty_level": "intermediate"
    }


@pytest.fixture
async def test_assessment_data():
    """Test assessment data fixture"""
    return {
        "title": "Test Assessment",
        "description": "A test assessment",
        "course_id": "test-course-id",
        "questions": [
            {
                "question": "What is 2+2?",
                "options": ["3", "4", "5", "6"],
                "correct_answer": 1,
                "points": 10
            }
        ],
        "time_limit": 30,
        "passing_score": 70
    }


@pytest.fixture
async def cleanup_test_data(test_database):
    """Fixture to clean up test data after each test"""
    yield
    # Clean up collections
    collections = await test_database.list_collection_names()
    for collection in collections:
        await test_database[collection].delete_many({})


@pytest.fixture(scope="session")
def performance_config():
    """Performance test configuration"""
    return {
        "concurrent_users": 100,
        "test_duration": 60,  # seconds
        "ramp_up_time": 10,   # seconds
        "response_time_threshold": 2.0,  # seconds
        "error_rate_threshold": 0.05     # 5%
    }


@pytest.fixture(scope="session")
def security_config():
    """Security test configuration"""
    return {
        "sql_injection_payloads": [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users; --"
        ],
        "xss_payloads": [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')"
        ],
        "rate_limit_threshold": 100,  # requests per minute
        "auth_bypass_attempts": 10
    }