"""
Authentication Middleware for User Service
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List, Optional
import time

from shared.common.logging import get_logger
from ..utils.user_utils import get_current_user

logger = get_logger("user-service-middleware")

class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for user service"""

    def __init__(self, app, exclude_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json", "/redoc"]

    async def dispatch(self, request: Request, call_next):
        """Process each request through authentication middleware"""

        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        start_time = time.time()

        try:
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization", "")
            token = None

            if auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Remove "Bearer " prefix
            elif auth_header:
                token = auth_header

            # Get current user
            if token:
                try:
                    user = await get_current_user(token)
                    # Add user to request state
                    request.state.user = user
                    request.state.user_id = user["id"]
                    request.state.user_role = user.get("role", "student")

                    logger.info("Authentication successful", extra={
                        "user_id": user["id"],
                        "path": request.url.path,
                        "method": request.method
                    })

                except Exception as e:
                    logger.warning("Authentication failed", extra={
                        "path": request.url.path,
                        "error": str(e)
                    })
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Authentication failed", "error": str(e)}
                    )
            else:
                # No token provided - add anonymous user state
                request.state.user = None
                request.state.user_id = None
                request.state.user_role = "anonymous"

            # Process request
            response = await call_next(request)

            # Log request completion
            process_time = time.time() - start_time
            logger.info("Request completed", extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "process_time": round(process_time, 3),
                "user_id": getattr(request.state, 'user_id', None)
            })

            return response

        except Exception as e:
            logger.error("Middleware error", extra={
                "path": request.url.path,
                "error": str(e)
            })
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )

class RoleBasedMiddleware(BaseHTTPMiddleware):
    """Role-based access control middleware"""

    def __init__(self, app, role_requirements: Optional[dict] = None):
        super().__init__(app)
        self.role_requirements = role_requirements or {}

    async def dispatch(self, request: Request, call_next):
        """Check role-based permissions"""

        path = request.url.path
        method = request.method

        # Check if path has role requirements
        required_roles = self._get_required_roles(path, method)

        if required_roles:
            user_role = getattr(request.state, 'user_role', 'anonymous')

            if user_role not in required_roles:
                logger.warning("Access denied", extra={
                    "path": path,
                    "method": method,
                    "user_role": user_role,
                    "required_roles": required_roles
                })
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Insufficient permissions"}
                )

        return await call_next(request)

    def _get_required_roles(self, path: str, method: str) -> list:
        """Get required roles for a path and method"""
        # Check exact path match
        if path in self.role_requirements:
            return self.role_requirements[path].get(method, [])

        # Check pattern matching (simple implementation)
        for pattern, requirements in self.role_requirements.items():
            if pattern in path:
                return requirements.get(method, [])

        return []

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for user operations"""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # Simple in-memory storage (use Redis in production)

    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting"""

        # Get client identifier (IP address for now)
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, 'user_id', client_ip)

        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        # Clean old requests
        if user_id in self.requests:
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if req_time > window_start
            ]
        else:
            self.requests[user_id] = []

        # Check rate limit
        if len(self.requests[user_id]) >= self.requests_per_minute:
            logger.warning("Rate limit exceeded", extra={
                "user_id": user_id,
                "client_ip": client_ip,
                "path": request.url.path
            })
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."}
            )

        # Add current request
        self.requests[user_id].append(current_time)

        return await call_next(request)

# Middleware configuration
def create_auth_middleware(exclude_paths: Optional[List[str]] = None):
    """Create authentication middleware"""
    return AuthMiddleware(None, exclude_paths=exclude_paths or ["/health", "/docs", "/openapi.json"])

def create_role_middleware(role_requirements: Optional[dict] = None):
    """Create role-based middleware"""
    return RoleBasedMiddleware(None, role_requirements=role_requirements)

def create_rate_limit_middleware(requests_per_minute: int = 60):
    """Create rate limiting middleware"""
    return RateLimitMiddleware(None, requests_per_minute=requests_per_minute)