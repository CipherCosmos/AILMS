import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.testclient import TestClient
from main import app
from database import init_database, client
import os
from config import settings

# Test database configuration
TEST_DB_NAME = "test_lms_database"
TEST_MONGO_URL = "mongodb://localhost:27017"  # Use local MongoDB for tests

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_database():
    """Set up test database connection."""
    # Override settings for testing
    original_mongo_url = settings.mongo_url
    original_db_name = settings.db_name

    settings.mongo_url = TEST_MONGO_URL
    settings.db_name = TEST_DB_NAME

    # Initialize test database
    test_client = AsyncIOMotorClient(TEST_MONGO_URL)
    test_db = test_client[TEST_DB_NAME]

    # Clean up any existing data
    await test_db.drop_database()

    yield test_db

    # Cleanup
    await test_db.drop_database()
    test_client.close()

    # Restore original settings
    settings.mongo_url = original_mongo_url
    settings.db_name = original_db_name

@pytest.fixture
def test_client():
    """Create a test client for FastAPI app."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
async def test_user(test_database):
    """Create a test user in the database."""
    user_data = {
        "_id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User",
        "role": "student",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6fYzYXxQK",  # "password"
        "created_at": "2024-01-01T00:00:00Z"
    }

    await test_database.users.insert_one(user_data)
    return user_data

@pytest.fixture
async def test_instructor(test_database):
    """Create a test instructor in the database."""
    instructor_data = {
        "_id": "test_instructor_123",
        "email": "instructor@example.com",
        "name": "Test Instructor",
        "role": "instructor",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6fYzYXxQK",  # "password"
        "created_at": "2024-01-01T00:00:00Z"
    }

    await test_database.users.insert_one(instructor_data)
    return instructor_data

@pytest.fixture
async def test_course(test_database, test_instructor):
    """Create a test course in the database."""
    course_data = {
        "_id": "test_course_123",
        "owner_id": test_instructor["_id"],
        "title": "Test Course",
        "audience": "Students",
        "difficulty": "beginner",
        "lessons": [
            {
                "id": "lesson_1",
                "title": "Introduction",
                "content": "Welcome to the course",
                "order_index": 0
            }
        ],
        "quiz": [
            {
                "id": "quiz_1",
                "question": "What is 2+2?",
                "options": [
                    {"text": "3", "is_correct": False},
                    {"text": "4", "is_correct": True},
                    {"text": "5", "is_correct": False},
                    {"text": "6", "is_correct": False}
                ],
                "explanation": "Basic math"
            }
        ],
        "published": True,
        "enrolled_user_ids": ["test_user_123"],
        "created_at": "2024-01-01T00:00:00Z"
    }

    await test_database.courses.insert_one(course_data)
    return course_data

@pytest.fixture
async def auth_token(test_client, test_user):
    """Get authentication token for test user."""
    # Try login first (user might already exist)
    response = test_client.post("/api/auth/login", json={
        "email": test_user["email"],
        "password": "password"
    })
    if response.status_code != 200:
        # User doesn't exist, register first
        response = test_client.post("/api/auth/register", json={
            "email": test_user["email"],
            "name": test_user["name"],
            "password": "password"
        })
        if response.status_code == 200:
            # Now login
            response = test_client.post("/api/auth/login", json={
                "email": test_user["email"],
                "password": "password"
            })
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
async def instructor_token(test_client, test_instructor):
    """Get authentication token for test instructor."""
    # Try login first (user might already exist)
    response = test_client.post("/api/auth/login", json={
        "email": test_instructor["email"],
        "password": "password"
    })
    if response.status_code != 200:
        # User doesn't exist, register first
        response = test_client.post("/api/auth/register", json={
            "email": test_instructor["email"],
            "name": test_instructor["name"],
            "password": "password"
        })
        if response.status_code == 200:
            # Now login
            response = test_client.post("/api/auth/login", json={
                "email": test_instructor["email"],
                "password": "password"
            })
    assert response.status_code == 200
    return response.json()["access_token"]