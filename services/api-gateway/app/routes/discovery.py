"""
Service discovery routes for API Gateway
"""
from fastapi import APIRouter, HTTPException
import httpx
import asyncio
from typing import Dict, Any, List

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

# Service metadata
SERVICE_METADATA = {
    "auth": {
        "description": "User authentication and authorization",
        "version": "1.0.0",
        "capabilities": ["login", "register", "token_refresh", "user_management"],
        "dependencies": ["mongodb", "redis"]
    },
    "course": {
        "description": "Course management and content delivery",
        "version": "1.0.0",
        "capabilities": ["course_crud", "lesson_management", "progress_tracking", "ai_generation"],
        "dependencies": ["mongodb", "redis", "gemini_ai"]
    },
    "user": {
        "description": "User profiles and personalized features",
        "version": "1.0.0",
        "capabilities": ["profile_management", "career_tracking", "study_plans", "skill_analysis"],
        "dependencies": ["mongodb", "redis"]
    },
    "ai": {
        "description": "AI-powered content generation and analysis",
        "version": "1.0.0",
        "capabilities": ["content_generation", "enhancement", "performance_analysis", "personalization"],
        "dependencies": ["mongodb", "redis", "gemini_ai"]
    },
    "assessment": {
        "description": "Assignment and quiz management",
        "version": "1.0.0",
        "capabilities": ["assignment_management", "grading", "plagiarism_detection"],
        "dependencies": ["mongodb", "redis"]
    },
    "analytics": {
        "description": "Learning analytics and reporting",
        "version": "1.0.0",
        "capabilities": ["course_analytics", "student_performance", "progress_tracking"],
        "dependencies": ["mongodb", "redis"]
    },
    "notification": {
        "description": "Real-time notifications and communication",
        "version": "1.0.0",
        "capabilities": ["websocket", "email_notifications", "push_notifications"],
        "dependencies": ["mongodb", "redis"]
    },
    "file": {
        "description": "File upload, storage, and management",
        "version": "1.0.0",
        "capabilities": ["file_upload", "storage", "access_control"],
        "dependencies": ["mongodb", "redis", "filesystem"]
    }
}

@router.get("/services")
async def list_services():
    """List all registered services with metadata"""
    services_info = []
    for service_name, service_url in SERVICES.items():
        metadata = SERVICE_METADATA.get(service_name, {})
        services_info.append({
            "name": service_name,
            "url": service_url,
            "status": "registered",
            **metadata
        })

    return {
        "services": services_info,
        "total_count": len(services_info),
        "gateway_version": "1.0.0"
    }

@router.get("/services/{service_name}")
async def get_service_details(service_name: str):
    """Get detailed information about a specific service"""
    if service_name not in SERVICES:
        raise HTTPException(404, f"Service '{service_name}' not found")

    service_url = SERVICES[service_name]
    metadata = SERVICE_METADATA.get(service_name, {})

    # Try to get additional info from the service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{service_url}/")
            if response.status_code == 200:
                service_info = response.json()
            else:
                service_info = {}
    except Exception:
        service_info = {}

    return {
        "name": service_name,
        "url": service_url,
        "status": "active",
        "metadata": metadata,
        "service_info": service_info,
        "last_updated": "2024-01-01T00:00:00Z"  # Would use actual timestamp
    }

@router.get("/capabilities")
async def list_capabilities():
    """List all capabilities across all services"""
    capabilities = {}
    for service_name, metadata in SERVICE_METADATA.items():
        service_caps = metadata.get("capabilities", [])
        for cap in service_caps:
            if cap not in capabilities:
                capabilities[cap] = []
            capabilities[cap].append(service_name)

    return {
        "capabilities": capabilities,
        "total_capabilities": len(capabilities),
        "services_by_capability": {cap: services for cap, services in capabilities.items()}
    }

@router.get("/capabilities/{capability}")
async def get_capability_providers(capability: str):
    """Get services that provide a specific capability"""
    providers = []
    for service_name, metadata in SERVICE_METADATA.items():
        if capability in metadata.get("capabilities", []):
            providers.append({
                "service": service_name,
                "url": SERVICES[service_name],
                "description": metadata.get("description", ""),
                "version": metadata.get("version", "1.0.0")
            })

    if not providers:
        raise HTTPException(404, f"No services provide capability: {capability}")

    return {
        "capability": capability,
        "providers": providers,
        "provider_count": len(providers)
    }

@router.get("/dependencies")
async def list_dependencies():
    """List all service dependencies"""
    dependencies = {}
    for service_name, metadata in SERVICE_METADATA.items():
        service_deps = metadata.get("dependencies", [])
        for dep in service_deps:
            if dep not in dependencies:
                dependencies[dep] = []
            dependencies[dep].append(service_name)

    return {
        "dependencies": dependencies,
        "total_dependencies": len(dependencies),
        "services_by_dependency": {dep: services for dep, services in dependencies.items()}
    }

@router.get("/health-matrix")
async def get_health_matrix():
    """Get a matrix of service health status"""
    try:
        async def check_service(service_name: str, service_url: str):
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.get(f"{service_url}/health")
                    return {
                        "service": service_name,
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "response_time": response.elapsed.total_seconds()
                    }
            except Exception as e:
                return {
                    "service": service_name,
                    "status": "unhealthy",
                    "error": str(e)
                }

        # Check all services concurrently
        health_checks = []
        for service_name, service_url in SERVICES.items():
            health_checks.append(check_service(service_name, service_url))

        results = await asyncio.gather(*health_checks, return_exceptions=True)

        health_matrix = {}
        summary = {"healthy": 0, "unhealthy": 0, "total": len(SERVICES)}

        for result in results:
            if isinstance(result, dict):
                service_name = result["service"]
                health_matrix[service_name] = result
                if result["status"] == "healthy":
                    summary["healthy"] += 1
                else:
                    summary["unhealthy"] += 1

        return {
            "health_matrix": health_matrix,
            "summary": summary,
            "overall_status": "healthy" if summary["unhealthy"] == 0 else "degraded",
            "timestamp": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow()
        }

    except Exception as e:
        logger.error("Health matrix check failed", extra={"error": str(e)})
        raise HTTPException(503, "Health matrix check failed")

@router.get("/topology")
async def get_service_topology():
    """Get the service topology and relationships"""
    topology = {
        "gateway": {
            "name": "api-gateway",
            "type": "entry_point",
            "connects_to": list(SERVICES.keys()),
            "port": 8000
        },
        "services": {}
    }

    for service_name, service_url in SERVICES.items():
        metadata = SERVICE_METADATA.get(service_name, {})
        topology["services"][service_name] = {
            "name": service_name,
            "url": service_url,
            "type": "microservice",
            "capabilities": metadata.get("capabilities", []),
            "dependencies": metadata.get("dependencies", []),
            "connects_from": ["api-gateway"]
        }

    return {
        "topology": topology,
        "description": "Service mesh topology showing relationships between gateway and microservices",
        "total_services": len(SERVICES) + 1  # +1 for gateway
    }

@router.get("/endpoints")
async def list_endpoints():
    """List all API endpoints across services"""
    endpoints = {
        "auth": [
            "POST /auth/register",
            "POST /auth/login",
            "POST /auth/refresh",
            "GET /auth/me",
            "PUT /auth/me",
            "GET /auth/users",
            "DELETE /auth/users/{uid}",
            "PUT /auth/users/{uid}"
        ],
        "course": [
            "POST /courses",
            "GET /courses",
            "GET /courses/{cid}",
            "PUT /courses/{cid}",
            "POST /courses/{cid}/enroll",
            "POST /courses/ai/generate_course",
            "POST /courses/{cid}/lessons",
            "POST /courses/{cid}/progress",
            "GET /courses/{cid}/progress"
        ],
        "user": [
            "GET /users/profile",
            "PUT /users/profile",
            "GET /users/career-profile",
            "PUT /users/career-profile",
            "GET /users/study-plan",
            "GET /users/skill-gaps",
            "GET /users/career-readiness",
            "GET /users/learning-analytics",
            "GET /users/achievements"
        ],
        "ai": [
            "POST /ai/generate-course",
            "POST /ai/enhance-content",
            "POST /ai/generate-quiz",
            "POST /ai/analyze-performance",
            "POST /ai/personalize-learning"
        ],
        "assessment": [
            "POST /assignments",
            "GET /assignments/{course_id}",
            "POST /submissions",
            "GET /submissions/{assignment_id}",
            "POST /grade/{submission_id}"
        ],
        "analytics": [
            "GET /analytics/course/{course_id}",
            "GET /analytics/student/{user_id}"
        ],
        "notification": [
            "WebSocket /ws/{user_id}",
            "POST /notifications",
            "GET /notifications",
            "PUT /notifications/{notification_id}/read"
        ],
        "file": [
            "POST /upload",
            "GET /files",
            "GET /files/{file_id}",
            "DELETE /files/{file_id}"
        ]
    }

    return {
        "endpoints": endpoints,
        "total_endpoints": sum(len(service_endpoints) for service_endpoints in endpoints.values()),
        "services_count": len(endpoints)
    }

@router.get("/status")
async def get_gateway_status():
    """Get comprehensive gateway status"""
    return {
        "gateway": {
            "name": "api-gateway",
            "version": "1.0.0",
            "status": "active",
            "uptime": "N/A",  # Would track actual uptime
            "port": 8000
        },
        "services": {
            "registered": len(SERVICES),
            "active": len(SERVICES),  # Would check actual status
            "endpoints": "N/A"  # Would count actual endpoints
        },
        "configuration": {
            "environment": "production",  # Would get from settings
            "cors_enabled": True,
            "rate_limiting": True,
            "health_checks": True
        },
        "last_updated": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow()
    }