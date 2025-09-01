"""
Notification Service Configuration
"""
from pydantic_settings import BaseSettings
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

class NotificationServiceSettings(BaseSettings):
    """Notification service specific configuration"""

    # Service settings
    service_name: str = "notification-service"
    service_version: str = "1.0.0"

    # Notification limits
    max_title_length: int = 200
    max_message_length: int = 1000
    max_notifications_per_user: int = 1000
    max_bulk_notifications: int = 100

    # Delivery settings
    email_batch_size: int = 50
    sms_batch_size: int = 20
    push_batch_size: int = 100

    # Retry settings
    max_delivery_attempts: int = 3
    delivery_retry_delay: int = 300  # seconds

    # Cache settings
    notification_cache_ttl: int = 300  # 5 minutes
    settings_cache_ttl: int = 1800  # 30 minutes

    # Rate limiting
    notifications_per_minute: int = 60
    bulk_notifications_per_hour: int = 1000

    # Email settings
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = "noreply@lms-platform.com"

    # SMS settings
    sms_provider: str = ""
    sms_api_key: str = ""
    sms_sender_id: str = "LMS"

    # Push notification settings
    fcm_server_key: str = ""
    apns_key_id: str = ""
    apns_team_id: str = ""

    # Template settings
    template_cache_enabled: bool = True
    template_cache_ttl: int = 3600  # 1 hour

    # Analytics settings
    enable_delivery_tracking: bool = True
    enable_read_tracking: bool = True
    stats_retention_days: int = 90

    class Config:
        env_file = str(Path(__file__).parent.parent.parent.parent / '.env')
        env_file_encoding = "utf-8"
        env_prefix = "NOTIFICATION_SERVICE_"

# Create settings instance
notification_service_settings = NotificationServiceSettings()