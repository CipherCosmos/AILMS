"""
Health check routes for Notification Service
"""
from fastapi import APIRouter, HTTPException
from shared.common.database import health_check as db_health
from shared.common.cache import health_check as cache_health
from shared.common.logging import get_logger

logger = get_logger("notification-service")
router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "notification-service",
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with dependencies"""
    try:
        # Check database health
        db_status = await db_health()

        # Check cache health
        cache_status = await cache_health()

        # Overall status
        overall_status = "healthy"
        if db_status.get("status") != "healthy" or cache_status.get("status") != "healthy":
            overall_status = "degraded"

        return {
            "status": overall_status,
            "service": "notification-service",
            "version": "1.0.0",
            "dependencies": {
                "database": db_status,
                "cache": cache_status
            },
            "timestamp": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow()
        }

    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)})
        raise HTTPException(503, "Service unhealthy")

@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    try:
        db_status = await db_health()
        if db_status.get("status") != "healthy":
            raise HTTPException(503, "Database not ready")

        return {"status": "ready"}
    except Exception:
        raise HTTPException(503, "Service not ready")

@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}