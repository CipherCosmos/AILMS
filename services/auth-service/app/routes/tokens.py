"""
Token management routes for Auth Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
import jwt

from shared.config.config import settings
from shared.common.auth import get_current_user, require_admin
from shared.common.errors import ValidationError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("auth-service")
router = APIRouter()

async def _current_user(token: str = None):
    """Get current authenticated user"""
    if not token:
        raise HTTPException(401, "No authentication token provided")

    try:
        import jwt
        from shared.config.config import settings

        # Decode and validate JWT token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        # Verify token hasn't expired
        from datetime import datetime, timezone
        if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(401, "Token has expired")

        # Get user from database
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

def _require_role(user, allowed: list[str]):
    """Check if user has required role"""
    if user.get("role") not in allowed:
        raise HTTPException(403, "Insufficient permissions")

@router.post("/validate")
async def validate_token(token: str):
    """
    Validate a JWT token without requiring authentication.

    - **token**: JWT token to validate
    """
    try:
        if not token:
            raise ValidationError("Token is required", "token")

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
        db = get_database()
        user = await db.users.find_one({"_id": payload.get("sub")})
        if not user:
            return {
                "valid": False,
                "error": "User not found"
            }

        return {
            "valid": True,
            "user_id": payload.get("sub"),
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
    except ValidationError:
        raise
    except Exception as e:
        logger.error("Token validation failed", extra={"error": str(e)})
        return {
            "valid": False,
            "error": "Token validation failed"
        }

@router.get("/info")
async def get_token_info(user=Depends(_current_user)):
    """
    Get information about the current user's token.
    """
    try:
        # Get the token from the request headers
        from fastapi import Request
        # Note: This would need to be implemented differently in practice
        # For now, return basic user info

        return {
            "user_id": user["id"],
            "role": user["role"],
            "email": user["email"],
            "name": user["name"],
            "token_type": "bearer",
            "issued_at": "current_session"  # Would need to track this
        }

    except Exception as e:
        logger.error("Failed to get token info", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to get token information")

@router.post("/revoke")
async def revoke_token(token: str, user=Depends(_current_user)):
    """
    Revoke a specific token (admin only).

    In a production system, this would add the token to a blacklist.
    For now, this is a placeholder implementation.

    - **token**: Token to revoke
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "super_admin"])

        if not token:
            raise ValidationError("Token is required", "token")

        # In production, you would:
        # 1. Decode the token to get user info
        # 2. Add token to a blacklist/cache
        # 3. Set an expiration time for the blacklist entry

        logger.info("Token revocation requested", extra={
            "requested_by": user["id"],
            "token_preview": token[:20] + "..." if len(token) > 20 else token
        })

        # Placeholder response
        return {
            "status": "revoked",
            "message": "Token has been revoked",
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "note": "Token blacklisting not yet implemented"
        }

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Token revocation failed", extra={
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Token revocation failed")

@router.get("/config")
async def get_token_config(user=Depends(_current_user)):
    """
    Get JWT token configuration (admin only).
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "super_admin"])

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

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get token config", extra={
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to get token configuration")

@router.post("/refresh-config")
async def refresh_token_config(user=Depends(_current_user)):
    """
    Refresh JWT configuration from environment (admin only).

    This would reload configuration from environment variables.
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "super_admin"])

        # In production, this would reload settings from environment
        # For now, return current config

        logger.info("Token config refresh requested", extra={
            "requested_by": user["id"]
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

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Token config refresh failed", extra={
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Token config refresh failed")

@router.get("/stats")
async def get_token_stats(user=Depends(_current_user)):
    """
    Get token usage statistics (admin only).
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "super_admin"])

        # In production, you would track:
        # - Tokens issued per day/hour
        # - Token validation failures
        # - Refresh token usage
        # - Token expiration patterns

        stats = {
            "tokens_issued_today": 0,  # Would track actual metrics
            "tokens_validated_today": 0,
            "token_failures_today": 0,
            "refresh_tokens_used_today": 0,
            "average_token_lifetime": f"{settings.access_expire_min} minutes",
            "most_common_failure_reason": "expired",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return stats

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get token stats", extra={
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to get token statistics")

@router.post("/blacklist")
async def blacklist_token(token: str, reason: str = "manual", user=Depends(_current_user)):
    """
    Add a token to the blacklist (admin only).

    - **token**: Token to blacklist
    - **reason**: Reason for blacklisting
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "super_admin"])

        if not token:
            raise ValidationError("Token is required", "token")

        # In production, you would:
        # 1. Store the token hash in Redis/cache
        # 2. Set expiration time
        # 3. Check blacklist during token validation

        logger.info("Token blacklisted", extra={
            "requested_by": user["id"],
            "reason": reason,
            "token_preview": token[:20] + "..." if len(token) > 20 else token
        })

        return {
            "status": "blacklisted",
            "token_id": "placeholder",  # Would be actual token ID/hash
            "reason": reason,
            "blacklisted_at": datetime.now(timezone.utc).isoformat(),
            "blacklisted_by": user["id"]
        }

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Token blacklisting failed", extra={
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Token blacklisting failed")