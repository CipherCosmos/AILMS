"""
API Versioning system for LMS microservices
"""
import re
from typing import Dict, List, Optional, Any, Callable
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from shared.common.logging import get_logger

logger = get_logger("common-versioning")


class APIVersion:
    """API Version representation"""

    def __init__(self, version: str, release_date: str, deprecated: bool = False, sunset_date: Optional[str] = None):
        self.version = version
        self.release_date = release_date
        self.deprecated = deprecated
        self.sunset_date = sunset_date

    def __str__(self):
        return self.version

    def __repr__(self):
        return f"APIVersion({self.version}, deprecated={self.deprecated})"


class APIVersionManager:
    """Manages API versions and routing"""

    def __init__(self):
        self.versions: Dict[str, APIVersion] = {}
        self.version_routes: Dict[str, Dict[str, Callable]] = {}
        self.default_version = "v1"
        self.supported_versions = ["v1"]

    def register_version(self, version: APIVersion):
        """Register a new API version"""
        self.versions[version.version] = version
        self.version_routes[version.version] = {}
        logger.info(f"Registered API version: {version}")

    def add_versioned_route(self, version: str, path: str, handler: Callable):
        """Add a route for a specific version"""
        if version not in self.version_routes:
            self.version_routes[version] = {}

        self.version_routes[version][path] = handler
        logger.debug(f"Added route {path} for version {version}")

    def get_version_from_request(self, request: Request) -> str:
        """Extract API version from request"""
        # Check Accept header
        accept_header = request.headers.get("Accept", "")
        if "application/vnd.lms." in accept_header:
            version_match = re.search(r'application/vnd\.lms\.(\w+)\+', accept_header)
            if version_match:
                version = version_match.group(1)
                if version in self.versions:
                    return version

        # Check custom header
        version_header = request.headers.get("X-API-Version")
        if version_header and version_header in self.versions:
            return version_header

        # Check URL path
        path_parts = request.url.path.split("/")
        if len(path_parts) > 1 and path_parts[1].startswith("v"):
            version = path_parts[1]
            if version in self.versions:
                return version

        # Check query parameter
        version_param = request.query_params.get("api_version")
        if version_param and version_param in self.versions:
            return version_param

        return self.default_version

    def get_handler_for_version(self, version: str, path: str) -> Optional[Callable]:
        """Get the handler for a specific version and path"""
        if version in self.version_routes and path in self.version_routes[version]:
            return self.version_routes[version][path]

        # Fallback to default version
        if self.default_version in self.version_routes and path in self.version_routes[self.default_version]:
            return self.version_routes[self.default_version][path]

        return None

    def is_version_supported(self, version: str) -> bool:
        """Check if a version is supported"""
        return version in self.versions

    def get_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific version"""
        if version not in self.versions:
            return None

        v = self.versions[version]
        return {
            "version": v.version,
            "release_date": v.release_date,
            "deprecated": v.deprecated,
            "sunset_date": v.sunset_date,
            "status": "deprecated" if v.deprecated else "active"
        }

    def list_versions(self) -> List[Dict[str, Any]]:
        """List all available versions"""
        return [info for v in self.versions.keys() if (info := self.get_version_info(v)) is not None]

    def deprecate_version(self, version: str, sunset_date: Optional[str] = None):
        """Mark a version as deprecated"""
        if version in self.versions:
            self.versions[version].deprecated = True
            if sunset_date:
                self.versions[version].sunset_date = sunset_date
            logger.info(f"Deprecated API version: {version}")

    def remove_version(self, version: str):
        """Remove a version (for cleanup)"""
        if version in self.versions:
            del self.versions[version]
            if version in self.version_routes:
                del self.version_routes[version]
            logger.info(f"Removed API version: {version}")


# Global version manager instance
version_manager = APIVersionManager()

# Initialize with default versions
v1 = APIVersion("v1", "2024-01-01")
version_manager.register_version(v1)
version_manager.default_version = "v1"


def versioned_route(version: str, path: Optional[str] = None):
    """Decorator to register a route for a specific API version"""
    def decorator(func: Callable) -> Callable:
        route_path = path or f"/{version}{func.__name__.replace('_', '-')}"
        version_manager.add_versioned_route(version, route_path, func)
        return func
    return decorator


def get_api_version(request: Request) -> str:
    """Get API version from request"""
    return version_manager.get_version_from_request(request)


def require_version(version: str):
    """Decorator to require a specific API version"""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            if request:
                request_version = version_manager.get_version_from_request(request)
                if request_version != version:
                    raise HTTPException(
                        status_code=400,
                        detail=f"This endpoint requires API version {version}"
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def version_compatibility_check(request: Request):
    """Middleware to check API version compatibility"""
    version = version_manager.get_version_from_request(request)

    if not version_manager.is_version_supported(version):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Unsupported API version",
                "supported_versions": version_manager.supported_versions,
                "requested_version": version
            }
        )

    version_info = version_manager.get_version_info(version)
    if version_info and version_info.get("deprecated"):
        # Add deprecation warning header
        response = JSONResponse(
            status_code=200,
            content={"warning": f"API version {version} is deprecated"}
        )
        response.headers["X-API-Deprecated"] = "true"
        if version_info.get("sunset_date"):
            response.headers["X-API-Sunset"] = version_info["sunset_date"]
        return response

    return None


# Version negotiation utilities
def negotiate_version(request: Request, supported_versions: List[str]) -> str:
    """Negotiate the best API version based on client preferences"""
    client_version = version_manager.get_version_from_request(request)

    if client_version in supported_versions:
        return client_version

    # Return the latest supported version as fallback
    return supported_versions[-1] if supported_versions else "v1"


def create_versioned_response(data: Any, version: str, request: Request) -> Dict[str, Any]:
    """Create a versioned response with appropriate metadata"""
    response = {
        "data": data,
        "api_version": version,
        "timestamp": request.state.start_time if hasattr(request.state, 'start_time') else None
    }

    # Add version-specific metadata
    if version == "v1":
        response["format"] = "standard"
    elif version == "v2":
        response["format"] = "enhanced"
        response["metadata"] = {
            "pagination": "cursor-based",
            "filtering": "advanced"
        }

    return response


# Version migration helpers
def migrate_request_data(data: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
    """Migrate request data between versions"""
    migrations = {
        ("v1", "v2"): lambda d: {k: v for k, v in d.items()},  # No changes for now
        ("v2", "v1"): lambda d: {k: v for k, v in d.items()},  # No changes for now
    }

    migration_key = (from_version, to_version)
    if migration_key in migrations:
        return migrations[migration_key](data)

    return data


def migrate_response_data(data: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
    """Migrate response data between versions"""
    migrations = {
        ("v1", "v2"): lambda d: {**d, "version": "v2"},
        ("v2", "v1"): lambda d: {k: v for k, v in d.items() if k != "version"},
    }

    migration_key = (from_version, to_version)
    if migration_key in migrations:
        return migrations[migration_key](data)

    return data


# Version documentation helpers
def generate_version_docs(version: str) -> Dict[str, Any]:
    """Generate documentation for a specific API version"""
    version_info = version_manager.get_version_info(version)
    if not version_info:
        return {}

    routes = version_manager.version_routes.get(version, {})

    return {
        "version": version_info,
        "routes": list(routes.keys()),
        "endpoints": {
            path: {
                "path": path,
                "methods": ["GET", "POST", "PUT", "DELETE"],  # Simplified
                "description": f"Endpoint for {path}"
            }
            for path in routes.keys()
        }
    }


# Version health check
async def version_health_check() -> Dict[str, Any]:
    """Health check for API versioning system"""
    return {
        "status": "healthy",
        "versions": {
            "registered": list(version_manager.versions.keys()),
            "default": version_manager.default_version,
            "supported": version_manager.supported_versions
        },
        "routes": {
            version: len(routes)
            for version, routes in version_manager.version_routes.items()
        }
    }