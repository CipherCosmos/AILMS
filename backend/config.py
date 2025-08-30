from pydantic_settings import BaseSettings
from pathlib import Path
import os

class Settings(BaseSettings):
    # Environment
    root_dir: Path = Path(__file__).parent

    # MongoDB (with fallback defaults)
    mongo_url: str = "mongodb+srv://collagedsba:shivam977140@cluster0.1l6yrez.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    db_name: str = "test_database"

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

# Load environment variables first
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

# Create settings with proper env var loading
settings = Settings()