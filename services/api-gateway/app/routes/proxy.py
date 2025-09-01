"""
Request proxying routes for API Gateway
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
from typing import Dict

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

def determine_target_service(path: str) -> str:
    """Determine which service should handle the request"""
    path_parts = path.split("/")
    if not path_parts or path_parts[0] == "":
        return None

    first_part = f"/{path_parts[0]}"
    target_service = SERVICE_ROUTES.get(first_part)

    if not target_service:
        # Try to match partial paths
        for route_prefix, service in SERVICE_ROUTES.items():
            if path.startswith(route_prefix[1:]):  # Remove leading slash
                target_service = service
                break

    return target_service

def clean_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Remove hop-by-hop headers that shouldn't be forwarded"""
    hop_by_hop_headers = [
        "connection", "keep-alive", "proxy-authenticate",
        "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"
    ]

    cleaned = {}
    for key, value in headers.items():
        if key.lower() not in hop_by_hop_headers:
            cleaned[key] = value

    return cleaned

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_request(request: Request, path: str):
    """
    Proxy requests to appropriate microservices.

    This is the main routing endpoint that forwards requests to the appropriate
    service based on the URL path.
    """
    try:
        # Handle /api prefix
        if path.startswith("api/"):
            path = path[4:]  # Remove "api/" prefix

        # Determine target service
        target_service = determine_target_service(path)

        if not target_service:
            logger.warning("No service found for path", extra={"path": path})
            raise HTTPException(404, f"No service found for path: {path}")

        service_url = SERVICES.get(target_service)
        if not service_url:
            logger.error("Service URL not configured", extra={"service": target_service})
            raise HTTPException(503, f"Service {target_service} not available")

        # Construct target URL
        target_url = f"{service_url}/{path}"

        # Get request data
        body = await request.body()
        headers = clean_headers(dict(request.headers))

        # Add gateway identifier
        headers["X-Gateway"] = "lms-api-gateway"
        headers["X-Forwarded-For"] = request.client.host if request.client else "unknown"
        headers["X-Request-ID"] = request.headers.get("X-Request-ID", "gateway-generated")

        logger.info("Proxying request", extra={
            "method": request.method,
            "path": path,
            "target_service": target_service,
            "target_url": target_url,
            "user_agent": headers.get("user-agent", "unknown")
        })

        # Forward the request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )

            # Log response
            logger.info("Proxy response received", extra={
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "target_service": target_service
            })

            # Return response
            # Handle different content types
            if response.headers.get("content-type", "").startswith("application/json"):
                try:
                    content = response.json()
                except:
                    content = response.text
            else:
                content = response.text

            return JSONResponse(
                content=content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )

    except httpx.TimeoutException:
        logger.error("Service timeout", extra={"path": path, "target_service": target_service})
        raise HTTPException(504, "Service timeout")
    except httpx.ConnectError:
        logger.error("Service connection failed", extra={"path": path, "target_service": target_service})
        raise HTTPException(503, f"Service {target_service} unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Proxy error", extra={
            "path": path,
            "target_service": target_service,
            "error": str(e)
        })
        raise HTTPException(500, f"Gateway error: {str(e)}")

@router.get("/services")
async def list_services():
    """List all available services"""
    return {
        "services": list(SERVICES.keys()),
        "endpoints": SERVICES,
        "routes": SERVICE_ROUTES
    }

@router.get("/services/{service_name}")
async def service_info(service_name: str):
    """Get information about a specific service"""
    if service_name not in SERVICES:
        raise HTTPException(404, f"Service '{service_name}' not found")

    return {
        "service": service_name,
        "url": SERVICES[service_name],
        "routes": [route for route, service in SERVICE_ROUTES.items() if service == service_name]
    }

@router.get("/routes")
async def list_routes():
    """List all route mappings"""
    return {
        "route_mappings": SERVICE_ROUTES,
        "services": SERVICES
    }

# Legacy compatibility endpoints
@router.get("/ws-test")
async def websocket_test():
    """WebSocket test endpoint for backward compatibility"""
    return {
        "message": "WebSocket endpoints available through individual services",
        "services": {
            "notification_service": "ws://notification-service:8007/ws",
            "realtime_updates": "Available through notification service"
        }
    }