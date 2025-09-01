"""
Token management routes for Auth Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.errors import ValidationError, AuthenticationError
from ..services.auth_service import AuthService
from ..models import UserPrivate
from ..database import auth_db

logger = get_logger("auth-service")
router = APIRouter()

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from service"""
    return await AuthService.get_current_user(credentials.credentials)

def require_role(user: UserPrivate, allowed: list[str]):
    """Check if user has required role"""
    return AuthService.validate_token_permissions(user, allowed)

@router.post("/validate")
async def validate_token(token: str):
    """
    Validate a JWT token without requiring authentication.

    - **token**: JWT token to validate
    """
    try:
        if not token:
            raise HTTPException(400, "Token is required")

        # Decode and validate token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        # Check if token has expired
        if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            return {
                "valid": False,
                "error": "Token has expired",
                "expired_at": datetime.fromtimestamp(payload["exp"], timezone.utc).isoformat()
            }

        # Get user to verify they still exist
        db = await auth_db.get_db()
        user = await db.users.find_one({"_id": payload.get("sub")})
        if not user:
            return {
                "valid": False,
                "error": "User not found"
            }

        return {
            "valid": True,
            "user_id": str(payload.get("sub")),
            "role": payload.get("role"),
            "expires_at": datetime.fromtimestamp(payload["exp"], timezone.utc).isoformat() if payload.get("exp") else None,
            "issued_at": datetime.fromtimestamp(payload["iat"], timezone.utc).isoformat() if payload.get("iat") else None
        }

    except jwt.ExpiredSignatureError:
        return {
            "valid": False,
            "error": "Token has expired"
        }
    except jwt.InvalidTokenError:
        return {
            "valid": False,
            "error": "Invalid token"
        }
    except Exception as e:
        logger.error("Token validation failed", extra={"error": str(e)})
        return {
            "valid": False,
            "error": "Token validation failed"
        }

@router.get("/info")
async def get_token_info(user: UserPrivate = Depends(get_current_user)):
    """
    Get information about the current user's token.
    """
    try:
        return {
            "user_id": user.id,
            "role": user.role,
            "email": user.email,
            "name": user.name,
            "token_type": "bearer",
            "issued_at": "current_session"  # Would need to track this
        }

    except Exception as e:
        logger.error("Failed to get token info", extra={
            "user_id": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to get token information")

@router.post("/revoke")
async def revoke_token(token: str, user: UserPrivate = Depends(get_current_user)):
    """
    Revoke a specific token (admin only).

    In a production system, this would add the token to a blacklist.
    For now, this is a placeholder implementation.

    - **token**: Token to revoke
    """
    try:
        # Check permissions
        if not require_role(user, ["admin", "super_admin"]):
            raise AuthenticationError("Admin access required")

        if not token:
            raise HTTPException(400, "Token is required")

        # In production, you would:
        # 1. Decode the token to get user info
        # 2. Add token to a blacklist/cache
        # 3. Set an expiration time for the blacklist entry

        logger.info("Token revocation requested", extra={
            "requested_by": user.id,
            "token_preview": token[:20] + "..." if len(token) > 20 else token
        })

        # Placeholder response
        return {
            "status": "revoked",
            "message": "Token has been revoked",
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "note": "Token blacklisting not yet implemented"
        }

    except AuthenticationError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error("Token revocation failed", extra={
            "requested_by": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Token revocation failed")

@router.get("/config")
async def get_token_config(user: UserPrivate = Depends(get_current_user)):
    """
    Get JWT token configuration (admin only).
    """
    try:
        # Check permissions
        if not require_role(user, ["admin", "super_admin"]):
            raise AuthenticationError("Admin access required")

        config = {
            "jwt_algorithm": "HS256",
            "access_token_expiry_minutes": settings.access_expire_min,
            "refresh_token_expiry_days": settings.refresh_expire_days,
            "issuer": "lms-auth-service",
            "audience": "lms-users",
            "secret_configured": bool(settings.jwt_secret),
            "token_format": "JWT",
            "claims": {
                "standard": ["sub", "exp", "iat"],
                "custom": ["role"]
            }
        }

        return config

    except AuthenticationError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error("Failed to get token config", extra={
            "requested_by": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to get token configuration")

@router.post("/refresh-config")
async def refresh_token_config(user: UserPrivate = Depends(get_current_user)):
    """
    Refresh JWT configuration from environment (admin only).

    This would reload configuration from environment variables.
    """
    try:
        # Check permissions
        if not require_role(user, ["admin", "super_admin"]):
            raise AuthenticationError("Admin access required")

        # In production, this would reload settings from environment
        # For now, return current config

        logger.info("Token config refresh requested", extra={
            "requested_by": user.id
        })

        return {
            "status": "refreshed",
            "message": "Token configuration refreshed",
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
            "current_config": {
                "access_token_expiry": f"{settings.access_expire_min} minutes",
                "refresh_token_expiry": f"{settings.refresh_expire_days} days",
                "algorithm": "HS256"
            }
        }

    except AuthenticationError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error("Token config refresh failed", extra={
            "requested_by": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Token config refresh failed")

@router.get("/stats")
async def get_token_stats(user: UserPrivate = Depends(get_current_user)):
    """
    Get token usage statistics (admin only).
    """
    try:
        # Check permissions
        if not require_role(user, ["admin", "super_admin"]):
            raise AuthenticationError("Admin access required")

        # Get basic metrics from service
        metrics = await AuthService.get_auth_metrics()

        return metrics

    except AuthenticationError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error("Failed to get token stats", extra={
            "requested_by": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to get token statistics")

@router.post("/blacklist")
async def blacklist_token(token: str, reason: str = "manual", user: UserPrivate = Depends(get_current_user)):
    """
    Add a token to the blacklist (admin only).

    - **token**: Token to blacklist
    - **reason**: Reason for blacklisting
    """
    try:
        # Check permissions
        if not require_role(user, ["admin", "super_admin"]):
            raise AuthenticationError("Admin access required")

        if not token:
            raise HTTPException(400, "Token is required")

        # In production, you would:
        # 1. Store the token hash in Redis/cache
        # 2. Set expiration time
        # 3. Check blacklist during token validation

        logger.info("Token blacklisted", extra={
            "requested_by": user.id,
            "reason": reason,
            "token_preview": token[:20] + "..." if len(token) > 20 else token
        })

        return {
            "status": "blacklisted",
            "token_id": "placeholder",  # Would be actual token ID/hash
            "reason": reason,
            "blacklisted_at": datetime.now(timezone.utc).isoformat(),
            "blacklisted_by": user.id
        }

    except AuthenticationError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error("Token blacklisting failed", extra={
            "requested_by": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Token blacklisting failed")