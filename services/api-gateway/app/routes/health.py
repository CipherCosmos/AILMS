"""
Health check routes for API Gateway
"""
from fastapi import APIRouter, HTTPException
import httpx
import asyncio
import time
from typing import Dict, Any

from shared.common.logging import get_logger

logger = get_logger("api-gateway")
router = APIRouter()

# Service endpoints
SERVICES = {
    "auth": "http://auth-service:8001",
    "course": "http://course-service:8002",
    "user": "http://user-service:8003",
    "ai": "http://ai-service:8004",
    "assessment": "http://assessment-service:8005",
    "analytics": "http://analytics-service:8006",
    "notification": "http://notification-service:8007",
    "file": "http://file-service:8008"
}

async def check_service_health(service_name: str, service_url: str) -> Dict[str, Any]:
    """Check health of a specific service"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{service_url}/health")
            if response.status_code == 200:
                return {"status": "healthy", "service": service_name, "response_time": response.elapsed.total_seconds()}
            else:
                return {
                    "status": "unhealthy",
                    "service": service_name,
                    "error": f"Status {response.status_code}",
                    "response_time": response.elapsed.total_seconds()
                }
    except httpx.TimeoutException:
        return {"status": "unhealthy", "service": service_name, "error": "Timeout"}
    except httpx.ConnectError:
        return {"status": "unhealthy", "service": service_name, "error": "Connection failed"}
    except Exception as e:
        return {"status": "unhealthy", "service": service_name, "error": str(e)}

@router.get("/health")
async def gateway_health():
    """Gateway health check"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "1.0.0",
        "timestamp": time.time()
    }

@router.get("/health/services")
async def services_health():
    """Check health of all services"""
    try:
        health_checks = []
        for service_name, service_url in SERVICES.items():
            health_checks.append(check_service_health(service_name, service_url))

        results = await asyncio.gather(*health_checks, return_exceptions=True)

        services_status = {}
        overall_status = "healthy"
        healthy_count = 0
        total_count = len(SERVICES)

        for result in results:
            if isinstance(result, dict):
                services_status[result["service"]] = result
                if result["status"] == "healthy":
                    healthy_count += 1
                else:
                    overall_status = "degraded"
            else:
                # Exception occurred
                services_status["unknown"] = {"status": "error", "error": str(result)}
                overall_status = "unhealthy"

        return {
            "status": overall_status,
            "services": services_status,
            "summary": {
                "total_services": total_count,
                "healthy_services": healthy_count,
                "unhealthy_services": total_count - healthy_count
            },
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error("Services health check failed", extra={"error": str(e)})
        raise HTTPException(503, "Health check failed")

@router.get("/health/services/{service_name}")
async def service_health(service_name: str):
    """Check health of a specific service"""
    if service_name not in SERVICES:
        raise HTTPException(404, f"Service '{service_name}' not found")

    service_url = SERVICES[service_name]
    result = await check_service_health(service_name, service_url)

    return {
        "service": service_name,
        "url": service_url,
        "health": result,
        "timestamp": time.time()
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with performance metrics"""
    try:
        # Check all services
        health_checks = []
        for service_name, service_url in SERVICES.items():
            health_checks.append(check_service_health(service_name, service_url))

        results = await asyncio.gather(*health_checks, return_exceptions=True)

        services_status = {}
        response_times = []
        healthy_count = 0

        for result in results:
            if isinstance(result, dict):
                services_status[result["service"]] = result
                if result["status"] == "healthy":
                    healthy_count += 1
                    if "response_time" in result:
                        response_times.append(result["response_time"])

        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        return {
            "status": "healthy" if healthy_count == len(SERVICES) else "degraded",
            "services": services_status,
            "performance": {
                "average_response_time": round(avg_response_time, 3),
                "total_services": len(SERVICES),
                "healthy_services": healthy_count,
                "health_percentage": round((healthy_count / len(SERVICES)) * 100, 1)
            },
            "system_info": {
                "gateway_version": "1.0.0",
                "services_count": len(SERVICES),
                "environment": "production"  # Would get from settings
            },
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error("Detailed health check failed", extra={"error": str(e)})
        raise HTTPException(503, "Detailed health check failed")

@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    try:
        # Quick check of critical services
        critical_services = ["auth", "course", "user"]
        health_checks = []

        for service_name in critical_services:
            if service_name in SERVICES:
                service_url = SERVICES[service_name]
                health_checks.append(check_service_health(service_name, service_url))

        results = await asyncio.gather(*health_checks, return_exceptions=True)

        for result in results:
            if isinstance(result, dict) and result["status"] != "healthy":
                raise HTTPException(503, f"Critical service {result['service']} is unhealthy")

        return {"status": "ready"}
    except Exception:
        raise HTTPException(503, "Service not ready")

@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}

@router.get("/health/metrics")
async def health_metrics():
    """Health metrics for monitoring systems"""
    try:
        health_checks = []
        for service_name, service_url in SERVICES.items():
            health_checks.append(check_service_health(service_name, service_url))

        results = await asyncio.gather(*health_checks, return_exceptions=True)

        metrics = {
            "gateway_up": 1,
            "services_total": len(SERVICES),
            "services_healthy": 0,
            "services_unhealthy": 0,
            "response_times": []
        }

        for result in results:
            if isinstance(result, dict):
                if result["status"] == "healthy":
                    metrics["services_healthy"] += 1
                    if "response_time" in result:
                        metrics["response_times"].append(result["response_time"])
                else:
                    metrics["services_unhealthy"] += 1

        # Calculate average response time
        if metrics["response_times"]:
            metrics["avg_response_time"] = round(sum(metrics["response_times"]) / len(metrics["response_times"]), 3)
        else:
            metrics["avg_response_time"] = 0

        return metrics

    except Exception as e:
        logger.error("Health metrics failed", extra={"error": str(e)})
        return {
            "gateway_up": 0,
            "error": str(e)
        }