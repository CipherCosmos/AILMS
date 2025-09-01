"""
Analytics Service Configuration
"""
from pydantic_settings import BaseSettings
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

class AnalyticsServiceSettings(BaseSettings):
    """Analytics service specific configuration"""

    # Service settings
    service_name: str = "analytics-service"
    service_version: str = "1.0.0"

    # Data retention settings
    course_analytics_retention_days: int = 365
    student_analytics_retention_days: int = 730
    performance_data_retention_days: int = 1095
    real_time_data_retention_hours: int = 24

    # Aggregation settings
    aggregation_batch_size: int = 1000
    real_time_aggregation_interval: int = 300  # 5 minutes
    historical_aggregation_interval: int = 3600  # 1 hour

    # Performance thresholds
    high_performance_threshold: float = 85.0
    medium_performance_threshold: float = 70.0
    low_performance_threshold: float = 50.0

    # Cache settings
    analytics_cache_ttl: int = 1800  # 30 minutes
    dashboard_cache_ttl: int = 900  # 15 minutes
    report_cache_ttl: int = 3600  # 1 hour

    # Rate limiting
    analytics_request_rate_limit: int = 100  # per minute
    report_generation_rate_limit: int = 20  # per hour per user
    dashboard_access_rate_limit: int = 200  # per minute

    # Data processing
    enable_real_time_analytics: bool = True
    enable_predictive_analytics: bool = True
    enable_anomaly_detection: bool = True
    max_concurrent_analytics_jobs: int = 10

    # Export settings
    max_export_rows: int = 10000
    supported_export_formats: list = ["csv", "json", "pdf", "xlsx"]
    export_timeout_seconds: int = 300

    # Privacy settings
    enable_data_anonymization: bool = True
    enable_pii_masking: bool = True
    data_sharing_consent_required: bool = True

    # AI integration settings
    enable_ai_insights: bool = True
    ai_model_update_interval: int = 86400  # 24 hours
    predictive_model_accuracy_threshold: float = 0.8

    # Monitoring settings
    enable_performance_monitoring: bool = True
    alert_threshold_response_time: float = 5.0  # seconds
    alert_threshold_error_rate: float = 0.05  # 5%

    # Database optimization
    enable_query_optimization: bool = True
    enable_index_auto_creation: bool = True
    max_query_execution_time: int = 30  # seconds

    class Config:
        env_file = str(Path(__file__).parent.parent.parent.parent / '.env')
        env_file_encoding = "utf-8"
        env_prefix = "ANALYTICS_SERVICE_"

# Create settings instance
analytics_service_settings = AnalyticsServiceSettings()