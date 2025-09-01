"""
Assessment Service Configuration
"""
from pydantic_settings import BaseSettings
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

class AssessmentServiceSettings(BaseSettings):
    """Assessment service specific configuration"""

    # Service settings
    service_name: str = "assessment-service"
    service_version: str = "1.0.0"

    # Assessment settings
    max_assignment_title_length: int = 200
    max_assignment_description_length: int = 2000
    max_submission_content_length: int = 10000
    max_file_size_mb: int = 50

    # Grading settings
    auto_grading_enabled: bool = True
    manual_grading_required: bool = False
    grading_deadline_hours: int = 168  # 7 days
    max_grade_value: int = 100
    min_grade_value: int = 0

    # Submission settings
    allow_late_submissions: bool = True
    late_submission_penalty_percent: int = 10
    max_submissions_per_assignment: int = 5
    submission_cooldown_minutes: int = 5

    # Notification settings
    notify_on_submission: bool = True
    notify_on_grading: bool = True
    notify_before_deadline_hours: int = 24

    # Plagiarism settings
    plagiarism_check_enabled: bool = True
    plagiarism_threshold_percent: int = 70
    plagiarism_check_service: str = "internal"

    # Analytics settings
    enable_performance_analytics: bool = True
    analytics_retention_days: int = 365
    performance_cache_ttl: int = 1800

    # Rate limiting
    assignment_creation_rate_limit: int = 20  # per hour per instructor
    submission_rate_limit: int = 10  # per hour per student
    grading_rate_limit: int = 50  # per hour per instructor

    # File handling
    allowed_file_types: list = [".pdf", ".doc", ".docx", ".txt", ".py", ".java", ".cpp", ".js", ".html", ".css"]
    max_files_per_submission: int = 5

    # AI Integration settings
    ai_grading_enabled: bool = True
    ai_feedback_enabled: bool = True
    ai_model_temperature: float = 0.3
    ai_confidence_threshold: float = 0.8

    # Security settings
    enable_content_filtering: bool = True
    max_content_length_filter: int = 50000
    sensitive_data_masking: bool = True

    # Cache settings
    assignment_cache_ttl: int = 3600  # 1 hour
    submission_cache_ttl: int = 1800  # 30 minutes
    grade_cache_ttl: int = 7200  # 2 hours

    class Config:
        env_file = str(Path(__file__).parent.parent.parent.parent / '.env')
        env_file_encoding = "utf-8"
        env_prefix = "ASSESSMENT_SERVICE_"

# Create settings instance
assessment_service_settings = AssessmentServiceSettings()