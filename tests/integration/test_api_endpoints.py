"""
Integration tests for API endpoints
"""
import pytest
from httpx import AsyncClient
from fastapi import FastAPI
import json


class TestAuthAPI:
    """Test authentication API endpoints"""

    @pytest.mark.asyncio
    async def test_user_registration(self, test_client: AsyncClient, test_user_data):
        """Test user registration endpoint"""
        response = await test_client.post(
            "/auth/register",
            json=test_user_data
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == test_user_data["email"]
        assert data["name"] == test_user_data["name"]
        assert data["role"] == test_user_data["role"]

    @pytest.mark.asyncio
    async def test_user_login(self, test_client: AsyncClient, test_user_data):
        """Test user login endpoint"""
        # First register the user
        await test_client.post("/auth/register", json=test_user_data)

        # Then try to login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }

        response = await test_client.post(
            "/auth/login",
            json=login_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_invalid_login(self, test_client: AsyncClient):
        """Test login with invalid credentials"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }

        response = await test_client.post(
            "/auth/login",
            json=login_data
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_token_refresh(self, test_client: AsyncClient, test_user_data, auth_headers):
        """Test token refresh endpoint"""
        # First login to get tokens
        login_response = await test_client.post(
            "/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )

        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token to get new access token
        response = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data

    @pytest.mark.asyncio
    async def test_protected_endpoint_access(self, test_client: AsyncClient, auth_headers):
        """Test access to protected endpoints"""
        response = await test_client.get(
            "/users/profile",
            headers=auth_headers
        )

        # Should succeed with valid token
        assert response.status_code in [200, 404]  # 404 if user doesn't exist yet

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, test_client: AsyncClient):
        """Test access to protected endpoints without authentication"""
        response = await test_client.get("/users/profile")

        assert response.status_code == 401


class TestCourseAPI:
    """Test course management API endpoints"""

    @pytest.mark.asyncio
    async def test_create_course(self, test_client: AsyncClient, test_course_data, auth_headers):
        """Test course creation endpoint"""
        response = await test_client.post(
            "/courses",
            json=test_course_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == test_course_data["title"]
        assert data["description"] == test_course_data["description"]

    @pytest.mark.asyncio
    async def test_get_course_list(self, test_client: AsyncClient, auth_headers):
        """Test course listing endpoint"""
        response = await test_client.get(
            "/courses",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_course_by_id(self, test_client: AsyncClient, test_course_data, auth_headers):
        """Test get course by ID endpoint"""
        # First create a course
        create_response = await test_client.post(
            "/courses",
            json=test_course_data,
            headers=auth_headers
        )

        course_id = create_response.json()["id"]

        # Then retrieve it
        response = await test_client.get(
            f"/courses/{course_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == course_id
        assert data["title"] == test_course_data["title"]

    @pytest.mark.asyncio
    async def test_update_course(self, test_client: AsyncClient, test_course_data, auth_headers):
        """Test course update endpoint"""
        # First create a course
        create_response = await test_client.post(
            "/courses",
            json=test_course_data,
            headers=auth_headers
        )

        course_id = create_response.json()["id"]

        # Update the course
        update_data = {
            "title": "Updated Course Title",
            "description": "Updated description"
        }

        response = await test_client.put(
            f"/courses/{course_id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]

    @pytest.mark.asyncio
    async def test_delete_course(self, test_client: AsyncClient, test_course_data, auth_headers):
        """Test course deletion endpoint"""
        # First create a course
        create_response = await test_client.post(
            "/courses",
            json=test_course_data,
            headers=auth_headers
        )

        course_id = create_response.json()["id"]

        # Delete the course
        response = await test_client.delete(
            f"/courses/{course_id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify course is deleted
        get_response = await test_client.get(
            f"/courses/{course_id}",
            headers=auth_headers
        )

        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_course_enrollment(self, test_client: AsyncClient, test_course_data, auth_headers):
        """Test course enrollment endpoint"""
        # First create a course
        create_response = await test_client.post(
            "/courses",
            json=test_course_data,
            headers=auth_headers
        )

        course_id = create_response.json()["id"]

        # Enroll in the course
        response = await test_client.post(
            f"/courses/{course_id}/enroll",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "enrollment_id" in data or "message" in data

    @pytest.mark.asyncio
    async def test_course_search(self, test_client: AsyncClient, auth_headers):
        """Test course search functionality"""
        search_params = {
            "query": "test",
            "category": "Test Category",
            "difficulty_level": "intermediate"
        }

        response = await test_client.get(
            "/courses/search",
            params=search_params,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAssessmentAPI:
    """Test assessment API endpoints"""

    @pytest.mark.asyncio
    async def test_create_assessment(self, test_client: AsyncClient, test_assessment_data, auth_headers):
        """Test assessment creation endpoint"""
        response = await test_client.post(
            "/assessments",
            json=test_assessment_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == test_assessment_data["title"]

    @pytest.mark.asyncio
    async def test_get_assessment_questions(self, test_client: AsyncClient, test_assessment_data, auth_headers):
        """Test get assessment questions endpoint"""
        # First create an assessment
        create_response = await test_client.post(
            "/assessments",
            json=test_assessment_data,
            headers=auth_headers
        )

        assessment_id = create_response.json()["id"]

        # Get questions
        response = await test_client.get(
            f"/assessments/{assessment_id}/questions",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == len(test_assessment_data["questions"])

    @pytest.mark.asyncio
    async def test_submit_assessment(self, test_client: AsyncClient, test_assessment_data, auth_headers):
        """Test assessment submission endpoint"""
        # First create an assessment
        create_response = await test_client.post(
            "/assessments",
            json=test_assessment_data,
            headers=auth_headers
        )

        assessment_id = create_response.json()["id"]

        # Submit answers
        submission_data = {
            "answers": [
                {"question_id": "q1", "answer": 1}
            ]
        }

        response = await test_client.post(
            f"/assessments/{assessment_id}/submit",
            json=submission_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "passed" in data
        assert isinstance(data["score"], (int, float))

    @pytest.mark.asyncio
    async def test_get_assessment_results(self, test_client: AsyncClient, test_assessment_data, auth_headers):
        """Test get assessment results endpoint"""
        # First create and submit an assessment
        create_response = await test_client.post(
            "/assessments",
            json=test_assessment_data,
            headers=auth_headers
        )

        assessment_id = create_response.json()["id"]

        submission_data = {
            "answers": [
                {"question_id": "q1", "answer": 1}
            ]
        }

        await test_client.post(
            f"/assessments/{assessment_id}/submit",
            json=submission_data,
            headers=auth_headers
        )

        # Get results
        response = await test_client.get(
            f"/assessments/{assessment_id}/results",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "total_questions" in data
        assert "correct_answers" in data

    @pytest.mark.asyncio
    async def test_assessment_analytics(self, test_client: AsyncClient, auth_headers):
        """Test assessment analytics endpoint"""
        response = await test_client.get(
            "/assessments/analytics",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_assessments" in data
        assert "average_score" in data
        assert "completion_rate" in data


class TestAnalyticsAPI:
    """Test analytics API endpoints"""

    @pytest.mark.asyncio
    async def test_user_progress_analytics(self, test_client: AsyncClient, auth_headers):
        """Test user progress analytics endpoint"""
        response = await test_client.get(
            "/analytics/progress",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "completed_courses" in data
        assert "in_progress_courses" in data
        assert "total_study_time" in data

    @pytest.mark.asyncio
    async def test_course_performance_analytics(self, test_client: AsyncClient, auth_headers):
        """Test course performance analytics endpoint"""
        response = await test_client.get(
            "/analytics/courses/performance",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            course = data[0]
            assert "course_id" in course
            assert "average_score" in course
            assert "completion_rate" in course

    @pytest.mark.asyncio
    async def test_learning_insights(self, test_client: AsyncClient, auth_headers):
        """Test learning insights endpoint"""
        response = await test_client.get(
            "/analytics/insights",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "strengths" in data
        assert "weaknesses" in data
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_engagement_metrics(self, test_client: AsyncClient, auth_headers):
        """Test engagement metrics endpoint"""
        response = await test_client.get(
            "/analytics/engagement",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "active_users" in data
        assert "session_duration" in data
        assert "feature_usage" in data


class TestFileAPI:
    """Test file management API endpoints"""

    @pytest.mark.asyncio
    async def test_file_upload(self, test_client: AsyncClient, auth_headers):
        """Test file upload endpoint"""
        # Create test file content
        file_content = b"Test file content for upload"
        files = {"file": ("test.txt", file_content, "text/plain")}

        response = await test_client.post(
            "/files/upload",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert "file_id" in data
        assert "filename" in data
        assert data["filename"] == "test.txt"

    @pytest.mark.asyncio
    async def test_file_download(self, test_client: AsyncClient, auth_headers):
        """Test file download endpoint"""
        # First upload a file
        file_content = b"Test file content for download"
        files = {"file": ("test.txt", file_content, "text/plain")}

        upload_response = await test_client.post(
            "/files/upload",
            files=files,
            headers=auth_headers
        )

        file_id = upload_response.json()["file_id"]

        # Download the file
        response = await test_client.get(
            f"/files/{file_id}/download",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.content == file_content

    @pytest.mark.asyncio
    async def test_file_metadata(self, test_client: AsyncClient, auth_headers):
        """Test file metadata retrieval endpoint"""
        # First upload a file
        file_content = b"Test file content"
        files = {"file": ("test.txt", file_content, "text/plain")}

        upload_response = await test_client.post(
            "/files/upload",
            files=files,
            headers=auth_headers
        )

        file_id = upload_response.json()["file_id"]

        # Get file metadata
        response = await test_client.get(
            f"/files/{file_id}/metadata",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.txt"
        assert "size" in data
        assert "upload_date" in data
        assert "content_type" in data

    @pytest.mark.asyncio
    async def test_file_deletion(self, test_client: AsyncClient, auth_headers):
        """Test file deletion endpoint"""
        # First upload a file
        file_content = b"Test file content"
        files = {"file": ("test.txt", file_content, "text/plain")}

        upload_response = await test_client.post(
            "/files/upload",
            files=files,
            headers=auth_headers
        )

        file_id = upload_response.json()["file_id"]

        # Delete the file
        response = await test_client.delete(
            f"/files/{file_id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify file is deleted
        download_response = await test_client.get(
            f"/files/{file_id}/download",
            headers=auth_headers
        )

        assert download_response.status_code == 404


class TestNotificationAPI:
    """Test notification API endpoints"""

    @pytest.mark.asyncio
    async def test_send_notification(self, test_client: AsyncClient, auth_headers):
        """Test send notification endpoint"""
        notification_data = {
            "recipient_id": "user123",
            "type": "course_reminder",
            "title": "Course Reminder",
            "message": "Don't forget to complete your assignment!",
            "priority": "medium"
        }

        response = await test_client.post(
            "/notifications/send",
            json=notification_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert "notification_id" in data
        assert data["type"] == notification_data["type"]

    @pytest.mark.asyncio
    async def test_get_notifications(self, test_client: AsyncClient, auth_headers):
        """Test get notifications endpoint"""
        response = await test_client.get(
            "/notifications",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "notifications" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_mark_notification_read(self, test_client: AsyncClient, auth_headers):
        """Test mark notification as read endpoint"""
        # First send a notification
        notification_data = {
            "recipient_id": "user123",
            "type": "test",
            "title": "Test Notification",
            "message": "This is a test notification"
        }

        send_response = await test_client.post(
            "/notifications/send",
            json=notification_data,
            headers=auth_headers
        )

        notification_id = send_response.json()["notification_id"]

        # Mark as read
        response = await test_client.put(
            f"/notifications/{notification_id}/read",
            headers=auth_headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_bulk_notification_operations(self, test_client: AsyncClient, auth_headers):
        """Test bulk notification operations"""
        # Mark all notifications as read
        response = await test_client.put(
            "/notifications/mark-all-read",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Get unread count
        response = await test_client.get(
            "/notifications/unread-count",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)


class TestHealthAPI:
    """Test health check API endpoints"""

    @pytest.mark.asyncio
    async def test_health_check(self, test_client: AsyncClient):
        """Test basic health check endpoint"""
        response = await test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_detailed_health_check(self, test_client: AsyncClient):
        """Test detailed health check endpoint"""
        response = await test_client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "database" in data["services"]
        assert "redis" in data["services"]

    @pytest.mark.asyncio
    async def test_service_health_checks(self, test_client: AsyncClient):
        """Test individual service health checks"""
        services = ["auth", "course", "assessment", "analytics", "file", "notification"]

        for service in services:
            response = await test_client.get(f"/health/{service}")

            # Service might not be running, but endpoint should exist
            assert response.status_code in [200, 503]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data


class TestRateLimiting:
    """Test rate limiting functionality"""

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, test_client: AsyncClient):
        """Test that rate limiting is enforced"""
        # Make multiple requests to a rate-limited endpoint
        responses = []
        for i in range(15):  # Exceed typical rate limit
            response = await test_client.post(
                "/auth/login",
                json={
                    "email": f"user{i}@example.com",
                    "password": "password123"
                }
            )
            responses.append(response.status_code)

        # Should have some 429 (Too Many Requests) responses
        assert 429 in responses

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, test_client: AsyncClient):
        """Test rate limit headers are present"""
        response = await test_client.get("/health")

        # Check for rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers


class TestErrorHandling:
    """Test error handling across API endpoints"""

    @pytest.mark.asyncio
    async def test_404_errors(self, test_client: AsyncClient, auth_headers):
        """Test 404 error responses"""
        response = await test_client.get(
            "/nonexistent/endpoint",
            headers=auth_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_422_validation_errors(self, test_client: AsyncClient, auth_headers):
        """Test 422 validation error responses"""
        # Send invalid data
        response = await test_client.post(
            "/courses",
            json={"invalid": "data"},
            headers=auth_headers
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_500_server_errors(self, test_client: AsyncClient, auth_headers):
        """Test 500 server error handling"""
        # This would typically happen with database connection issues
        # For now, just verify error structure
        response = await test_client.get(
            "/health",
            headers=auth_headers
        )

        # Should not be 500 under normal circumstances
        assert response.status_code != 500

    @pytest.mark.asyncio
    async def test_cors_headers(self, test_client: AsyncClient):
        """Test CORS headers are properly set"""
        response = await test_client.options("/health")

        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers

    @pytest.mark.asyncio
    async def test_security_headers(self, test_client: AsyncClient):
        """Test security headers are present"""
        response = await test_client.get("/health")

        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security"
        ]

        for header in security_headers:
            assert header in response.headers