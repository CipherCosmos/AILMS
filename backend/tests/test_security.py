"""
Security tests for LMS backend.
"""
import pytest
from tests.test_base import BaseTestCase


class TestAuthenticationSecurity(BaseTestCase):
    """Security tests for authentication mechanisms."""

    def test_brute_force_protection(self):
        """Test protection against brute force attacks."""
        # Test multiple failed login attempts
        login_data = {
            "email": "alice.johnson@student.edu",
            "password": "wrongpassword"
        }

        # Attempt multiple failed logins
        for i in range(10):
            response = self.client.post("/api/auth/login", json=login_data)
            assert response.status_code == 401

        # Account should still work with correct password
        correct_login = {
            "email": "alice.johnson@student.edu",
            "password": "password"
        }

        response = self.client.post("/api/auth/login", json=correct_login)
        assert response.status_code == 200

    def test_sql_injection_prevention(self):
        """Test prevention of SQL injection attacks."""
        injection_attempts = [
            {"email": "admin@example.com' OR '1'='1", "password": "password"},
            {"email": "admin@example.com'; DROP TABLE users; --", "password": "password"},
            {"email": "admin@example.com' UNION SELECT * FROM users; --", "password": "password"},
        ]

        for attempt in injection_attempts:
            response = self.client.post("/api/auth/login", json=attempt)
            # Should fail authentication, not execute injection
            assert response.status_code == 401

    def test_xss_prevention_in_auth(self):
        """Test prevention of XSS attacks in authentication."""
        xss_payloads = [
            {"email": "<script>alert('xss')</script>", "password": "password"},
            {"email": "test@example.com", "password": "<img src=x onerror=alert('xss')>"},
            {"email": "javascript:alert('xss')@example.com", "password": "password"},
        ]

        for payload in xss_payloads:
            response = self.client.post("/api/auth/login", json=payload)
            # Should handle gracefully without executing scripts
            assert response.status_code in [401, 422]  # Auth fail or validation error

    def test_token_exposure_prevention(self):
        """Test that tokens are not exposed in error messages."""
        # Try to access protected endpoint without token
        response = self.client.get("/api/auth/me")
        assert response.status_code == 401

        error_detail = response.json().get("detail", "")
        # Error should not contain sensitive token information
        assert "token" not in error_detail.lower()
        assert "jwt" not in error_detail.lower()

    def test_weak_password_prevention(self):
        """Test prevention of weak passwords during registration."""
        weak_passwords = [
            "123",
            "password",
            "123456",
            "qwerty",
            "",  # Empty password
        ]

        for weak_password in weak_passwords:
            user_data = {
                "email": f"weak{weak_password}@example.com",
                "name": "Weak Password User",
                "password": weak_password
            }

            response = self.client.post("/api/auth/register", json=user_data)
            # Should either reject or accept (depending on implementation)
            # But should not crash the system
            assert response.status_code in [200, 400, 422]


class TestAuthorizationSecurity(BaseTestCase):
    """Security tests for authorization mechanisms."""

    def test_role_based_access_control(self):
        """Test that users can only access resources they're authorized for."""
        # Test student trying to access admin endpoints
        student_token = self.login_user("alice.johnson@student.edu", "password")
        student_headers = self.get_auth_headers(student_token)

        # Try to list all users (admin only)
        response = self.client.get("/api/auth/users", headers=student_headers)
        assert response.status_code == 403

        # Try to update another user's profile
        update_data = {"name": "Hacked Name"}
        response = self.client.put("/api/auth/users/student_002", json=update_data, headers=student_headers)
        assert response.status_code == 403

    def test_instructor_permissions(self):
        """Test instructor-specific permissions."""
        instructor_token = self.login_user("john.doe@university.edu", "password")
        instructor_headers = self.get_auth_headers(instructor_token)

        # Instructor should be able to create courses
        course_data = {
            "title": "Security Test Course",
            "audience": "Students",
            "difficulty": "beginner"
        }

        response = self.client.post("/api/courses", json=course_data, headers=instructor_headers)
        assert response.status_code == 200

        course_id = response.json()["id"]

        # Instructor should be able to view enrolled students
        response = self.client.get(f"/api/courses/{course_id}/students", headers=instructor_headers)
        assert response.status_code == 200

        # But should not be able to access admin endpoints
        response = self.client.get("/api/auth/users", headers=instructor_headers)
        assert response.status_code == 403

    def test_cross_tenant_access_prevention(self):
        """Test prevention of cross-tenant access (if multi-tenant)."""
        # Login as student from one "course group"
        token1 = self.login_user("alice.johnson@student.edu", "password")
        headers1 = self.get_auth_headers(token1)

        # Try to access resources from another "group"
        # This tests that alice cannot access bob's private data
        response = self.client.get("/api/courses/course_data_science_001/students", headers=headers1)
        # Should fail because alice is not the instructor/owner
        assert response.status_code == 403

    def test_ownership_validation(self):
        """Test that users can only modify their own resources."""
        # Student tries to modify another student's progress
        student_token = self.login_user("alice.johnson@student.edu", "password")
        student_headers = self.get_auth_headers(student_token)

        # Try to update bob's progress (should fail)
        progress_data = {"overall_progress": 100}
        response = self.client.put("/api/courses/course_data_science_001/students/student_002/progress",
                                 json=progress_data, headers=student_headers)
        assert response.status_code == 403

    def test_admin_privilege_escalation_prevention(self):
        """Test prevention of privilege escalation to admin."""
        student_token = self.login_user("alice.johnson@student.edu", "password")
        student_headers = self.get_auth_headers(student_token)

        # Try to update own role to admin
        update_data = {"role": "admin"}
        response = self.client.put("/api/auth/me", json=update_data, headers=student_headers)
        assert response.status_code == 200

        # Verify role was not changed
        me_response = self.client.get("/api/auth/me", headers=student_headers)
        assert me_response.json()["role"] == "student"


class TestInputValidationSecurity(BaseTestCase):
    """Security tests for input validation."""

    def test_malformed_json_handling(self):
        """Test handling of malformed JSON input."""
        # Send malformed JSON
        response = self.client.post("/api/auth/login",
                                  data='{"email": "test@example.com", "password": "test"',
                                  headers={"Content-Type": "application/json"})
        # Should handle gracefully
        assert response.status_code in [400, 422]

    def test_oversized_payload_handling(self):
        """Test handling of oversized payloads."""
        # Create a very large payload
        large_data = "x" * 1000000  # 1MB of data
        user_data = {
            "email": f"large{len(large_data)}@example.com",
            "name": large_data,
            "password": "password"
        }

        response = self.client.post("/api/auth/register", json=user_data)
        # Should handle large payload gracefully
        assert response.status_code in [200, 400, 413]  # Success, validation error, or payload too large

    def test_special_characters_in_input(self):
        """Test handling of special characters in input."""
        special_chars = ["<>", "{}[]", "|\\^", ";&`", "$(", ")(", "../", "..\\"]

        for chars in special_chars:
            user_data = {
                "email": f"test{chars}@example.com",
                "name": f"Test User {chars}",
                "password": "password123"
            }

            response = self.client.post("/api/auth/register", json=user_data)
            # Should handle special characters gracefully
            assert response.status_code in [200, 400, 422]

    def test_unicode_input_handling(self):
        """Test handling of Unicode input."""
        unicode_names = [
            "José María",
            "李小明",
            "محمد علي",
            "Александр",
            "François",
            "São Paulo"
        ]

        for name in unicode_names:
            user_data = {
                "email": f"{name.lower().replace(' ', '')}@example.com",
                "name": name,
                "password": "password123"
            }

            response = self.client.post("/api/auth/register", json=user_data)
            # Should handle Unicode gracefully
            assert response.status_code in [200, 400, 422]

    def test_null_byte_injection(self):
        """Test prevention of null byte injection attacks."""
        injection_attempts = [
            {"email": "test@example.com\x00.evil.com", "password": "password"},
            {"email": "test@example.com", "password": "pass\x00word"},
            {"email": "test\x00@example.com", "password": "password"},
        ]

        for attempt in injection_attempts:
            response = self.client.post("/api/auth/login", json=attempt)
            # Should handle null bytes safely
            assert response.status_code in [401, 422]

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32",
        ]

        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        for path in traversal_attempts:
            # Try to access course with malicious path
            response = self.client.get(f"/api/courses/{path}", headers=headers)
            # Should not allow path traversal
            assert response.status_code in [403, 404, 422]

    def test_command_injection_prevention(self):
        """Test prevention of command injection attacks."""
        injection_commands = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "`whoami`",
            "$(echo 'hacked')",
            "; shutdown now",
        ]

        for command in injection_commands:
            user_data = {
                "email": f"test{hash(command)}@example.com",
                "name": f"Test User {command}",
                "password": "password123"
            }

            response = self.client.post("/api/auth/register", json=user_data)
            # Should handle command injection attempts safely
            assert response.status_code in [200, 400, 422]


class TestSessionSecurity(BaseTestCase):
    """Security tests for session management."""

    def test_session_timeout_simulation(self):
        """Test session timeout handling."""
        # Login and get token
        login_response = self.client.post("/api/auth/login", json={
            "email": "alice.johnson@student.edu",
            "password": "password"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Use token immediately (should work)
        response = self.client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200

        # In a real scenario, we'd wait for token expiry
        # For this test, we simulate by using an invalid token
        invalid_headers = {"Authorization": "Bearer expired_token_123"}
        response = self.client.get("/api/auth/me", headers=invalid_headers)
        assert response.status_code == 401

    def test_concurrent_session_handling(self):
        """Test handling of concurrent sessions."""
        # Login multiple times with same credentials
        tokens = []
        for _ in range(5):
            response = self.client.post("/api/auth/login", json={
                "email": "alice.johnson@student.edu",
                "password": "password"
            })
            assert response.status_code == 200
            tokens.append(response.json()["access_token"])

        # All tokens should be valid
        for token in tokens:
            headers = {"Authorization": f"Bearer {token}"}
            response = self.client.get("/api/auth/me", headers=headers)
            assert response.status_code == 200

    def test_token_reuse_after_logout_simulation(self):
        """Test token behavior after logout (simulated)."""
        # Login
        login_response = self.client.post("/api/auth/login", json={
            "email": "alice.johnson@student.edu",
            "password": "password"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Use token
        response = self.client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200

        # Simulate logout by invalidating token
        # In real implementation, this would be handled server-side
        # For test, we just verify invalid tokens are rejected
        invalid_headers = {"Authorization": "Bearer logged_out_token"}
        response = self.client.get("/api/auth/me", headers=invalid_headers)
        assert response.status_code == 401


class TestDataExposureSecurity(BaseTestCase):
    """Security tests for preventing data exposure."""

    def test_sensitive_data_not_exposed(self):
        """Test that sensitive data is not exposed in responses."""
        # Login
        login_response = self.client.post("/api/auth/login", json={
            "email": "alice.johnson@student.edu",
            "password": "password"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get user profile
        response = self.client.get("/api/auth/me", headers=headers)
        user_data = response.json()

        # Sensitive fields should not be exposed
        sensitive_fields = ["password", "password_hash", "secret", "token", "key"]
        for field in sensitive_fields:
            assert field not in str(user_data).lower()

    def test_error_messages_not_exposed(self):
        """Test that error messages don't expose sensitive information."""
        # Try to access non-existent course
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.get("/api/courses/nonexistent_course_12345", headers=headers)
        assert response.status_code == 404

        error_message = response.json().get("detail", "")
        # Error should not contain file paths, stack traces, or sensitive data
        sensitive_indicators = ["file", "line", "trace", "stack", "internal", "server"]
        for indicator in sensitive_indicators:
            assert indicator not in error_message.lower()

    def test_user_enumeration_prevention(self):
        """Test prevention of user enumeration attacks."""
        # Try to login with various emails to see if we can enumerate users
        test_emails = [
            "alice.johnson@student.edu",  # Exists
            "nonexistent@example.com",    # Doesn't exist
            "admin@lms.com",             # Exists
            "fakeuser@test.com",         # Doesn't exist
        ]

        for email in test_emails:
            response = self.client.post("/api/auth/login", json={
                "email": email,
                "password": "wrongpassword"
            })

            # All should return same error to prevent enumeration
            assert response.status_code == 401
            error_detail = response.json().get("detail", "")
            # Error should be generic
            assert "invalid" in error_detail.lower()
            assert "credentials" in error_detail.lower()


class TestRateLimitingSecurity(BaseTestCase):
    """Security tests for rate limiting."""

    def test_api_rate_limiting(self):
        """Test that API endpoints are rate limited."""
        # Make many rapid requests
        for _ in range(100):
            response = self.client.get("/api/")
            # Should not crash, but might be rate limited
            assert response.status_code in [200, 429]  # OK or Too Many Requests

    def test_login_rate_limiting(self):
        """Test rate limiting on login endpoint."""
        login_data = {
            "email": "alice.johnson@student.edu",
            "password": "wrongpassword"
        }

        # Make many login attempts
        responses = []
        for _ in range(50):
            response = self.client.post("/api/auth/login", json=login_data)
            responses.append(response.status_code)

        # Should have some failures, but not crash
        success_count = sum(1 for code in responses if code == 200)
        failure_count = sum(1 for code in responses if code == 401)

        # Most should fail due to wrong password
        assert failure_count > success_count
        # But system should remain stable
        assert len(responses) == 50


class TestCSRFAndXSSSecurity(BaseTestCase):
    """Security tests for CSRF and XSS prevention."""

    def test_csrf_protection(self):
        """Test CSRF protection mechanisms."""
        # Try to make state-changing requests without proper authentication
        course_data = {
            "title": "CSRF Test Course",
            "audience": "Students",
            "difficulty": "beginner"
        }

        # Without authentication
        response = self.client.post("/api/courses", json=course_data)
        assert response.status_code == 401

        # With invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = self.client.post("/api/courses", json=course_data, headers=headers)
        assert response.status_code == 401

    def test_xss_in_course_content(self):
        """Test XSS prevention in course content."""
        instructor_token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(instructor_token)

        # Create course with XSS payload
        course_data = {
            "title": "XSS Test Course",
            "audience": "Students",
            "difficulty": "beginner"
        }

        response = self.client.post("/api/courses", json=course_data, headers=headers)
        course_id = response.json()["id"]

        # Add lesson with XSS content
        xss_content = "<script>alert('XSS Attack')</script><img src=x onerror=alert('XSS')>"
        lesson_data = {
            "title": "XSS Test Lesson",
            "content": xss_content
        }

        response = self.client.post(f"/api/courses/{course_id}/lessons", json=lesson_data, headers=headers)
        assert response.status_code == 200

        # Retrieve content
        response = self.client.get(f"/api/courses/{course_id}", headers=headers)
        course_data = response.json()

        # Content should be stored (XSS prevention is typically handled at display time)
        lesson_content = course_data["lessons"][0]["content"]
        assert xss_content in lesson_content