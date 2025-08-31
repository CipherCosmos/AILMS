"""
Integration tests with real data to verify backend functionality.
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from config import settings

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

@pytest.mark.asyncio
async def test_real_database_connection():
    """Test that we can connect to the real database."""
    # Use the actual database connection
    client = AsyncIOMotorClient(settings.mongo_url)
    db = client[settings.db_name]

    # Test basic database operations
    test_collection = db.test_collection

    # Insert a test document
    test_doc = {"test_field": "test_value", "number": 42}
    result = await test_collection.insert_one(test_doc)
    assert result.inserted_id is not None

    # Find the document
    found_doc = await test_collection.find_one({"_id": result.inserted_id})
    assert found_doc is not None
    assert found_doc["test_field"] == "test_value"
    assert found_doc["number"] == 42

    # Clean up
    await test_collection.delete_one({"_id": result.inserted_id})
    client.close()

def test_backend_startup():
    """Test that the backend starts up correctly."""
    client = TestClient(app)

    # Test root endpoint
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "AI LMS Backend" in data["message"]

    # Test API root
    response = client.get("/api/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

def test_cors_headers():
    """Test that CORS headers are properly set."""
    client = TestClient(app)

    response = client.options("/api/auth/register", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type"
    })

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers
    assert "access-control-allow-headers" in response.headers

def test_websocket_endpoint():
    """Test WebSocket endpoint availability."""
    client = TestClient(app)

    # Test WebSocket test endpoint
    response = client.get("/ws-test")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "WebSocket endpoint available" in data["message"]

def test_auth_endpoints_availability():
    """Test that authentication endpoints are available."""
    client = TestClient(app)

    endpoints = [
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/refresh",
        "/api/auth/me"
    ]

    for endpoint in endpoints:
        response = client.options(endpoint)
        # Should return 200 for OPTIONS or 405 if method not allowed
        assert response.status_code in [200, 405]

def test_course_endpoints_availability():
    """Test that course endpoints are available."""
    client = TestClient(app)

    endpoints = [
        "/api/courses",
        "/api/courses/basic_recommendations",
        "/api/courses/learning_path",
        "/api/courses/course_recommendations"
    ]

    for endpoint in endpoints:
        response = client.options(endpoint)
        assert response.status_code in [200, 405]

def test_ai_endpoints_availability():
    """Test that AI-powered endpoints are available."""
    client = TestClient(app)

    endpoints = [
        "/api/courses/ai/generate_course",
        "/api/courses/ai/learning_path/test_user",
        "/api/courses/ai/course_insights/test_course",
        "/api/courses/ai/generate_course_content",
        "/api/courses/ai/analyze_student_performance/test_user"
    ]

    for endpoint in endpoints:
        response = client.options(endpoint)
        assert response.status_code in [200, 405]

def test_error_handling():
    """Test error handling for invalid requests."""
    client = TestClient(app)

    # Test invalid JSON
    response = client.post("/api/auth/register",
                          data="invalid json",
                          headers={"Content-Type": "application/json"})
    assert response.status_code == 422  # Validation error

    # Test non-existent endpoint
    response = client.get("/api/nonexistent")
    assert response.status_code == 404

def test_content_type_validation():
    """Test that API properly validates content types."""
    client = TestClient(app)

    # Test with wrong content type
    response = client.post("/api/auth/register",
                          data="not json",
                          headers={"Content-Type": "text/plain"})
    assert response.status_code == 422

def test_rate_limiting_placeholder():
    """Test that we have rate limiting considerations (placeholder)."""
    client = TestClient(app)

    # This is a placeholder test - in production you'd implement rate limiting
    # For now, just verify the endpoint exists and handles requests
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password"
    })
    # Should return 401 (unauthorized) not 429 (rate limited)
    assert response.status_code == 401

def test_database_models_import():
    """Test that all database models can be imported."""
    try:
        from models import (
            UserBase, UserCreate, UserPublic, LoginRequest,
            Course, CourseCreate, CourseLesson, QuizQuestion,
            Assignment, Submission, Notification, Certificate
        )
        # If we get here, all imports succeeded
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import models: {e}")

def test_utils_functions():
    """Test utility functions."""
    from utils import serialize_mongo_doc
    from bson import ObjectId

    # Test serialization of ObjectId
    doc = {"_id": ObjectId("507f1f77bcf86cd799439011"), "name": "test"}
    result = serialize_mongo_doc(doc)
    assert result["_id"] == "507f1f77bcf86cd799439011"
    assert result["name"] == "test"

    # Test serialization of list with ObjectId
    doc_list = [ObjectId("507f1f77bcf86cd799439011"), "string"]
    result = serialize_mongo_doc(doc_list)
    assert result[0] == "507f1f77bcf86cd799439011"
    assert result[1] == "string"

def test_config_loading():
    """Test that configuration loads properly."""
    from config import settings

    # Test that required settings exist
    assert hasattr(settings, 'mongo_url')
    assert hasattr(settings, 'db_name')
    assert hasattr(settings, 'jwt_secret')
    assert hasattr(settings, 'access_expire_min')
    assert hasattr(settings, 'refresh_expire_days')

    # Test that settings have reasonable values
    assert isinstance(settings.mongo_url, str)
    assert len(settings.mongo_url) > 0
    assert isinstance(settings.db_name, str)
    assert len(settings.db_name) > 0

def test_auth_dependencies():
    """Test authentication dependencies can be imported."""
    try:
        from auth import _current_user, _require_role, _create_tokens
        # If we get here, all auth functions can be imported
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import auth functions: {e}")

def test_database_functions():
    """Test database utility functions can be imported."""
    try:
        from database import get_database, init_database, _find_one, _update_one
        # If we get here, all database functions can be imported
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import database functions: {e}")

def test_route_modules_import():
    """Test that all route modules can be imported."""
    route_modules = [
        'routes.courses',
        'routes.assignments',
        'routes.files',
        'routes.chat',
        'routes.discussions',
        'routes.analytics',
        'routes.notifications',
        'routes.profile',
        'routes.rbac',
        'routes.assessment',
        'routes.marketplace',
        'routes.wellbeing',
        'routes.career',
        'routes.proctoring',
        'routes.alumni',
        'routes.student',
        'routes.instructor',
        'routes.admin',
        'routes.parent',
        'routes.reviewer',
        'routes.integrations',
        'routes.ai_ethics'
    ]

    for module_name in route_modules:
        try:
            __import__(module_name)
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")

def test_main_app_structure():
    """Test that the main app has the expected structure."""
    from main import app

    # Test that app has expected attributes
    assert hasattr(app, 'routes')
    assert hasattr(app, 'middleware')
    assert hasattr(app, 'exception_handlers')

    # Test that we have routes
    routes = [route for route in app.routes]
    assert len(routes) > 0

    # Test that we have middleware
    assert len(app.user_middleware) > 0

def test_api_router_inclusion():
    """Test that API router is properly included."""
    from main import app, api

    # Check that API routes are included in main app
    api_routes = [route for route in api.routes]
    assert len(api_routes) > 0

    # Check that main app has API routes
    main_routes = [route for route in app.routes if hasattr(route, 'path') and route.path.startswith('/api')]
    assert len(main_routes) > 0

def test_websocket_manager():
    """Test WebSocket manager functionality."""
    from main import manager

    # Test manager initialization
    assert hasattr(manager, 'active_connections')
    assert isinstance(manager.active_connections, list)

    # Test manager methods
    assert hasattr(manager, 'connect')
    assert hasattr(manager, 'disconnect')
    assert hasattr(manager, 'send_personal_message')
    assert hasattr(manager, 'broadcast')