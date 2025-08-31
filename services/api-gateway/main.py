"""
API Gateway - Main entry point for the LMS microservices architecture
"""
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import asyncio
import time
import sys
import os
from typing import Dict, Any

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.config.config import settings

app = FastAPI(title='LMS API Gateway', version='1.0.0')

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

# Service routes mapping
SERVICE_ROUTES = {
    "/auth": "auth",
    "/courses": "course",
    "/users": "user",
    "/user": "user",  # For backward compatibility
    "/ai": "ai",
    "/assignments": "assessment",
    "/analytics": "analytics",
    "/notifications": "notification",
    "/files": "file"
}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Health check for all services
async def check_service_health(service_name: str, service_url: str) -> Dict[str, Any]:
    """Check health of a specific service"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{service_url}/health")
            if response.status_code == 200:
                return {"status": "healthy", "service": service_name}
            else:
                return {"status": "unhealthy", "service": service_name, "error": f"Status {response.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "service": service_name, "error": str(e)}

@app.get("/health")
async def gateway_health():
    """Gateway health check"""
    return {"status": "healthy", "service": "api-gateway"}

@app.get("/health/services")
async def services_health():
    """Check health of all services"""
    health_checks = []
    for service_name, service_url in SERVICES.items():
        health_checks.append(check_service_health(service_name, service_url))

    results = await asyncio.gather(*health_checks, return_exceptions=True)

    services_status = {}
    overall_status = "healthy"

    for result in results:
        if isinstance(result, dict):
            services_status[result["service"]] = result
            if result["status"] == "unhealthy":
                overall_status = "degraded"
        else:
            # Exception occurred
            services_status["unknown"] = {"status": "error", "error": str(result)}
            overall_status = "unhealthy"

    return {
        "status": overall_status,
        "services": services_status,
        "timestamp": time.time()
    }

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_request(request: Request, path: str):
    """Proxy requests to appropriate services"""

    # Determine target service
    path_parts = path.split("/")
    if not path_parts or path_parts[0] == "":
        # Root path
        return {"message": "LMS API Gateway", "status": "running", "version": "1.0.0"}

    first_part = f"/{path_parts[0]}"
    target_service = SERVICE_ROUTES.get(first_part)

    if not target_service:
        # Try to match partial paths
        for route_prefix, service in SERVICE_ROUTES.items():
            if path.startswith(route_prefix[1:]):  # Remove leading slash
                target_service = service
                break

    if not target_service:
        raise HTTPException(404, f"No service found for path: {path}")

    service_url = SERVICES.get(target_service)
    if not service_url:
        raise HTTPException(503, f"Service {target_service} not available")

    # Construct target URL
    target_url = f"{service_url}/{path}"

    # Get request data
    body = await request.body()
    headers = dict(request.headers)

    # Remove hop-by-hop headers
    hop_by_hop_headers = [
        "connection", "keep-alive", "proxy-authenticate",
        "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"
    ]
    for header in hop_by_hop_headers:
        headers.pop(header, None)

    # Add gateway identifier
    headers["X-Gateway"] = "lms-api-gateway"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Forward the request
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )

            # Return response
            return JSONResponse(
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )

    except httpx.TimeoutException:
        raise HTTPException(504, "Service timeout")
    except httpx.ConnectError:
        raise HTTPException(503, f"Service {target_service} unavailable")
    except Exception as e:
        raise HTTPException(500, f"Gateway error: {str(e)}")

# Legacy route compatibility
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "message": "AI LMS Backend - Microservices Architecture",
        "status": "running",
        "version": "2.0.0",
        "services": list(SERVICES.keys()),
        "docs": "/docs",
        "health": "/health",
        "service_health": "/health/services"
    }

@app.get("/api/")
async def api_root():
    """API root endpoint"""
    return {
        "message": "LMS API",
        "services": {
            "auth": "/auth",
            "courses": "/courses",
            "users": "/users",
            "ai": "/ai",
            "assignments": "/assignments",
            "analytics": "/analytics",
            "notifications": "/notifications",
            "files": "/files"
        }
    }

# WebSocket support (if needed)
@app.get("/ws-test")
async def websocket_test():
    """WebSocket test endpoint"""
    return {
        "message": "WebSocket endpoints available through individual services",
        "services": {
            "notification_service": "ws://notification-service:8007/ws",
            "realtime_updates": "Available through notification service"
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.environment == 'development')