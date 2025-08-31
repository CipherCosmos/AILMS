"""
Performance tests for critical LMS endpoints.
"""
import pytest
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
import statistics
from tests.test_base import BaseTestCase


class TestPerformanceBase(BaseTestCase):
    """Base class for performance tests with timing utilities."""

    def time_request(self, method, url, **kwargs):
        """Time a single request."""
        start_time = time.time()
        response = getattr(self.client, method)(url, **kwargs)
        end_time = time.time()
        return response, end_time - start_time

    def run_concurrent_requests(self, method, url, num_requests=10, **kwargs):
        """Run multiple concurrent requests and measure performance."""
        responses = []
        times = []

        def single_request():
            start = time.time()
            response = getattr(self.client, method)(url, **kwargs)
            end = time.time()
            return response, end - start

        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(single_request) for _ in range(num_requests)]
            for future in futures:
                response, request_time = future.result()
                responses.append(response)
                times.append(request_time)

        return responses, times

    def analyze_performance(self, times, max_avg_time=1.0, max_p95_time=2.0):
        """Analyze performance metrics."""
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
        min_time = min(times)
        max_time = max(times)

        print(f"Performance Metrics:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Median: {median_time:.3f}s")
        print(f"  95th percentile: {p95_time:.3f}s")
        print(f"  Min: {min_time:.3f}s")
        print(f"  Max: {max_time:.3f}s")

        # Assertions
        assert avg_time < max_avg_time, f"Average response time {avg_time:.3f}s exceeds {max_avg_time}s"
        assert p95_time < max_p95_time, f"95th percentile {p95_time:.3f}s exceeds {max_p95_time}s"

        return {
            "avg_time": avg_time,
            "median_time": median_time,
            "p95_time": p95_time,
            "min_time": min_time,
            "max_time": max_time
        }


class TestAuthenticationPerformance(TestPerformanceBase):
    """Performance tests for authentication endpoints."""

    @pytest.mark.performance
    def test_login_performance(self):
        """Test login endpoint performance under load."""
        login_data = {
            "email": "alice.johnson@student.edu",
            "password": "password"
        }

        # Test single request performance
        response, request_time = self.time_request("post", "/api/auth/login", json=login_data)
        assert response.status_code == 200
        assert request_time < 0.5, f"Single login too slow: {request_time:.3f}s"

        # Test concurrent logins
        responses, times = self.run_concurrent_requests(
            "post", "/api/auth/login", num_requests=20, json=login_data
        )

        # All responses should be successful
        assert all(r.status_code == 200 for r in responses)

        # Analyze performance
        metrics = self.analyze_performance(times, max_avg_time=1.0, max_p95_time=2.0)
        assert metrics["avg_time"] < 1.0

    @pytest.mark.performance
    def test_token_refresh_performance(self):
        """Test token refresh performance."""
        # Get initial token
        login_response = self.client.post("/api/auth/login", json={
            "email": "alice.johnson@student.edu",
            "password": "password"
        })
        refresh_token = login_response.json()["refresh_token"]

        refresh_data = {"refresh_token": refresh_token}

        # Test single refresh
        response, request_time = self.time_request("post", "/api/auth/refresh", json=refresh_data)
        assert response.status_code == 200
        assert request_time < 0.3

        # Test concurrent refreshes
        responses, times = self.run_concurrent_requests(
            "post", "/api/auth/refresh", num_requests=15, json=refresh_data
        )

        assert all(r.status_code == 200 for r in responses)
        metrics = self.analyze_performance(times, max_avg_time=0.8, max_p95_time=1.5)


class TestCoursesPerformance(TestPerformanceBase):
    """Performance tests for courses endpoints."""

    @pytest.mark.performance
    def test_list_courses_performance(self):
        """Test course listing performance."""
        # Login first
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Test single request
        response, request_time = self.time_request("get", "/api/courses", headers=headers)
        assert response.status_code == 200
        assert request_time < 0.5

        # Test concurrent requests
        responses, times = self.run_concurrent_requests(
            "get", "/api/courses", num_requests=25, headers=headers
        )

        assert all(r.status_code == 200 for r in responses)
        metrics = self.analyze_performance(times, max_avg_time=1.0, max_p95_time=2.0)

    @pytest.mark.performance
    def test_get_course_detail_performance(self):
        """Test individual course detail retrieval performance."""
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Test single course detail
        response, request_time = self.time_request("get", "/api/courses/course_ai_ml_001", headers=headers)
        assert response.status_code == 200
        assert request_time < 0.3

        # Test concurrent course detail requests
        responses, times = self.run_concurrent_requests(
            "get", "/api/courses/course_ai_ml_001", num_requests=20, headers=headers
        )

        assert all(r.status_code == 200 for r in responses)
        metrics = self.analyze_performance(times, max_avg_time=0.8, max_p95_time=1.5)

    @pytest.mark.performance
    def test_course_enrollment_performance(self):
        """Test course enrollment performance under concurrent load."""
        # Create multiple test users for enrollment
        test_users = []
        for i in range(10):
            user_data = {
                "email": f"perf.user{i}@example.com",
                "name": f"Performance User {i}",
                "password": "test123"
            }
            self.client.post("/api/auth/register", json=user_data)
            test_users.append(user_data)

        # Login all users and enroll them concurrently
        def enroll_user(user_data):
            login_response = self.client.post("/api/auth/login", json={
                "email": user_data["email"],
                "password": user_data["password"]
            })
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            start_time = time.time()
            response = self.client.post("/api/courses/course_data_science_001/enroll", headers=headers)
            end_time = time.time()

            return response, end_time - start_time

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(enroll_user, user) for user in test_users]
            results = [future.result() for future in futures]

        responses, times = zip(*results)
        assert all(r.status_code == 200 for r in responses)
        metrics = self.analyze_performance(times, max_avg_time=1.5, max_p95_time=3.0)


class TestProgressTrackingPerformance(TestPerformanceBase):
    """Performance tests for progress tracking."""

    @pytest.mark.performance
    def test_progress_update_performance(self):
        """Test progress update performance."""
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        progress_data = {
            "lesson_id": "lesson_1",
            "completed": True,
            "quiz_score": 85
        }

        # Test single progress update
        response, request_time = self.time_request(
            "post", "/api/courses/course_ai_ml_001/progress", json=progress_data, headers=headers
        )
        assert response.status_code == 200
        assert request_time < 0.5

        # Test concurrent progress updates
        responses, times = self.run_concurrent_requests(
            "post", "/api/courses/course_ai_ml_001/progress", num_requests=15,
            json=progress_data, headers=headers
        )

        assert all(r.status_code == 200 for r in responses)
        metrics = self.analyze_performance(times, max_avg_time=1.0, max_p95_time=2.0)

    @pytest.mark.performance
    def test_progress_retrieval_performance(self):
        """Test progress retrieval performance."""
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Test single progress retrieval
        response, request_time = self.time_request("get", "/api/courses/course_ai_ml_001/progress", headers=headers)
        assert response.status_code == 200
        assert request_time < 0.3

        # Test concurrent progress retrievals
        responses, times = self.run_concurrent_requests(
            "get", "/api/courses/course_ai_ml_001/progress", num_requests=20, headers=headers
        )

        assert all(r.status_code == 200 for r in responses)
        metrics = self.analyze_performance(times, max_avg_time=0.8, max_p95_time=1.5)


class TestRecommendationsPerformance(TestPerformanceBase):
    """Performance tests for recommendation system."""

    @pytest.mark.performance
    def test_recommendations_performance(self):
        """Test course recommendations performance."""
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Test single recommendation request
        response, request_time = self.time_request("get", "/api/courses/course_recommendations", headers=headers)
        assert response.status_code == 200
        assert request_time < 1.0  # Recommendations can be slower

        # Test concurrent recommendation requests
        responses, times = self.run_concurrent_requests(
            "get", "/api/courses/course_recommendations", num_requests=10, headers=headers
        )

        assert all(r.status_code == 200 for r in responses)
        metrics = self.analyze_performance(times, max_avg_time=2.0, max_p95_time=4.0)

    @pytest.mark.performance
    def test_learning_path_performance(self):
        """Test learning path generation performance."""
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Test single learning path request
        response, request_time = self.time_request("get", "/api/courses/learning_path", headers=headers)
        assert response.status_code == 200
        assert request_time < 1.5

        # Test concurrent learning path requests
        responses, times = self.run_concurrent_requests(
            "get", "/api/courses/learning_path", num_requests=8, headers=headers
        )

        assert all(r.status_code == 200 for r in responses)
        metrics = self.analyze_performance(times, max_avg_time=2.5, max_p95_time=5.0)


class TestDatabasePerformance(TestPerformanceBase):
    """Performance tests for database operations."""

    @pytest.mark.performance
    def test_database_query_performance(self):
        """Test database query performance with large datasets."""
        token = self.login_user("admin@lms.com", "admin123")
        headers = self.get_auth_headers(token)

        # Test user listing performance
        response, request_time = self.time_request("get", "/api/auth/users", headers=headers)
        assert response.status_code == 200
        assert request_time < 1.0

        # Test concurrent user listing
        responses, times = self.run_concurrent_requests(
            "get", "/api/auth/users", num_requests=10, headers=headers
        )

        assert all(r.status_code == 200 for r in responses)
        metrics = self.analyze_performance(times, max_avg_time=1.5, max_p95_time=3.0)

    @pytest.mark.performance
    def test_course_search_performance(self):
        """Test course search and filtering performance."""
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Test course listing with search
        response, request_time = self.time_request("get", "/api/courses", headers=headers)
        assert response.status_code == 200
        assert request_time < 0.8

        # Simulate search load
        responses, times = self.run_concurrent_requests(
            "get", "/api/courses", num_requests=15, headers=headers
        )

        assert all(r.status_code == 200 for r in responses)
        metrics = self.analyze_performance(times, max_avg_time=1.2, max_p95_time=2.5)


class TestMemoryAndResourceUsage(TestPerformanceBase):
    """Tests for memory usage and resource consumption."""

    @pytest.mark.performance
    def test_memory_usage_under_load(self):
        """Test memory usage under concurrent load."""
        import psutil
        import os

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Run many concurrent requests
        responses, times = self.run_concurrent_requests(
            "get", "/api/courses", num_requests=50, headers=headers
        )

        # Check memory usage after load
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{memory_increase:.1f}MB)")

        # Memory increase should be reasonable
        assert memory_increase < 100, f"Memory increase too high: {memory_increase:.1f}MB"
        assert all(r.status_code == 200 for r in responses)

    @pytest.mark.performance
    def test_connection_pooling_efficiency(self):
        """Test database connection pooling efficiency."""
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Run many quick requests to test connection reuse
        start_time = time.time()

        for _ in range(100):
            response = self.client.get("/api/courses", headers=headers)
            assert response.status_code == 200

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / 100

        print(f"100 sequential requests: {total_time:.3f}s total, {avg_time:.3f}s average")

        # Average time should be reasonable for sequential requests
        assert avg_time < 0.1, f"Average request time too high: {avg_time:.3f}s"


class TestScalabilityTests(TestPerformanceBase):
    """Tests for system scalability."""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_high_concurrency_load(self):
        """Test system under high concurrency load."""
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Test with high concurrency
        responses, times = self.run_concurrent_requests(
            "get", "/api/courses", num_requests=100, headers=headers
        )

        # Should handle high load gracefully
        success_rate = sum(1 for r in responses if r.status_code == 200) / len(responses)
        assert success_rate > 0.95, f"Success rate too low: {success_rate:.2%}"

        metrics = self.analyze_performance(times, max_avg_time=2.0, max_p95_time=5.0)

        # Even under high load, should not have excessive failures
        assert len([r for r in responses if r.status_code >= 500]) == 0, "Server errors under load"

    @pytest.mark.performance
    def test_large_payload_handling(self):
        """Test handling of large request payloads."""
        token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(token)

        # Create a course with large content
        large_content = "Large content " * 1000  # ~13KB of content
        course_data = {
            "title": "Large Content Course",
            "audience": "Students",
            "difficulty": "intermediate"
        }

        # Create course
        create_response = self.client.post("/api/courses", json=course_data, headers=headers)
        assert create_response.status_code == 200
        course_id = create_response.json()["id"]

        # Add lesson with large content
        lesson_data = {
            "title": "Large Lesson",
            "content": large_content
        }

        response, request_time = self.time_request(
            "post", f"/api/courses/{course_id}/lessons", json=lesson_data, headers=headers
        )
        assert response.status_code == 200
        assert request_time < 2.0  # Should handle large payloads reasonably

        # Retrieve large content
        response, request_time = self.time_request("get", f"/api/courses/{course_id}", headers=headers)
        assert response.status_code == 200
        assert request_time < 1.0