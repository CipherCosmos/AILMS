from pydantic_settings import BaseSettings
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent / '.env')

class Settings(BaseSettings):
    # Environment
    root_dir: Path = Path(__file__).parent.parent.parent
    environment: str = os.getenv("ENVIRONMENT", "development")

    # MongoDB - SECURE: Use environment variables only
    mongo_url: str = os.getenv("MONGO_URL", "mongodb://localhost:27017/lms_dev")
    mongo_username: str = os.getenv("MONGO_USERNAME", "")
    mongo_password: str = os.getenv("MONGO_PASSWORD", "")
    db_name: str = os.getenv("DB_NAME", "lms_dev")

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Security - NO HARDCODED SECRETS
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    access_expire_min: int = int(os.getenv("ACCESS_EXPIRE_MIN", "30"))
    refresh_expire_days: int = int(os.getenv("REFRESH_EXPIRE_DAYS", "14"))

    # AI - NO HARDCODED API KEYS
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    default_llm_model: str = os.getenv("DEFAULT_LLM_MODEL", "gemini-1.5-flash")

    # CORS
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")

    # Service URLs for inter-service communication
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
    course_service_url: str = os.getenv("COURSE_SERVICE_URL", "http://course-service:8002")
    user_service_url: str = os.getenv("USER_SERVICE_URL", "http://user-service:8003")
    ai_service_url: str = os.getenv("AI_SERVICE_URL", "http://ai-service:8004")
    assessment_service_url: str = os.getenv("ASSESSMENT_SERVICE_URL", "http://assessment-service:8005")
    analytics_service_url: str = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8006")
    notification_service_url: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8007")
    file_service_url: str = os.getenv("FILE_SERVICE_URL", "http://file-service:8008")

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / '.env')
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Validate critical security settings
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET environment variable is required")
        if not self.gemini_api_key and self.environment == "production":
            raise ValueError("GEMINI_API_KEY environment variable is required for production")

# Create settings with proper env var loading
settings = Settings()