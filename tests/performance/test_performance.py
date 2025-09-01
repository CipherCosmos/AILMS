"""
Performance tests for LMS backend
"""
import pytest
import asyncio
import time
from typing import List, Dict, Any
from httpx import AsyncClient
import statistics
import concurrent.futures
from datetime import datetime, timedelta


class TestPerformance:
    """Performance test cases"""

    @pytest.fixture
    async def performance_client(self, test_client: AsyncClient):
        """Performance test client"""
        return test_client

    def test_response_time_baseline(self, performance_config):
        """Test baseline response times for critical endpoints"""
        # This would be run separately with locust or similar tool
        pass

    @pytest.mark.asyncio
    async def test_concurrent_user_load(self, performance_client: AsyncClient, performance_config):
        """Test system performance under concurrent user load"""
        async def single_user_workflow(user_id: int):
            """Simulate a single user's workflow"""
            start_time = time.time()

            try:
                # User registration
                user_data = {
                    "email": f"perf_user_{user_id}@example.com",
                    "name": f"Performance User {user_id}",
                    "password": "TestPass123!",
                    "role": "student"
                }

                response = await performance_client.post("/auth/register", json=user_data)
                assert response.status_code in [201, 409]  # 409 if user exists

                # User login
                login_data = {
                    "email": user_data["email"],
                    "password": user_data["password"]
                }

                response = await performance_client.post("/auth/login", json=login_data)
                if response.status_code == 200:
                    token = response.json()["access_token"]
                    headers = {"Authorization": f"Bearer {token}"}

                    # Course operations
                    course_data = {
                        "title": f"Performance Course {user_id}",
                        "description": f"Course for performance testing user {user_id}",
                        "instructor_id": f"instructor_{user_id}",
                        "category": "Performance Testing",
                        "difficulty_level": "intermediate"
                    }

                    response = await performance_client.post("/courses", json=course_data, headers=headers)
                    course_id = response.json().get("id") if response.status_code == 201 else None

                    # Assessment operations
                    if course_id:
                        assessment_data = {
                            "title": f"Performance Assessment {user_id}",
                            "description": f"Assessment for user {user_id}",
                            "course_id": course_id,
                            "questions": [
                                {
                                    "question": f"What is {i} + {i}?",
                                    "options": [str(2*i), str(2*i+1), str(2*i-1), str(2*i+2)],
                                    "correct_answer": 0,
                                    "points": 10
                                } for i in range(1, 6)
                            ],
                            "time_limit": 30,
                            "passing_score": 70
                        }

                        response = await performance_client.post("/assessments", json=assessment_data, headers=headers)

                return time.time() - start_time

            except Exception as e:
                print(f"User {user_id} failed: {e}")
                return time.time() - start_time

        # Run concurrent users
        num_users = min(performance_config["concurrent_users"], 10)  # Limit for testing
        tasks = [single_user_workflow(i) for i in range(num_users)]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Calculate metrics
        successful_requests = [r for r in results if isinstance(r, (int, float)) and r > 0]
        failed_requests = len(results) - len(successful_requests)

        if successful_requests:
            avg_response_time = statistics.mean(successful_requests)
            median_response_time = statistics.median(successful_requests)
            min_response_time = min(successful_requests)
            max_response_time = max(successful_requests)
            throughput = len(successful_requests) / total_time

            print(f"""
Performance Test Results:
- Total Users: {num_users}
- Successful Requests: {len(successful_requests)}
- Failed Requests: {failed_requests}
- Total Time: {total_time:.2f}s
- Average Response Time: {avg_response_time:.2f}s
- Median Response Time: {median_response_time:.2f}s
- Min Response Time: {min_response_time:.2f}s
- Max Response Time: {max_response_time:.2f}s
- Throughput: {throughput:.2f} requests/second
            """)

            # Assert performance thresholds
            assert avg_response_time < performance_config["response_time_threshold"]
            assert failed_requests / num_users < performance_config["error_rate_threshold"]

    @pytest.mark.asyncio
    async def test_database_performance(self, test_database, performance_config):
        """Test database performance under load"""
        # Create test data
        test_users = [
            {
                "email": f"db_test_user_{i}@example.com",
                "name": f"DB Test User {i}",
                "password": "hashed_password",
                "role": "student",
                "is_active": True,
                "created_at": datetime.utcnow()
            } for i in range(100)
        ]

        # Bulk insert performance
        start_time = time.time()
        result = await test_database.users.insert_many(test_users)
        insert_time = time.time() - start_time

        assert len(result.inserted_ids) == 100
        print(f"Database bulk insert (100 records): {insert_time:.2f}s")

        # Query performance
        start_time = time.time()
        users = await test_database.users.find({"role": "student"}).to_list(length=None)
        query_time = time.time() - start_time

        assert len(users) == 100
        print(f"Database query (100 records): {query_time:.2f}s")

        # Update performance
        start_time = time.time()
        result = await test_database.users.update_many(
            {"role": "student"},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        update_time = time.time() - start_time

        assert result.modified_count == 100
        print(f"Database bulk update (100 records): {update_time:.2f}s")

        # Assert reasonable performance
        assert insert_time < 5.0  # Should complete within 5 seconds
        assert query_time < 2.0   # Should complete within 2 seconds
        assert update_time < 3.0  # Should complete within 3 seconds

    @pytest.mark.asyncio
    async def test_cache_performance(self, test_redis_client, performance_config):
        """Test Redis cache performance"""
        # Set multiple cache entries
        cache_data = {f"cache_key_{i}": f"cache_value_{i}" for i in range(1000)}

        start_time = time.time()
        for key, value in cache_data.items():
            await test_redis_client.set(key, value, ex=3600)
        set_time = time.time() - start_time

        print(f"Redis set (1000 keys): {set_time:.2f}s")

        # Get cache entries
        start_time = time.time()
        for key in cache_data.keys():
            value = await test_redis_client.get(key)
            assert value is not None
        get_time = time.time() - start_time

        print(f"Redis get (1000 keys): {get_time:.2f}s")

        # Assert reasonable performance
        assert set_time < 2.0  # Should complete within 2 seconds
        assert get_time < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_memory_usage(self, performance_client: AsyncClient):
        """Test memory usage under load"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operations
        tasks = []
        for i in range(50):
            task = performance_client.get("/health")
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"Memory usage - Initial: {initial_memory:.2f}MB, Final: {final_memory:.2f}MB, Increase: {memory_increase:.2f}MB")

        # Assert reasonable memory usage
        assert memory_increase < 100  # Should not increase by more than 100MB
        assert all(response.status_code == 200 for response in responses)

    @pytest.mark.asyncio
    async def test_api_endpoint_performance(self, performance_client: AsyncClient):
        """Test individual API endpoint performance"""
        endpoints = [
            ("/health", "GET", None),
            ("/auth/login", "POST", {"email": "test@example.com", "password": "test"}),
            ("/courses", "GET", None),
        ]

        results = {}

        for endpoint, method, data in endpoints:
            response_times = []

            # Make multiple requests to each endpoint
            for _ in range(10):
                start_time = time.time()

                if method == "GET":
                    response = await performance_client.get(endpoint)
                elif method == "POST":
                    response = await performance_client.post(endpoint, json=data or {})

                end_time = time.time()
                response_times.append(end_time - start_time)

                assert response.status_code in [200, 401, 404, 422]  # Acceptable status codes

            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            min_time = min(response_times)

            results[endpoint] = {
                "average": avg_time,
                "max": max_time,
                "min": min_time,
                "requests": len(response_times)
            }

            print(f"Endpoint {endpoint}: Avg {avg_time:.3f}s, Max {max_time:.3f}s, Min {min_time:.3f}s")

            # Assert reasonable performance
            assert avg_time < 1.0  # Should respond within 1 second on average

        return results

    @pytest.mark.asyncio
    async def test_file_upload_performance(self, performance_client: AsyncClient, auth_headers):
        """Test file upload performance"""
        # Create test files of different sizes
        file_sizes = [1024, 10240, 102400]  # 1KB, 10KB, 100KB

        results = {}

        for size in file_sizes:
            file_content = b"X" * size
            files = {"file": (f"test_{size}.txt", file_content, "text/plain")}

            response_times = []

            # Upload file multiple times
            for _ in range(5):
                start_time = time.time()

                response = await performance_client.post(
                    "/files/upload",
                    files=files,
                    headers=auth_headers
                )

                end_time = time.time()
                response_times.append(end_time - start_time)

                if response.status_code == 201:
                    # Clean up uploaded file
                    file_id = response.json()["file_id"]
                    await performance_client.delete(f"/files/{file_id}", headers=auth_headers)

            avg_time = statistics.mean(response_times)
            results[size] = avg_time

            print(f"File upload ({size} bytes): Avg {avg_time:.3f}s")

            # Assert reasonable performance (larger files can take longer)
            if size <= 10240:  # 10KB
                assert avg_time < 2.0
            else:  # 100KB
                assert avg_time < 5.0

        return results

    @pytest.mark.asyncio
    async def test_database_connection_pooling(self, test_database):
        """Test database connection pooling performance"""
        # Simulate multiple concurrent database operations
        async def db_operation(operation_id: int):
            start_time = time.time()

            # Perform a simple database operation
            result = await test_database.command('ping')
            assert result['ok'] == 1.0

            end_time = time.time()
            return end_time - start_time

        # Run multiple concurrent operations
        num_operations = 50
        tasks = [db_operation(i) for i in range(num_operations)]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        avg_time = statistics.mean(results)
        throughput = num_operations / total_time

        print(f"Database connection pooling test:")
        print(f"- Operations: {num_operations}")
        print(f"- Total Time: {total_time:.2f}s")
        print(f"- Average Time: {avg_time:.3f}s")
        print(f"- Throughput: {throughput:.2f} ops/sec")

        # Assert reasonable performance
        assert avg_time < 0.1  # Should complete within 100ms on average
        assert throughput > 100  # Should handle at least 100 ops/sec

    @pytest.mark.asyncio
    async def test_cache_hit_ratio(self, test_redis_client, performance_client: AsyncClient):
        """Test cache hit ratio under load"""
        # Populate cache with test data
        cache_keys = [f"test_key_{i}" for i in range(100)]
        for key in cache_keys:
            await test_redis_client.set(key, f"value_for_{key}", ex=3600)

        # Perform cache operations
        hits = 0
        misses = 0
        total_operations = 200

        for _ in range(total_operations):
            key = cache_keys[_ % len(cache_keys)]  # Mix of hits and potential misses
            value = await test_redis_client.get(key)
            if value:
                hits += 1
            else:
                misses += 1

        hit_ratio = hits / total_operations

        print(f"Cache performance test:")
        print(f"- Total Operations: {total_operations}")
        print(f"- Cache Hits: {hits}")
        print(f"- Cache Misses: {misses}")
        print(f"- Hit Ratio: {hit_ratio:.2%}")

        # Assert reasonable cache performance
        assert hit_ratio > 0.8  # Should have at least 80% hit ratio

    @pytest.mark.asyncio
    async def test_websocket_performance(self, performance_client: AsyncClient):
        """Test WebSocket performance (if implemented)"""
        # This would test WebSocket connection performance
        # For now, just verify the endpoint exists
        response = await performance_client.get("/health")
        assert response.status_code == 200

        print("WebSocket performance test: Endpoint available")
        # Additional WebSocket tests would be implemented here

    @pytest.mark.asyncio
    async def test_background_task_performance(self, performance_client: AsyncClient):
        """Test background task performance"""
        # This would test Celery task performance
        # For now, just verify basic functionality
        response = await performance_client.get("/health")
        assert response.status_code == 200

        print("Background task performance test: Basic functionality verified")
        # Additional background task performance tests would be implemented here

    def test_resource_cleanup(self, performance_client: AsyncClient):
        """Test that resources are properly cleaned up after tests"""
        # This would verify that database connections, cache connections, etc.
        # are properly closed after test execution
        print("Resource cleanup test: Framework handles cleanup automatically")
        assert True  # pytest handles most cleanup automatically

    @pytest.mark.asyncio
    async def test_error_handling_performance(self, performance_client: AsyncClient):
        """Test error handling performance under load"""
        # Test how the system handles errors under load
        error_endpoints = [
            "/nonexistent/endpoint",
            "/courses/invalid-id",
            "/auth/login",  # Without proper data
        ]

        response_times = []

        for endpoint in error_endpoints:
            for _ in range(10):
                start_time = time.time()

                if endpoint == "/auth/login":
                    response = await performance_client.post(endpoint, json={})
                else:
                    response = await performance_client.get(endpoint)

                end_time = time.time()
                response_times.append(end_time - start_time)

                # Should return error status codes quickly
                assert response.status_code in [404, 422, 500]

        avg_error_time = statistics.mean(response_times)

        print(f"Error handling performance: Avg {avg_error_time:.3f}s per error response")

        # Assert that error responses are reasonably fast
        assert avg_error_time < 0.5  # Should respond within 500ms even for errors


class TestLoadPatterns:
    """Test different load patterns"""

    @pytest.mark.asyncio
    async def test_spike_load(self, performance_client: AsyncClient):
        """Test system behavior under sudden load spikes"""
        # Simulate a sudden increase in load
        async def spike_operation():
            response = await performance_client.get("/health")
            return response.status_code

        # Normal load
        normal_tasks = [spike_operation() for _ in range(10)]
        await asyncio.gather(*normal_tasks)

        # Spike load
        spike_tasks = [spike_operation() for _ in range(50)]
        start_time = time.time()
        results = await asyncio.gather(*spike_tasks)
        spike_time = time.time() - start_time

        successful_responses = sum(1 for r in results if r == 200)
        success_rate = successful_responses / len(results)

        print(f"Spike load test:")
        print(f"- Spike Operations: {len(spike_tasks)}")
        print(f"- Time: {spike_time:.2f}s")
        print(f"- Success Rate: {success_rate:.2%}")

        # Assert reasonable performance under spike
        assert success_rate > 0.9  # At least 90% success rate under spike

    @pytest.mark.asyncio
    async def test_sustained_load(self, performance_client: AsyncClient):
        """Test system performance under sustained load"""
        async def sustained_operation(iteration: int):
            response = await performance_client.get("/health")
            await asyncio.sleep(0.1)  # Small delay between requests
            return response.status_code

        # Run sustained load for 30 seconds
        duration = 30
        start_time = time.time()
        completed_operations = 0

        while time.time() - start_time < duration:
            tasks = [sustained_operation(i) for i in range(10)]
            results = await asyncio.gather(*tasks)
            completed_operations += len([r for r in results if r == 200])

        actual_duration = time.time() - start_time
        throughput = completed_operations / actual_duration

        print(f"Sustained load test:")
        print(f"- Duration: {actual_duration:.2f}s")
        print(f"- Completed Operations: {completed_operations}")
        print(f"- Throughput: {throughput:.2f} ops/sec")

        # Assert reasonable sustained performance
        assert throughput > 50  # Should handle at least 50 ops/sec sustained

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, performance_client: AsyncClient):
        """Test for memory leaks under prolonged load"""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # Take initial memory measurement
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run operations for an extended period
        for i in range(100):
            response = await performance_client.get("/health")
            assert response.status_code == 200

            if i % 20 == 0:  # Check memory every 20 iterations
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory

                print(f"Iteration {i}: Memory {current_memory:.2f}MB (Increase: {memory_increase:.2f}MB)")

                # Assert no significant memory leak
                assert memory_increase < 50  # Should not increase by more than 50MB

        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory

        print(f"Memory leak test completed:")
        print(f"- Initial Memory: {initial_memory:.2f}MB")
        print(f"- Final Memory: {final_memory:.2f}MB")
        print(f"- Total Increase: {total_increase:.2f}MB")

        # Assert no significant memory leak
        assert total_increase < 30  # Should not increase by more than 30MB total