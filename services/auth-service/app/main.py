"""
Auth Service - FastAPI Application Factory
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.monitoring import metrics_collector

from .config import auth_settings
from .database import auth_db
from .middleware import AuthMiddleware, SecurityHeadersMiddleware, RequestLoggingMiddleware
from .routes.auth import router as auth_router
from .routes.users import router as users_router
from .routes.tokens import router as tokens_router
from .routes.health import router as health_router

logger = get_logger("auth-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Auth Service", extra={
        "environment": settings.environment,
        "version": "1.0.0"
    })

    # Database connection is initialized lazily when needed
    # Metrics are initialized when first used

    yield

    # Shutdown
    logger.info("Shutting down Auth Service")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    # Create FastAPI app
    app = FastAPI(
        title="LMS Auth Service",
        description="Authentication and User Management Service",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on your needs
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuthMiddleware, exclude_paths=[
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/register",
        "/auth/login",
        "/auth/validate",
        "/tokens/validate"
    ])

    # Include routers
    app.include_router(
        auth_router,
        prefix="/auth",
        tags=["Authentication"]
    )

    app.include_router(
        users_router,
        prefix="/users",
        tags=["User Management"]
    )

    app.include_router(
        tokens_router,
        prefix="/tokens",
        tags=["Token Management"]
    )

    app.include_router(
        health_router,
        prefix="/health",
        tags=["Health Checks"]
    )

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with service information"""
        return {
            "service": "auth-service",
            "version": "1.0.0",
            "status": "running",
            "environment": settings.environment,
            "docs": "/docs"
        }

    # Service info endpoint
    @app.get("/info")
    async def service_info():
        """Service information endpoint"""
        return {
            "service": "auth-service",
            "version": "1.0.0",
            "description": "Authentication and User Management Service",
            "endpoints": {
                "auth": "/auth",
                "users": "/users",
                "tokens": "/tokens",
                "health": "/health"
            },
            "features": [
                "JWT Authentication",
                "User Registration",
                "Role-based Access Control",
                "Token Management",
                "Password Security",
                "Account Lockout Protection"
            ]
        }

    logger.info("Auth Service application created successfully")
    return app


# Create the application instance
app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.environment == "development",
        log_level="info"
    )