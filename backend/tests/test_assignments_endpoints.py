"""
Test assignment-related endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

def test_create_assignment_endpoint():
    """Test assignment creation endpoint."""
    client = TestClient(app)

    # Test without authentication
    assignment_data = {
        "title": "Test Assignment",
        "description": "Complete this assignment",
        "due_at": "2024-12-31T23:59:59Z",
        "rubric": ["Completeness", "Accuracy"]
    }

    response = client.post("/api/assignments", json=assignment_data)
    assert response.status_code == 401

def test_list_assignments_endpoint():
    """Test list assignments endpoint."""
    client = TestClient(app)

    # Test without authentication
    response = client.get("/api/assignments")
    assert response.status_code == 401

def test_get_assignment_endpoint():
    """Test get specific assignment endpoint."""
    client = TestClient(app)

    # Test without authentication
    response = client.get("/api/assignments/test_assignment_id")
    assert response.status_code == 401

def test_update_assignment_endpoint():
    """Test update assignment endpoint."""
    client = TestClient(app)

    # Test without authentication
    update_data = {"title": "Updated Assignment"}
    response = client.put("/api/assignments/test_assignment_id", json=update_data)
    assert response.status_code == 401

def test_delete_assignment_endpoint():
    """Test delete assignment endpoint."""
    client = TestClient(app)

    # Test without authentication
    response = client.delete("/api/assignments/test_assignment_id")
    assert response.status_code == 401

def test_submit_assignment_endpoint():
    """Test assignment submission endpoint."""
    client = TestClient(app)

    # Test without authentication
    submission_data = {
        "text_answer": "This is my answer",
        "file_ids": []
    }

    response = client.post("/api/assignments/test_assignment_id/submit", json=submission_data)
    assert response.status_code == 401

def test_get_submissions_endpoint():
    """Test get assignment submissions endpoint."""
    client = TestClient(app)

    # Test without authentication
    response = client.get("/api/assignments/test_assignment_id/submissions")
    assert response.status_code == 401

def test_grade_submission_endpoint():
    """Test grade submission endpoint."""
    client = TestClient(app)

    # Test without authentication
    grade_data = {
        "grade": 85,
        "feedback": "Good work!"
    }

    response = client.post("/api/assignments/submissions/test_submission_id/grade", json=grade_data)
    assert response.status_code == 401

def test_get_my_submissions_endpoint():
    """Test get my submissions endpoint."""
    client = TestClient(app)

    # Test without authentication
    response = client.get("/api/assignments/my_submissions")
    assert response.status_code == 401