from pydantic_settings import BaseSettings
from pathlib import Path
import os

class Settings(BaseSettings):
    # Environment
    root_dir: Path = Path(__file__).parent

    # MongoDB
    mongo_url: str
    db_name: str

    # Security
    jwt_secret: str = "dev-secret-change"
    access_expire_min: int = 30
    refresh_expire_days: int = 14

    # AI
    gemini_api_key: str = "AIzaSyDOAZMJqH9IMeU-hTEMl6Y8BbJYY4Sa9Yo"
    default_llm_model: str = "gemini-1.5-flash"

    # CORS
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Load dotenv
from dotenv import load_dotenv
load_dotenv(settings.root_dir / '.env')

# Override settings with env if available
settings.mongo_url = os.environ.get("MONGO_URL", settings.mongo_url)
settings.db_name = os.environ.get("DB_NAME", settings.db_name)
settings.jwt_secret = os.environ.get("JWT_SECRET", settings.jwt_secret)
settings.access_expire_min = int(os.environ.get("ACCESS_EXPIRE_MIN", settings.access_expire_min))
settings.refresh_expire_days = int(os.environ.get("REFRESH_EXPIRE_DAYS", settings.refresh_expire_days))
settings.gemini_api_key = os.environ.get("GEMINI_API_KEY", settings.gemini_api_key)
settings.default_llm_model = os.environ.get("DEFAULT_LLM_MODEL", settings.default_llm_model)
settings.cors_origins = os.environ.get("CORS_ORIGINS", settings.cors_origins)