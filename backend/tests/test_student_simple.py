"""
Simple tests for student APIs to avoid event loop issues.
"""
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

def test_student_endpoints_exist(client):
    """Test that student endpoints are accessible."""
    # Test study plan endpoint
    response = client.get("/api/student/study_plan")
    # Should return 401 (unauthorized) since no auth token
    assert response.status_code == 401

    # Test skill gaps endpoint
    response = client.get("/api/student/skill_gaps")
    assert response.status_code == 401

    # Test career readiness endpoint
    response = client.get("/api/student/career_readiness")
    assert response.status_code == 401

    # Test achievements endpoint
    response = client.get("/api/student/achievements")
    assert response.status_code == 401

    # Test learning analytics endpoint
    response = client.get("/api/student/learning_analytics")
    assert response.status_code == 401

def test_student_endpoints_with_invalid_token(client):
    """Test student endpoints with invalid token."""
    headers = {"Authorization": "Bearer invalid_token"}

    # Test study plan endpoint
    response = client.get("/api/student/study_plan", headers=headers)
    assert response.status_code == 401

    # Test skill gaps endpoint
    response = client.get("/api/student/skill_gaps", headers=headers)
    assert response.status_code == 401

def test_student_endpoints_with_wrong_role(client):
    """Test student endpoints with wrong user role."""
    # First register a user
    user_data = {
        "email": "test_student@example.com",
        "name": "Test Student",
        "password": "password123"
    }

    response = client.post("/api/auth/register", json=user_data)
    if response.status_code == 400:
        # User might already exist, try login
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
    else:
        assert response.status_code == 200
        # Login after registration
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # Test study plan endpoint - should work for student role
    response = client.get("/api/student/study_plan", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "weekly_hours" in data
    assert "focus_areas" in data

    # Test skill gaps endpoint
    response = client.get("/api/student/skill_gaps", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        assert "skill" in data[0]
        assert "current_level" in data[0]
        assert "target_level" in data[0]

    # Test career readiness endpoint
    response = client.get("/api/student/career_readiness", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "overall_score" in data
    assert "assessment" in data
    assert "recommended_careers" in data

    # Test achievements endpoint
    response = client.get("/api/student/achievements", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Test learning analytics endpoint
    response = client.get("/api/student/learning_analytics", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "timeframe" in data
    assert "total_sessions" in data
    assert "total_study_hours" in data

def test_student_endpoints_with_instructor_role(client):
    """Test student endpoints with instructor role (should fail)."""
    # Register an instructor
    user_data = {
        "email": "test_instructor@example.com",
        "name": "Test Instructor",
        "password": "password123",
        "role": "instructor"
    }

    response = client.post("/api/auth/register", json=user_data)
    if response.status_code == 400:
        # User might already exist, try login
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
    else:
        assert response.status_code == 200
        # Login after registration
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # Test study plan endpoint - should fail for instructor role
    response = client.get("/api/student/study_plan", headers=headers)
    assert response.status_code == 403

    # Test skill gaps endpoint - should fail for instructor role
    response = client.get("/api/student/skill_gaps", headers=headers)
    assert response.status_code == 403

    # Test career readiness endpoint - should fail for instructor role
    response = client.get("/api/student/career_readiness", headers=headers)
    assert response.status_code == 403

    # Test achievements endpoint - should fail for instructor role
    response = client.get("/api/student/achievements", headers=headers)
    assert response.status_code == 403

    # Test learning analytics endpoint - should fail for instructor role
    response = client.get("/api/student/learning_analytics", headers=headers)
    assert response.status_code == 403

def test_student_endpoints_response_structure(client):
    """Test that student endpoints return correct response structure."""
    # Register and login as student
    user_data = {
        "email": "test_student2@example.com",
        "name": "Test Student 2",
        "password": "password123"
    }

    response = client.post("/api/auth/register", json=user_data)
    if response.status_code == 400:
        # User might already exist, try login
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
    else:
        assert response.status_code == 200
        # Login after registration
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # Test study plan structure
    response = client.get("/api/student/study_plan", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "user_id" in data
    assert "weekly_hours" in data
    assert "focus_areas" in data
    assert "today_schedule" in data
    assert isinstance(data["focus_areas"], list)
    assert isinstance(data["today_schedule"], list)

    # Test skill gaps structure
    response = client.get("/api/student/skill_gaps", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        skill_gap = data[0]
        assert "skill" in skill_gap
        assert "current_level" in skill_gap
        assert "target_level" in skill_gap
        assert "gap_description" in skill_gap

    # Test career readiness structure
    response = client.get("/api/student/career_readiness", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "overall_score" in data
    assert "assessment" in data
    assert "skills_match" in data
    assert "recommended_careers" in data
    assert isinstance(data["recommended_careers"], list)

    # Test achievements structure
    response = client.get("/api/student/achievements", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        achievement = data[0]
        assert "title" in achievement
        assert "description" in achievement
        assert "earned_date" in achievement

    # Test learning analytics structure
    response = client.get("/api/student/learning_analytics", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "timeframe" in data
    assert "total_sessions" in data
    assert "total_study_hours" in data
    assert "average_productivity" in data
    assert "consistency_score" in data
    assert "daily_stats" in data
    assert isinstance(data["daily_stats"], list)