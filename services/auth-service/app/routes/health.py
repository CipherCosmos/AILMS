"""
Health check routes for Auth Service
"""
from fastapi import APIRouter, HTTPException
from shared.common.database import health_check as db_health, get_database
from shared.common.logging import get_logger
from shared.config.config import settings

logger = get_logger("auth-service")
router = APIRouter()

@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": "1.0.0",
        "jwt_config": {
            "access_token_expiry": f"{settings.access_expire_min} minutes",
            "refresh_token_expiry": f"{settings.refresh_expire_days} days"
        }
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with dependencies"""
    try:
        # Check database health
        db_status = await db_health()

        # Check JWT configuration
        jwt_status = {"status": "healthy", "secret_configured": bool(settings.jwt_secret)}

        # Check bcrypt availability
        try:
            from passlib.hash import bcrypt
            bcrypt_status = {"status": "healthy", "version": "available"}
        except Exception as e:
            bcrypt_status = {"status": "unhealthy", "error": str(e)}

        # Overall status
        overall_status = "healthy"
        if (db_status.get("status") != "healthy" or
            jwt_status.get("status") != "healthy" or
            bcrypt_status.get("status") != "healthy"):
            overall_status = "degraded"

        return {
            "status": overall_status,
            "service": "auth-service",
            "version": "1.0.0",
            "dependencies": {
                "database": db_status,
                "jwt": jwt_status,
                "bcrypt": bcrypt_status
            },
            "configuration": {
                "environment": settings.environment,
                "jwt_secret_configured": bool(settings.jwt_secret),
                "access_token_expiry_min": settings.access_expire_min,
                "refresh_token_expiry_days": settings.refresh_expire_days
            },
            "timestamp": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow()
        }

    except Exception as e:
        logger.error("Detailed health check failed", extra={"error": str(e)})
        raise HTTPException(503, "Health check failed")

@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    try:
        db_status = await db_health()
        if db_status.get("status") != "healthy":
            raise HTTPException(503, "Database not ready")

        if not settings.jwt_secret:
            raise HTTPException(503, "JWT secret not configured")

        return {"status": "ready"}
    except Exception:
        raise HTTPException(503, "Service not ready")

@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}

@router.get("/health/stats")
async def auth_stats():
    """Get authentication service statistics"""
    try:
        # Get database stats
        db = await get_database()
        user_count = await db.users.count_documents({})

        return {
            "service": "auth-service",
            "stats": {
                "total_users": user_count,
                "active_users_last_24h": 0,  # Would need to track this
                "failed_login_attempts": 0,  # Would need to track this
                "tokens_issued_today": 0     # Would need to track this
            },
            "timestamp": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow()
        }

    except Exception as e:
        logger.error("Auth stats retrieval failed", extra={"error": str(e)})
        raise HTTPException(500, "Stats retrieval failed")