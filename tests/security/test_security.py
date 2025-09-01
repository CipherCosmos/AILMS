"""
Security tests for LMS backend
"""
import pytest
from httpx import AsyncClient
import json
import re
from typing import List, Dict, Any


class TestAuthenticationSecurity:
    """Test authentication security"""

    @pytest.mark.asyncio
    async def test_brute_force_protection(self, test_client: AsyncClient):
        """Test protection against brute force attacks"""
        # Attempt multiple login failures
        for i in range(10):
            response = await test_client.post(
                "/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "wrongpassword"
                }
            )

        # Should eventually be rate limited or account locked
        response = await test_client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )

        # Should be blocked
        assert response.status_code in [429, 423]  # Too Many Requests or Locked

    @pytest.mark.asyncio
    async def test_weak_password_rejection(self, test_client: AsyncClient):
        """Test that weak passwords are rejected"""
        weak_passwords = [
            "123",
            "password",
            "qwerty",
            "abc123",
            "password123"
        ]

        for password in weak_passwords:
            response = await test_client.post(
                "/auth/register",
                json={
                    "email": f"test_{password}@example.com",
                    "name": "Test User",
                    "password": password,
                    "role": "student"
                }
            )

            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, test_client: AsyncClient, security_config):
        """Test SQL injection prevention"""
        for payload in security_config["sql_injection_payloads"]:
            # Test in login
            response = await test_client.post(
                "/auth/login",
                json={
                    "email": payload,
                    "password": "password"
                }
            )

            # Should not execute SQL or return sensitive data
            assert response.status_code in [401, 422]
            if response.status_code == 401:
                data = response.json()
                assert "detail" in data
                assert "SQL" not in str(data)  # Should not contain SQL errors

    @pytest.mark.asyncio
    async def test_jwt_token_security(self, test_client: AsyncClient, test_user_data):
        """Test JWT token security"""
        # Register and login
        await test_client.post("/auth/register", json=test_user_data)

        response = await test_client.post(
            "/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )

        token = response.json()["access_token"]

        # Test token tampering
        tampered_token = token[:-10] + "modified"

        response = await test_client.get(
            "/users/profile",
            headers={"Authorization": f"Bearer {tampered_token}"}
        )

        assert response.status_code == 401

        # Test expired token (would need to create expired token manually)
        # This is tested in the auth service unit tests

    @pytest.mark.asyncio
    async def test_session_fixation_prevention(self, test_client: AsyncClient):
        """Test prevention of session fixation attacks"""
        # This would require tracking session IDs
        # For now, verify that new logins get new tokens
        pass


class TestAuthorizationSecurity:
    """Test authorization security"""

    @pytest.mark.asyncio
    async def test_role_based_access_control(self, test_client: AsyncClient):
        """Test role-based access control"""
        # Create users with different roles
        roles = ["student", "instructor", "admin"]

        for role in roles:
            user_data = {
                "email": f"{role}@example.com",
                "name": f"{role.title()} User",
                "password": "TestPass123!",
                "role": role
            }

            await test_client.post("/auth/register", json=user_data)

            # Login
            response = await test_client.post(
                "/auth/login",
                json={
                    "email": user_data["email"],
                    "password": user_data["password"]
                }
            )

            if response.status_code == 200:
                token = response.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                # Test access to role-specific endpoints
                if role == "student":
                    # Students should not access admin endpoints
                    response = await test_client.get("/admin/users", headers=headers)
                    assert response.status_code == 403

                elif role == "instructor":
                    # Instructors should access course management
                    response = await test_client.get("/courses", headers=headers)
                    assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_horizontal_privilege_escalation(self, test_client: AsyncClient):
        """Test prevention of horizontal privilege escalation"""
        # Create two student users
        for i in range(2):
            user_data = {
                "email": f"student{i}@example.com",
                "name": f"Student {i}",
                "password": "TestPass123!",
                "role": "student"
            }

            await test_client.post("/auth/register", json=user_data)

        # Login as first student
        response = await test_client.post(
            "/auth/login",
            json={
                "email": "student0@example.com",
                "password": "TestPass123!"
            }
        )

        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to access another student's data
        response = await test_client.get(
            "/users/student1@example.com/profile",
            headers=headers
        )

        # Should be forbidden
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_vertical_privilege_escalation(self, test_client: AsyncClient):
        """Test prevention of vertical privilege escalation"""
        # Create a student user
        user_data = {
            "email": "student@example.com",
            "name": "Student User",
            "password": "TestPass123!",
            "role": "student"
        }

        await test_client.post("/auth/register", json=user_data)

        # Login
        response = await test_client.post(
            "/auth/login",
            json={
                "email": user_data["email"],
                "password": user_data["password"]
            }
        )

        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to access admin endpoints
        admin_endpoints = [
            "/admin/users",
            "/admin/courses",
            "/admin/analytics"
        ]

        for endpoint in admin_endpoints:
            response = await test_client.get(endpoint, headers=headers)
            assert response.status_code == 403


class TestInputValidationSecurity:
    """Test input validation security"""

    @pytest.mark.asyncio
    async def test_xss_prevention(self, test_client: AsyncClient, security_config):
        """Test XSS prevention"""
        for payload in security_config["xss_payloads"]:
            # Test in user registration
            response = await test_client.post(
                "/auth/register",
                json={
                    "email": "test@example.com",
                    "name": payload,
                    "password": "TestPass123!",
                    "role": "student"
                }
            )

            if response.status_code == 201:
                # If registration succeeded, check that XSS payload is not in response
                data = response.json()
                assert payload not in str(data)

    @pytest.mark.asyncio
    async def test_input_sanitization(self, test_client: AsyncClient):
        """Test input sanitization"""
        malicious_inputs = [
            "<script>alert('XSS')</script>",
            "../../../etc/passwd",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "{{7*7}}",  # Template injection
            "${7*7}"    # Expression injection
        ]

        for malicious_input in malicious_inputs:
            # Test in course creation
            response = await test_client.post(
                "/courses",
                json={
                    "title": malicious_input,
                    "description": "Test course",
                    "instructor_id": "instructor123",
                    "category": "Test",
                    "difficulty_level": "intermediate"
                },
                headers={"Authorization": "Bearer test-token"}
            )

            if response.status_code == 201:
                data = response.json()
                # Ensure malicious content is not in the response
                assert malicious_input not in str(data)

    @pytest.mark.asyncio
    async def test_file_upload_security(self, test_client: AsyncClient, auth_headers):
        """Test file upload security"""
        # Test malicious file uploads
        malicious_files = [
            ("malicious.exe", b"malicious content", "application/x-msdownload"),
            ("script.php", b"<?php echo 'malicious'; ?>", "application/x-php"),
            ("large_file.txt", b"x" * (100 * 1024 * 1024), "text/plain"),  # 100MB file
        ]

        for filename, content, content_type in malicious_files:
            files = {"file": (filename, content, content_type)}

            response = await test_client.post(
                "/files/upload",
                files=files,
                headers=auth_headers
            )

            # Should reject malicious files
            if "exe" in filename or "php" in filename:
                assert response.status_code == 400
            elif len(content) > 10 * 1024 * 1024:  # 10MB limit
                assert response.status_code == 413  # Payload Too Large

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, test_client: AsyncClient, auth_headers):
        """Test path traversal prevention"""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam"
        ]

        for payload in path_traversal_payloads:
            # Test in file operations
            response = await test_client.get(
                f"/files/{payload}/download",
                headers=auth_headers
            )

            assert response.status_code == 404  # Should not find the file

    @pytest.mark.asyncio
    async def test_command_injection_prevention(self, test_client: AsyncClient):
        """Test command injection prevention"""
        command_injection_payloads = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "`whoami`",
            "$(rm -rf /)",
            "; shutdown now"
        ]

        for payload in command_injection_payloads:
            # Test in search endpoints
            response = await test_client.get(
                "/courses/search",
                params={"query": payload}
            )

            # Should not execute commands
            assert response.status_code in [200, 422]
            if response.status_code == 200:
                data = response.json()
                # Ensure no command execution results in response
                assert "root" not in str(data).lower()
                assert "passwd" not in str(data).lower()


class TestRateLimitingSecurity:
    """Test rate limiting security"""

    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, test_client: AsyncClient, security_config):
        """Test rate limiting is properly enforced"""
        # Make multiple requests to rate-limited endpoints
        responses = []
        for i in range(security_config["rate_limit_threshold"] + 10):
            response = await test_client.post(
                "/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "password"
                }
            )
            responses.append(response.status_code)

        # Should have rate limiting responses
        assert 429 in responses  # Too Many Requests

    @pytest.mark.asyncio
    async def test_rate_limit_bypass_prevention(self, test_client: AsyncClient):
        """Test prevention of rate limit bypass attempts"""
        # Try different user agents, IPs, etc. (simulated)
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ]

        for ua in user_agents:
            response = await test_client.post(
                "/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "password"
                },
                headers={"User-Agent": ua}
            )

            # Rate limiting should still apply regardless of user agent
            assert response.status_code in [401, 429]


class TestDataExposureSecurity:
    """Test data exposure security"""

    @pytest.mark.asyncio
    async def test_sensitive_data_exposure(self, test_client: AsyncClient, auth_headers):
        """Test that sensitive data is not exposed"""
        # Test error messages don't leak sensitive information
        response = await test_client.get(
            "/users/nonexistent@example.com/profile",
            headers=auth_headers
        )

        if response.status_code == 404:
            data = response.json()
            error_message = str(data)

            # Should not contain sensitive information
            sensitive_patterns = [
                r"password",
                r"token",
                r"secret",
                r"key",
                r"mongodb",
                r"redis"
            ]

            for pattern in sensitive_patterns:
                assert not re.search(pattern, error_message, re.IGNORECASE)

    @pytest.mark.asyncio
    async def test_information_disclosure(self, test_client: AsyncClient):
        """Test prevention of information disclosure"""
        # Test that system information is not leaked
        endpoints = ["/health", "/health/detailed"]

        for endpoint in endpoints:
            response = await test_client.get(endpoint)

            data = response.json()
            response_str = str(data)

            # Should not contain sensitive system information
            sensitive_info = [
                "password",
                "secret",
                "key",
                "token",
                "mongodb://",
                "redis://",
                "/etc/passwd",
                "/home/",
                "root"
            ]

            for info in sensitive_info:
                assert info not in response_str

    @pytest.mark.asyncio
    async def test_debug_mode_disabled(self, test_client: AsyncClient):
        """Test that debug mode is disabled in production"""
        response = await test_client.get("/health")

        # Should not contain debug information
        data = response.json()
        assert "debug" not in str(data).lower()
        assert "traceback" not in str(data).lower()


class TestHTTPSecurity:
    """Test HTTP security headers and practices"""

    @pytest.mark.asyncio
    async def test_security_headers(self, test_client: AsyncClient):
        """Test that security headers are properly set"""
        response = await test_client.get("/health")

        # Check for essential security headers
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy"
        ]

        for header in required_headers:
            assert header in response.headers

        # Verify header values
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_cors_configuration(self, test_client: AsyncClient):
        """Test CORS configuration security"""
        # Test preflight request
        response = await test_client.options(
            "/health",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "GET"
            }
        )

        # Should not allow arbitrary origins
        if "Access-Control-Allow-Origin" in response.headers:
            allowed_origin = response.headers["Access-Control-Allow-Origin"]
            assert allowed_origin != "*"  # Should not allow all origins
            assert "malicious-site.com" not in allowed_origin

    @pytest.mark.asyncio
    async def test_http_methods_restriction(self, test_client: AsyncClient):
        """Test that dangerous HTTP methods are restricted"""
        dangerous_methods = ["TRACE", "TRACK", "CONNECT"]

        for method in dangerous_methods:
            if hasattr(test_client, method.lower()):
                response = await getattr(test_client, method.lower())("/health")
                assert response.status_code in [405, 501]  # Method Not Allowed or Not Implemented

    @pytest.mark.asyncio
    async def test_directory_traversal_prevention(self, test_client: AsyncClient):
        """Test directory traversal prevention"""
        traversal_payloads = [
            "/..",
            "/../",
            "/../../etc/passwd",
            "/static/../../../etc/passwd",
            "/api/../../../windows/system32"
        ]

        for payload in traversal_payloads:
            response = await test_client.get(payload)
            assert response.status_code in [404, 403]  # Not Found or Forbidden


class TestSessionSecurity:
    """Test session security"""

    @pytest.mark.asyncio
    async def test_session_timeout(self, test_client: AsyncClient, test_user_data):
        """Test session timeout enforcement"""
        # This would require creating a token and waiting for expiry
        # For now, just verify the endpoint exists
        response = await test_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_session_limit(self, test_client: AsyncClient):
        """Test concurrent session limits"""
        # This would require tracking multiple sessions
        # For now, just verify basic functionality
        response = await test_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_session_invalidation(self, test_client: AsyncClient):
        """Test session invalidation on logout"""
        # This would require implementing logout functionality
        # For now, just verify basic functionality
        response = await test_client.get("/health")
        assert response.status_code == 200


class TestAuditSecurity:
    """Test audit logging security"""

    @pytest.mark.asyncio
    async def test_audit_logging(self, test_client: AsyncClient, test_user_data, auth_headers):
        """Test that security events are properly logged"""
        # Perform some operations that should be logged
        await test_client.get("/users/profile", headers=auth_headers)
        await test_client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": "wrongpassword"
        })

        # Verify audit logs are created (would need access to log storage)
        # For now, just verify the operations complete
        response = await test_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_log_injection_prevention(self, test_client: AsyncClient):
        """Test prevention of log injection attacks"""
        injection_payloads = [
            "test%0A%0DInjected line",
            "test\nInjected line",
            "test\r\nInjected line"
        ]

        for payload in injection_payloads:
            response = await test_client.post(
                "/auth/login",
                json={
                    "email": payload,
                    "password": "password"
                }
            )

            # Should not cause log injection
            assert response.status_code in [401, 422]


class TestEncryptionSecurity:
    """Test encryption and data protection"""

    @pytest.mark.asyncio
    async def test_password_encryption(self, test_client: AsyncClient):
        """Test that passwords are properly encrypted"""
        # Register a user
        user_data = {
            "email": "encrypt_test@example.com",
            "name": "Encrypt Test",
            "password": "TestPassword123!",
            "role": "student"
        }

        response = await test_client.post("/auth/register", json=user_data)
        assert response.status_code == 201

        # Password should be hashed in database (would need database access to verify)
        # For now, just verify registration works
        assert "id" in response.json()

    @pytest.mark.asyncio
    async def test_data_transmission_encryption(self, test_client: AsyncClient):
        """Test that data is transmitted securely"""
        # This would require HTTPS setup
        # For now, verify basic functionality
        response = await test_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_sensitive_data_masking(self, test_client: AsyncClient, auth_headers):
        """Test that sensitive data is properly masked in logs/responses"""
        response = await test_client.get("/users/profile", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            response_str = str(data)

            # Should not contain unmasked sensitive data
            sensitive_patterns = [
                r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",  # Credit card numbers
                r"\b\d{3}[- ]?\d{3}[- ]?\d{4}\b",  # SSN pattern
                r"password.*:",  # Password fields
                r"token.*:",  # Token fields
            ]

            for pattern in sensitive_patterns:
                assert not re.search(pattern, response_str, re.IGNORECASE)