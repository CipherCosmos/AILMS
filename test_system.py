#!/usr/bin/env python3
"""
System Test Script for LMS Microservices
"""
import asyncio
import httpx
import time
import sys
from typing import Dict, List, Any

SERVICES = {
    "api-gateway": "http://localhost:8000",
    "auth-service": "http://localhost:8001",
    "course-service": "http://localhost:8002",
    "user-service": "http://localhost:8003",
    "ai-service": "http://localhost:8004",
    "assessment-service": "http://localhost:8005",
    "analytics-service": "http://localhost:8006",
    "notification-service": "http://localhost:8007",
    "file-service": "http://localhost:8008",
}


async def test_service_health(service_name: str, service_url: str) -> Dict[str, Any]:
    """Test health of a specific service"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            start_time = time.time()
            response = await client.get(f"{service_url}/health")
            response_time = time.time() - start_time

            if response.status_code == 200:
                return {
                    "service": service_name,
                    "status": "healthy",
                    "response_time": round(response_time, 3),
                    "url": service_url,
                }
            else:
                return {
                    "service": service_name,
                    "status": "unhealthy",
                    "error": f"Status {response.status_code}",
                    "url": service_url,
                }
    except Exception as e:
        return {
            "service": service_name,
            "status": "unhealthy",
            "error": str(e),
            "url": service_url,
        }


async def test_api_gateway():
    """Test API Gateway functionality"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test root endpoint
            response = await client.get("http://localhost:8000/")
            if response.status_code != 200:
                return {
                    "status": "failed",
                    "error": f"Root endpoint failed: {response.status_code}",
                }

            # Test health endpoint
            response = await client.get("http://localhost:8000/health")
            if response.status_code != 200:
                return {
                    "status": "failed",
                    "error": f"Health endpoint failed: {response.status_code}",
                }

            # Test service health endpoint
            response = await client.get("http://localhost:8000/health/services")
            if response.status_code != 200:
                return {
                    "status": "failed",
                    "error": f"Service health endpoint failed: {response.status_code}",
                }

            return {"status": "passed"}

    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def test_auth_service():
    """Test Auth Service functionality"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test registration
            test_user = {
                "email": "test@example.com",
                "name": "Test User",
                "password": "testpassword123",
                "role": "student",
            }

            response = await client.post(
                "http://localhost:8001/auth/register", json=test_user
            )
            if response.status_code not in [200, 400]:  # 400 is expected if user exists
                return {
                    "status": "failed",
                    "error": f"Registration failed: {response.status_code}",
                }

            # Test login
            login_data = {"email": "test@example.com", "password": "testpassword123"}

            response = await client.post(
                "http://localhost:8001/auth/login", json=login_data
            )
            if response.status_code not in [200, 401]:
                return {
                    "status": "failed",
                    "error": f"Login failed: {response.status_code}",
                }

            return {"status": "passed"}

    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def run_system_tests():
    """Run comprehensive system tests"""
    print("Starting LMS Microservices System Tests")
    print("=" * 50)

    # Test individual services
    print("\nTesting Individual Services:")
    service_tests = []
    for service_name, service_url in SERVICES.items():
        result = await test_service_health(service_name, service_url)
        service_tests.append(result)

        status_icon = "[OK]" if result["status"] == "healthy" else "[FAIL]"
        print(f"{status_icon} {service_name}: {result['status']}")
        if result["status"] == "healthy":
            print(".3f")
        else:
            print(f"   Error: {result.get('error', 'Unknown')}")

    # Test API Gateway
    print("\nTesting API Gateway:")
    gateway_test = await test_api_gateway()
    if gateway_test["status"] == "passed":
        print("[OK] API Gateway: All endpoints responding")
    else:
        print(f"[FAIL] API Gateway: {gateway_test.get('error', 'Failed')}")

    # Test Auth Service
    print("\nTesting Auth Service:")
    auth_test = await test_auth_service()
    if auth_test["status"] == "passed":
        print("[OK] Auth Service: Registration and login working")
    else:
        print(f"[FAIL] Auth Service: {auth_test.get('error', 'Failed')}")

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")

    healthy_services = len([s for s in service_tests if s["status"] == "healthy"])
    total_services = len(service_tests)

    print(f"Services: {healthy_services}/{total_services} healthy")
    print(
        f"API Gateway: {'[OK] Working' if gateway_test['status'] == 'passed' else '[FAIL] Failed'}"
    )
    print(
        f"Auth Service: {'[OK] Working' if auth_test['status'] == 'passed' else '[FAIL] Failed'}"
    )

    if (
        healthy_services == total_services
        and gateway_test["status"] == "passed"
        and auth_test["status"] == "passed"
    ):
        print("\nAll tests passed! System is ready for use.")
        return True
    else:
        print("\nSome tests failed. Check the output above for details.")
        return False


async def main():
    """Main test function"""
    try:
        success = await run_system_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
