"""
AI Service Configuration
"""
from pydantic_settings import BaseSettings
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

class AIServiceSettings(BaseSettings):
    """AI service specific configuration"""

    # Service settings
    service_name: str = "ai-service"
    service_version: str = "1.0.0"

    # AI Model settings
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_model: str = "gpt-4"
    fallback_model: str = "gpt-3.5-turbo"

    # AI Processing settings
    max_tokens_per_request: int = 4000
    max_requests_per_minute: int = 60
    max_concurrent_requests: int = 10
    request_timeout_seconds: int = 30

    # Content Generation settings
    max_course_content_length: int = 10000
    max_quiz_questions: int = 20
    max_lesson_content_length: int = 5000

    # Analysis settings
    max_analysis_input_length: int = 10000
    analysis_cache_ttl: int = 3600  # 1 hour

    # Personalization settings
    max_user_preferences: int = 100
    personalization_cache_ttl: int = 1800  # 30 minutes

    # Enhancement settings
    max_enhancement_input_length: int = 5000
    enhancement_cache_ttl: int = 7200  # 2 hours

    # Rate limiting
    analysis_rate_limit: int = 100  # per hour per user
    generation_rate_limit: int = 50  # per hour per user
    enhancement_rate_limit: int = 30  # per hour per user
    personalization_rate_limit: int = 20  # per hour per user

    # Data retention
    ai_request_logs_retention_days: int = 30
    analysis_results_retention_days: int = 90
    personalization_data_retention_days: int = 365

    # AI Integration settings
    enable_openai: bool = True
    enable_anthropic: bool = False
    enable_caching: bool = True
    enable_request_logging: bool = True

    # Quality settings
    min_confidence_score: float = 0.7
    max_retries: int = 3
    enable_content_filtering: bool = True

    # Cost management
    max_cost_per_request: float = 0.10  # $0.10 per request
    daily_cost_limit: float = 50.0  # $50 per day

    class Config:
        env_file = str(Path(__file__).parent.parent.parent.parent / '.env')
        env_file_encoding = "utf-8"
        env_prefix = "AI_SERVICE_"

# Create settings instance
ai_service_settings = AIServiceSettings()