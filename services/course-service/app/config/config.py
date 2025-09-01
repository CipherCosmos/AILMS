"""
Course Service Configuration
"""
from pydantic_settings import BaseSettings
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

class CourseServiceSettings(BaseSettings):
    """Course service specific configuration"""

    # Service settings
    service_name: str = "course-service"
    service_version: str = "1.0.0"

    # Course settings
    max_courses_per_instructor: int = 50
    max_enrollments_per_course: int = 1000
    max_lessons_per_course: int = 100
    max_quiz_questions_per_course: int = 50

    # Content settings
    max_course_title_length: int = 200
    max_course_description_length: int = 2000
    max_lesson_title_length: int = 150
    max_lesson_content_length: int = 50000  # 50KB

    # Cache settings
    course_cache_ttl: int = 300  # 5 minutes
    lesson_cache_ttl: int = 600  # 10 minutes
    enrollment_cache_ttl: int = 1800  # 30 minutes

    # Rate limiting
    course_creation_rate_limit: int = 5  # per hour per instructor
    course_update_rate_limit: int = 20  # per hour per instructor
    enrollment_rate_limit: int = 10  # per hour per user

    # Data retention
    course_data_retention_days: int = 365 * 5  # 5 years
    enrollment_history_retention_days: int = 365 * 2  # 2 years
    course_analytics_retention_days: int = 365  # 1 year

    # AI integration settings
    enable_ai_course_generation: bool = True
    ai_course_generation_temperature: float = 0.7
    max_ai_generated_courses_per_day: int = 10

    # Notification settings
    enable_course_publish_notifications: bool = True
    enable_enrollment_notifications: bool = True
    enable_course_update_notifications: bool = True

    # Security settings
    require_course_approval: bool = False
    allow_guest_course_viewing: bool = True
    enable_course_content_moderation: bool = True

    class Config:
        env_file = str(Path(__file__).parent.parent.parent.parent / '.env')
        env_file_encoding = "utf-8"
        env_prefix = "COURSE_SERVICE_"

# Create settings instance
course_service_settings = CourseServiceSettings()