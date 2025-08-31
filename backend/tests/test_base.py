"""
Base test classes and utilities for LMS backend testing.
"""
import pytest
from typing import Dict, Any
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorDatabase


class BaseTestCase:
    """Base class for all test cases."""

    @pytest.fixture(autouse=True)
    def setup_method(self, test_client, test_database):
        """Set up test method with client and database."""
        self.client: TestClient = test_client
        self.db: AsyncIOMotorDatabase = test_database

    def get_auth_headers(self, token: str) -> Dict[str, str]:
        """Get authorization headers for authenticated requests."""
        return {"Authorization": f"Bearer {token}"}

    def assert_success_response(self, response, status_code: int = 200):
        """Assert that response is successful."""
        assert response.status_code == status_code
        return response.json()

    def assert_error_response(self, response, status_code: int, error_detail: str = None):
        """Assert that response contains an error."""
        assert response.status_code == status_code
        if error_detail:
            assert error_detail in response.json().get("detail", "")

    async def create_test_user(self, **kwargs) -> Dict[str, Any]:
        """Create a test user in the database."""
        user_data = {
            "_id": kwargs.get("id", f"test_user_{len(str(id(self)))}"),
            "email": kwargs.get("email", f"test_{len(str(id(self)))}@example.com"),
            "name": kwargs.get("name", f"Test User {len(str(id(self)))}"),
            "role": kwargs.get("role", "student"),
            "password_hash": kwargs.get("password_hash", "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6fYzYXxQK"),  # "password"
            "created_at": kwargs.get("created_at", "2024-01-01T00:00:00Z")
        }
        await self.db.users.insert_one(user_data)
        return user_data

    async def create_test_course(self, owner_id: str, **kwargs) -> Dict[str, Any]:
        """Create a test course in the database."""
        course_data = {
            "_id": kwargs.get("id", f"test_course_{len(str(id(self)))}"),
            "owner_id": owner_id,
            "title": kwargs.get("title", f"Test Course {len(str(id(self)))}"),
            "audience": kwargs.get("audience", "Students"),
            "difficulty": kwargs.get("difficulty", "beginner"),
            "lessons": kwargs.get("lessons", []),
            "quiz": kwargs.get("quiz", []),
            "published": kwargs.get("published", True),
            "enrolled_user_ids": kwargs.get("enrolled_user_ids", []),
            "created_at": kwargs.get("created_at", "2024-01-01T00:00:00Z")
        }
        await self.db.courses.insert_one(course_data)
        return course_data

    def login_user(self, email: str, password: str = "password"):
        """Login user and return access token."""
        response = self.client.post("/api/auth/login", json={
            "email": email,
            "password": password
        })
        assert response.status_code == 200
        return response.json()["access_token"]


class AsyncBaseTestCase(BaseTestCase):
    """Base class for async test cases."""

    @pytest.fixture(autouse=True)
    async def setup_method(self, test_client, test_database):
        """Set up async test method."""
        self.client: TestClient = test_client
        self.db: AsyncIOMotorDatabase = test_database


# Test data generators
def generate_course_data(owner_id: str, **overrides):
    """Generate test course data."""
    base_data = {
        "owner_id": owner_id,
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
        "enrolled_user_ids": []
    }
    base_data.update(overrides)
    return base_data


def generate_user_data(**overrides):
    """Generate test user data."""
    base_data = {
        "email": "test@example.com",
        "name": "Test User",
        "role": "student",
        "password": "password"
    }
    base_data.update(overrides)
    return base_data


def generate_assignment_data(course_id: str, **overrides):
    """Generate test assignment data."""
    base_data = {
        "course_id": course_id,
        "title": "Test Assignment",
        "description": "Complete this assignment",
        "due_at": "2024-12-31T23:59:59Z",
        "rubric": ["Completeness", "Accuracy", "Creativity"]
    }
    base_data.update(overrides)
    return base_data