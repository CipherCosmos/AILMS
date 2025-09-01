"""
File Service Configuration
"""
from pydantic_settings import BaseSettings
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

class FileServiceSettings(BaseSettings):
    """File service specific configuration"""

    # Service settings
    service_name: str = "file-service"
    service_version: str = "1.0.0"

    # Storage settings
    storage_backend: str = "local"  # local, s3, azure, gcs
    upload_directory: str = "./uploads"
    temp_directory: str = "./temp"
    max_file_size_mb: int = 100
    max_files_per_user: int = 1000
    max_total_storage_mb: int = 5000

    # File type restrictions
    allowed_extensions: list = [
        # Documents
        ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt",
        # Spreadsheets
        ".xls", ".xlsx", ".csv", ".ods",
        # Presentations
        ".ppt", ".pptx", ".odp",
        # Images
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg",
        # Videos
        ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv",
        # Audio
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma",
        # Archives
        ".zip", ".rar", ".7z", ".tar", ".gz",
        # Code files
        ".py", ".js", ".html", ".css", ".json", ".xml", ".yaml", ".yml"
    ]

    # MIME type validation
    allowed_mime_types: list = [
        "application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain", "text/csv", "application/json", "application/xml",
        "image/jpeg", "image/png", "image/gif", "image/bmp", "image/tiff", "image/webp", "image/svg+xml",
        "video/mp4", "audio/mpeg", "audio/wav",
        "application/zip", "application/x-rar-compressed"
    ]

    # Security settings
    enable_virus_scanning: bool = True
    enable_content_filtering: bool = True
    quarantine_suspicious_files: bool = True
    max_filename_length: int = 255

    # Performance settings
    chunk_size_mb: int = 8
    max_concurrent_uploads: int = 5
    upload_timeout_seconds: int = 300
    download_timeout_seconds: int = 60

    # Caching settings
    enable_file_caching: bool = True
    cache_ttl_seconds: int = 3600
    max_cache_size_mb: int = 1000

    # CDN settings
    enable_cdn: bool = False
    cdn_url: str = ""
    cdn_api_key: str = ""

    # Rate limiting
    upload_rate_limit_per_minute: int = 10
    download_rate_limit_per_minute: int = 50
    api_rate_limit_per_minute: int = 100

    # Retention policies
    temp_file_cleanup_hours: int = 24
    deleted_file_cleanup_days: int = 30
    version_history_retention_days: int = 365

    # Thumbnail settings
    enable_thumbnails: bool = True
    thumbnail_sizes: list = ["100x100", "200x200", "400x400"]
    thumbnail_format: str = "jpeg"
    thumbnail_quality: int = 85

    # Backup settings
    enable_backups: bool = True
    backup_frequency_hours: int = 24
    backup_retention_days: int = 30
    backup_storage_path: str = "./backups"

    # Monitoring settings
    enable_performance_monitoring: bool = True
    alert_threshold_upload_time: float = 30.0  # seconds
    alert_threshold_download_time: float = 10.0  # seconds
    alert_threshold_storage_usage: float = 0.9  # 90%

    # Encryption settings
    enable_file_encryption: bool = True
    encryption_algorithm: str = "AES256"
    encryption_key_rotation_days: int = 90

    # Sharing settings
    enable_file_sharing: bool = True
    max_shared_links_per_file: int = 10
    shared_link_expiry_days: int = 7
    enable_password_protected_shares: bool = True

    # Analytics settings
    enable_file_analytics: bool = True
    track_download_stats: bool = True
    track_upload_stats: bool = True
    analytics_retention_days: int = 365

    class Config:
        env_file = str(Path(__file__).parent.parent.parent.parent / '.env')
        env_file_encoding = "utf-8"
        env_prefix = "FILE_SERVICE_"

# Create settings instance
file_service_settings = FileServiceSettings()