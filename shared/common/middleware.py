"""
Common middleware for LMS microservices
"""
from starlette.middleware.cors import CORSMiddleware

from shared.config.config import settings

def create_cors_middleware():
    """Create CORS middleware with proper configuration"""
    return CORSMiddleware(
        allow_origins=["*"],  # Simplified for now
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        max_age=86400,
    )

# Placeholder middleware classes for compatibility
class RequestLoggingMiddleware:
    """Placeholder middleware class"""
    pass

class RateLimitMiddleware:
    """Placeholder middleware class"""
    pass

# Common middleware stack
def get_common_middleware():
    """Get list of common middleware for services"""
    return [create_cors_middleware()]