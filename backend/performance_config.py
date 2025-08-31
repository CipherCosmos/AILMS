"""
Performance optimization configuration for LMS backend.
"""
from pydantic_settings import BaseSettings
from typing import List, Dict, Any
import os

class PerformanceSettings(BaseSettings):
    """Performance optimization settings."""

    # Database connection pooling
    db_connection_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 3600  # 1 hour

    # Caching settings
    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 300  # 5 minutes
    cache_enabled: bool = True

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_enabled: bool = True

    # Database query optimization
    db_query_timeout_seconds: int = 30
    db_read_preference: str = "secondaryPreferred"

    # Async worker settings
    max_concurrent_requests: int = 100
    worker_timeout_seconds: int = 30

    # Response compression
    enable_compression: bool = True
    compression_level: int = 6

    # Connection settings
    keep_alive_timeout: int = 75
    max_keep_alive_requests: int = 100

    class Config:
        env_file = ".env"
        env_prefix = "PERF_"

performance_settings = PerformanceSettings()