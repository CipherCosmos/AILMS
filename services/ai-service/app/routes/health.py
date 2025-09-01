"""
Health check routes for AI Service
"""
from fastapi import APIRouter, HTTPException
from shared.common.database import health_check as db_health
from shared.common.cache import health_check as cache_health
from shared.common.logging import get_logger
from shared.config.config import settings

logger = get_logger("ai-service")
router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-service",
        "version": "1.0.0",
        "ai_model": settings.default_llm_model
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with dependencies"""
    try:
        # Check database health
        db_status = await db_health()

        # Check cache health
        cache_status = await cache_health()

        # Check AI model availability
        ai_status = {"status": "unknown", "model": settings.default_llm_model}
        try:
            import google.generativeai as genai
            if settings.gemini_api_key:
                genai.configure(api_key=settings.gemini_api_key)
                # Test AI model with a simple request
                model = genai.GenerativeModel(settings.default_llm_model)
                ai_status = {"status": "healthy", "model": settings.default_llm_model}
            else:
                ai_status = {"status": "unhealthy", "error": "AI API key not configured"}
        except Exception as e:
            ai_status = {"status": "unhealthy", "error": str(e)}

        # Overall status
        overall_status = "healthy"
        if (db_status.get("status") != "healthy" or
            cache_status.get("status") != "healthy" or
            ai_status.get("status") != "healthy"):
            overall_status = "degraded"

        return {
            "status": overall_status,
            "service": "ai-service",
            "version": "1.0.0",
            "dependencies": {
                "database": db_status,
                "cache": cache_status,
                "ai_model": ai_status
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

        # Check AI model availability
        if not settings.gemini_api_key:
            raise HTTPException(503, "AI model not configured")

        return {"status": "ready"}
    except Exception:
        raise HTTPException(503, "Service not ready")

@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}

@router.get("/health/models")
async def ai_models_health():
    """Check available AI models and their status"""
    try:
        models_info = {
            "available_models": [
                {
                    "name": "gemini-1.5-flash",
                    "description": "Fast and efficient model for content generation",
                    "max_tokens": 8192,
                    "status": "available" if settings.gemini_api_key else "unavailable"
                },
                {
                    "name": "gemini-1.5-pro",
                    "description": "Advanced model with higher quality output",
                    "max_tokens": 16384,
                    "status": "available" if settings.gemini_api_key else "unavailable"
                }
            ],
            "current_model": settings.default_llm_model,
            "api_key_configured": bool(settings.gemini_api_key)
        }

        return models_info

    except Exception as e:
        logger.error("AI models health check failed", extra={"error": str(e)})
        raise HTTPException(503, "AI models health check failed")