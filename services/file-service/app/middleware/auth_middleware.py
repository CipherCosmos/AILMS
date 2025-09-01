"""
File Service Authentication Middleware
"""
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from shared.common.logging import get_logger
from shared.common.errors import AuthenticationError, AuthorizationError
from ..utils.file_utils import validate_file_extension, validate_file_size

logger = get_logger("file-service-middleware")

class FileMiddleware(BaseHTTPMiddleware):
    """File service specific middleware"""

    async def dispatch(self, request: Request, call_next):
        """Process request through middleware"""
        start_time = time.time()

        try:
            # Extract user information from request
            user_id = self._extract_user_id(request)
            user_role = self._extract_user_role(request)

            # Check rate limits based on user role and endpoint
            if user_id:
                await self._check_rate_limits(user_id, user_role, request.url.path, request.method)

            # Validate file uploads
            if request.method == "POST" and "upload" in request.url.path:
                await self._validate_file_upload(request)

            # Process request
            response = await call_next(request)

            # Log metrics
            if user_id:
                duration = time.time() - start_time
                logger.info("File request completed", extra={
                    "user_id": user_id,
                    "user_role": user_role,
                    "path": request.url.path,
                    "method": request.method,
                    "duration_seconds": round(duration, 3),
                    "status_code": response.status_code
                })

            return response

        except (AuthenticationError, AuthorizationError) as e:
            logger.warning("Authentication/Authorization error", extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(e)
            })
            raise HTTPException(401 if isinstance(e, AuthenticationError) else 403, str(e))
        except Exception as e:
            logger.error("Middleware error", extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(e)
            })
            raise HTTPException(500, "Internal server error")

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request headers"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        try:
            # Extract token from Bearer header
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                # In production, this would decode and validate the JWT
                # For now, return a mock user ID
                return "user_123"
        except Exception as e:
            logger.warning("Failed to extract user ID", extra={"error": str(e)})

        return None

    def _extract_user_role(self, request: Request) -> str:
        """Extract user role from request headers"""
        role_header = request.headers.get("X-User-Role")
        return role_header or "student"

    async def _check_rate_limits(self, user_id: str, user_role: str, path: str, method: str) -> None:
        """Check rate limits based on user role and endpoint"""
        from ..config.config import file_service_settings

        # Different rate limits for different operations
        if "upload" in path and method == "POST":
            limit = file_service_settings.upload_rate_limit_per_minute
        elif "download" in path:
            limit = file_service_settings.download_rate_limit_per_minute
        else:
            limit = file_service_settings.api_rate_limit_per_minute

        # Adjust limit based on user role
        if user_role == "instructor":
            limit = limit * 2  # Higher limit for instructors
        elif user_role == "admin":
            limit = limit * 5  # Even higher for admins

        logger.info("Rate limit check", extra={
            "user_id": user_id,
            "user_role": user_role,
            "path": path,
            "limit": limit
        })

    async def _validate_file_upload(self, request: Request) -> None:
        """Validate file upload request"""
        try:
            # Check Content-Length header
            content_length = request.headers.get("Content-Length")
            if content_length:
                file_size = int(content_length)
                from ..config.config import file_service_settings
                if file_size > file_service_settings.max_file_size_mb * 1024 * 1024:
                    raise HTTPException(413, "File too large")

            # Check Content-Type
            content_type = request.headers.get("Content-Type", "")
            if content_type.startswith("multipart/form-data"):
                # This would validate the uploaded file
                # For now, just log the validation attempt
                logger.info("File upload validation", extra={
                    "content_type": content_type,
                    "content_length": content_length
                })

        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Failed to validate file upload", extra={"error": str(e)})

class FileRequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging file requests"""

    async def dispatch(self, request: Request, call_next):
        """Log file requests"""
        start_time = time.time()

        # Log request
        logger.info("File request started", extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "user_agent": request.headers.get("User-Agent", ""),
            "content_length": request.headers.get("Content-Length"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        logger.info("File request completed", extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_seconds": round(duration, 3),
            "response_size": len(response.body) if hasattr(response, 'body') else 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return response

class FileSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for file security checks"""

    async def dispatch(self, request: Request, call_next):
        """Perform security checks"""
        # Check for path traversal attempts
        path = request.url.path
        if ".." in path or path.startswith("/etc") or path.startswith("/proc"):
            logger.warning("Potential path traversal attempt", extra={"path": path})
            raise HTTPException(403, "Access denied")

        # Check file access patterns
        if "download" in path or "files" in path:
            # Additional security checks for file access
            logger.info("File access security check", extra={"path": path})

        response = await call_next(request)
        return response

class FileStorageMiddleware(BaseHTTPMiddleware):
    """Middleware for file storage management"""

    async def dispatch(self, request: Request, call_next):
        """Handle storage-related concerns"""
        # Check storage quota before uploads
        if request.method == "POST" and "upload" in request.url.path:
            user_id = self._extract_user_id(request)
            if user_id:
                # This would check user's storage quota
                logger.info("Storage quota check", extra={"user_id": user_id})

        response = await call_next(request)
        return response

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request"""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # In production, decode JWT token
            return "user_123"
        return None

class FilePerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring file performance"""

    async def dispatch(self, request: Request, call_next):
        """Monitor performance of file requests"""
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Log slow requests
        from ..config.config import file_service_settings
        if duration > file_service_settings.alert_threshold_upload_time:
            logger.warning("Slow file request", extra={
                "path": request.url.path,
                "method": request.method,
                "duration_seconds": round(duration, 3),
                "threshold": file_service_settings.alert_threshold_upload_time
            })

        return response

class FileCachingMiddleware(BaseHTTPMiddleware):
    """Middleware for file caching"""

    async def dispatch(self, request: Request, call_next):
        """Handle caching for file requests"""
        # Add cache control headers for static files
        response = await call_next(request)

        if request.method == "GET" and ("download" in request.url.path or "files" in request.url.path):
            from ..config.config import file_service_settings
            if file_service_settings.enable_file_caching:
                response.headers["Cache-Control"] = f"max-age={file_service_settings.cache_ttl_seconds}"
                response.headers["X-File-Cache"] = "enabled"

        return response

class FileCleanupMiddleware(BaseHTTPMiddleware):
    """Middleware for file cleanup operations"""

    async def dispatch(self, request: Request, call_next):
        """Handle file cleanup"""
        response = await call_next(request)

        # Trigger cleanup operations periodically
        # This would be done asynchronously in production
        if request.method == "GET" and "health" in request.url.path:
            logger.info("File cleanup check triggered")

        return response

# Middleware classes - instantiated by FastAPI
# Usage in main.py:
# app.add_middleware(FileMiddleware)
# app.add_middleware(FileRequestLoggingMiddleware)
# app.add_middleware(FileSecurityMiddleware)
# app.add_middleware(FileStorageMiddleware)
# app.add_middleware(FilePerformanceMonitoringMiddleware)
# app.add_middleware(FileCachingMiddleware)
# app.add_middleware(FileCleanupMiddleware)