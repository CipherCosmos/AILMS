"""
Course Service Authentication Middleware
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import jwt

from shared.common.logging import get_logger
from shared.common.errors import AuthenticationError
from shared.config.config import settings

logger = get_logger("course-service-middleware")

class AuthMiddleware:
    """Authentication middleware for course service"""

    def __init__(self):
        self.jwt_secret = settings.jwt_secret

    async def authenticate_request(self, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Authenticate request and return user info"""
        if not token:
            return None

        try:
            # Decode and validate JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])

            # Verify token hasn't expired
            if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
                raise AuthenticationError("Token has expired")

            # Return user information
            user = {
                "id": payload.get("sub"),
                "role": payload.get("role", "student"),
                "email": payload.get("email", ""),
                "name": payload.get("name", "")
            }

            if not user["id"]:
                raise AuthenticationError("Invalid token: missing user ID")

            return user

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Authentication middleware error", extra={"error": str(e)})
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    def require_authentication(self, user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Require authentication and return user"""
        if not user:
            raise AuthenticationError("Authentication required")
        return user

    def require_role(self, user: Dict[str, Any], allowed_roles: list[str]) -> None:
        """Check if user has required role"""
        if user.get("role") not in allowed_roles:
            from shared.common.errors import AuthorizationError
            raise AuthorizationError("Insufficient permissions")

    def can_access_course(self, course_data: Dict[str, Any], user: Dict[str, Any]) -> bool:
        """Check if user can access a course"""
        # Public access if published
        if course_data.get("published"):
            return True

        # Owner access
        if course_data.get("owner_id") == user["id"]:
            return True

        # Enrolled user access
        if user["id"] in course_data.get("enrolled_user_ids", []):
            return True

        # Admin access
        if user.get("role") in ["admin", "instructor"]:
            return True

        return False

    def can_modify_course(self, course_data: Dict[str, Any], user: Dict[str, Any]) -> bool:
        """Check if user can modify a course"""
        # Owner can modify
        if course_data.get("owner_id") == user["id"]:
            return True

        # Admin can modify
        if user.get("role") == "admin":
            return True

        # Instructor can modify their own courses
        if user.get("role") == "instructor" and course_data.get("owner_id") == user["id"]:
            return True

        return False

# Global middleware instance
auth_middleware = AuthMiddleware()