"""
User Service Configuration
"""
from pydantic_settings import BaseSettings
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

class UserServiceSettings(BaseSettings):
    """User service specific configuration"""

    # Service settings
    service_name: str = "user-service"
    service_version: str = "1.0.0"

    # Learning analytics settings
    max_study_sessions_per_day: int = 10
    max_achievements_per_user: int = 100
    skill_gap_analysis_depth: int = 5
    career_readiness_threshold: float = 75.0

    # Cache settings
    profile_cache_ttl: int = 300  # 5 minutes
    analytics_cache_ttl: int = 600  # 10 minutes
    study_plan_cache_ttl: int = 1800  # 30 minutes

    # Rate limiting
    profile_update_rate_limit: int = 10  # per minute
    analytics_request_rate_limit: int = 30  # per minute

    # Data retention
    study_session_retention_days: int = 365
    analytics_data_retention_days: int = 730
    achievement_history_retention_days: int = 1095

    # AI integration settings
    enable_ai_recommendations: bool = True
    ai_model_temperature: float = 0.7
    max_recommendations_per_request: int = 5

    # Notification settings
    enable_achievement_notifications: bool = True
    enable_progress_notifications: bool = True
    enable_career_milestone_notifications: bool = True

    # Security settings
    max_profile_image_size: int = 5 * 1024 * 1024  # 5MB
    allowed_image_types: list = ["image/jpeg", "image/png", "image/webp"]
    sensitive_data_masking: bool = True

    class Config:
        env_file = str(Path(__file__).parent.parent.parent.parent / '.env')
        env_file_encoding = "utf-8"
        env_prefix = "USER_SERVICE_"

# Create settings instance
user_service_settings = UserServiceSettings()