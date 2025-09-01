"""
AI Service - FastAPI Application Factory
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.database import get_database, close_connection
from shared.common.cache import close_connection as close_cache
# Temporarily disabled middleware imports due to FastAPI version compatibility issues
# from shared.common.middleware import (
#     create_cors_middleware,
#     RequestLoggingMiddleware,
#     RateLimitMiddleware
# )

from routes.generation import router as generation_router
from routes.enhancement import router as enhancement_router
from routes.analysis import router as analysis_router
from routes.personalization import router as personalization_router
from routes.health import router as health_router

# Initialize logger
logger = get_logger("ai-service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting AI Service", extra={
        "environment": settings.environment,
        "ai_model": settings.default_llm_model,
        "database": settings.db_name
    })

    # Test database connection
    try:
        db = await get_database()
        await db.command('ping')
        logger.info("Database connection established")
    except Exception as e:
        logger.error("Database connection failed", extra={"error": str(e)})
        raise

    # Test AI model availability
    try:
        # Import AI module to test configuration
        import google.generativeai as genai
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            logger.info("AI model configured successfully")
        else:
            logger.warning("AI API key not configured")
    except Exception as e:
        logger.warning("AI model configuration failed", extra={"error": str(e)})

    yield

    # Shutdown
    logger.info("Shutting down AI Service")
    await close_connection()
    await close_cache()

def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="LMS AI Service",
        description="AI-powered content generation and learning analytics service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Temporarily disabled middleware due to import issues
    # app.add_middleware(create_cors_middleware())
    # app.add_middleware(RequestLoggingMiddleware)

    # Add rate limiting in production (strict for AI operations)
    # if settings.environment == "production":
    #     app.add_middleware(RateLimitMiddleware, requests_per_minute=100)

    # Include routers
    app.include_router(generation_router, prefix="/ai", tags=["Content Generation"])
    app.include_router(enhancement_router, prefix="/ai", tags=["Content Enhancement"])
    app.include_router(analysis_router, prefix="/ai", tags=["Performance Analysis"])
    app.include_router(personalization_router, prefix="/ai", tags=["Learning Personalization"])
    app.include_router(health_router, prefix="", tags=["Health"])

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with service information"""
        return {
            "service": "AI Service",
            "version": "1.0.0",
            "status": "running",
            "ai_model": settings.default_llm_model,
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "generate_course": "/ai/generate-course",
                "enhance_content": "/ai/enhance-content",
                "generate_quiz": "/ai/generate-quiz",
                "analyze_performance": "/ai/analyze-performance",
                "personalize_learning": "/ai/personalize-learning"
            }
        }

    return app

# Create application instance
app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8004,
        reload=settings.environment == "development",
        log_level="info"
    )