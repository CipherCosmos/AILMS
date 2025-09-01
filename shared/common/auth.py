"""
Shared authentication utilities for LMS microservices
"""
import jwt
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from shared.config.config import settings
from shared.database.database import get_database

# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)

class AuthService:
    """Centralized authentication service"""

    @staticmethod
    async def validate_jwt_token(token: str) -> Dict[str, Any]:
        """Validate JWT token and return user info"""
        try:
            # Decode and validate JWT token
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

            # Verify token hasn't expired
            if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
                raise HTTPException(401, "Token has expired")

            # Get user from database to ensure they still exist
            db = get_database()
            user = await db.users.find_one({"_id": payload.get("sub")})
            if not user:
                raise HTTPException(401, "User not found")

            return {
                "id": user["_id"],
                "role": user.get("role", "student"),
                "email": user.get("email", ""),
                "name": user.get("name", "")
            }

        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")
        except Exception as e:
            raise HTTPException(401, f"Authentication failed: {str(e)}")

    @staticmethod
    def require_role(user: Dict[str, Any], allowed_roles: list[str]):
        """Check if user has required role"""
        if user.get("role") not in allowed_roles:
            raise HTTPException(403, f"Insufficient permissions. Required: {allowed_roles}")

    @staticmethod
    def require_admin(user: Dict[str, Any]):
        """Check if user is admin"""
        AuthService.require_role(user, ["admin", "super_admin"])

    @staticmethod
    def require_instructor(user: Dict[str, Any]):
        """Check if user is instructor or admin"""
        AuthService.require_role(user, ["admin", "super_admin", "instructor", "teaching_assistant"])

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    """FastAPI dependency for getting current authenticated user"""
    if not credentials:
        raise HTTPException(401, "Authentication credentials not provided")

    return await AuthService.validate_jwt_token(credentials.credentials)

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """FastAPI dependency for optional user authentication"""
    if not credentials:
        return None

    try:
        return await AuthService.validate_jwt_token(credentials.credentials)
    except HTTPException:
        return None

# Convenience functions for common role checks
def require_admin(user: Dict[str, Any] = Depends(get_current_user)):
    """Dependency for admin-only endpoints"""
    return AuthService.require_admin(user)

def require_instructor(user: Dict[str, Any] = Depends(get_current_user)):
    """Dependency for instructor-only endpoints"""
    return AuthService.require_instructor(user)

def require_student(user: Dict[str, Any] = Depends(get_current_user)):
    """Dependency for student+ endpoints"""
    AuthService.require_role(user, ["student", "admin", "super_admin", "instructor", "teaching_assistant"])
    return user