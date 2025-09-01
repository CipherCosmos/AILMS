"""
Auth Service Configuration
"""
import os
from shared.config.config import settings as global_settings


class AuthServiceSettings:
    """Auth service specific settings"""

    def __init__(self):
        # JWT Configuration
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_EXPIRE_MIN", "30"))
        self.jwt_refresh_token_expire_days: int = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "14"))

        # Password settings
        self.password_min_length: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
        self.password_require_uppercase: bool = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower() == "true"
        self.password_require_lowercase: bool = os.getenv("PASSWORD_REQUIRE_LOWERCASE", "true").lower() == "true"
        self.password_require_digits: bool = os.getenv("PASSWORD_REQUIRE_DIGITS", "true").lower() == "true"
        self.password_require_special: bool = os.getenv("PASSWORD_REQUIRE_SPECIAL", "false").lower() == "true"

        # Security settings
        self.max_login_attempts: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.lockout_duration_minutes: int = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))
        self.enable_account_lockout: bool = os.getenv("ENABLE_ACCOUNT_LOCKOUT", "true").lower() == "true"

        # Session settings
        self.session_timeout_minutes: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "480"))  # 8 hours
        self.enable_session_tracking: bool = os.getenv("ENABLE_SESSION_TRACKING", "true").lower() == "true"

        # Rate limiting (auth-specific)
        self.auth_rate_limit_per_minute: int = int(os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "10"))
        self.token_refresh_rate_limit_per_hour: int = int(os.getenv("TOKEN_REFRESH_RATE_LIMIT_PER_HOUR", "20"))

        # Email settings (for future use)
        self.enable_email_verification: bool = os.getenv("ENABLE_EMAIL_VERIFICATION", "false").lower() == "true"
        self.email_verification_token_expire_hours: int = int(os.getenv("EMAIL_VERIFICATION_EXPIRE_HOURS", "24"))

        # OAuth settings (for future use)
        self.enable_oauth: bool = os.getenv("ENABLE_OAUTH", "false").lower() == "true"
        self.oauth_providers: list = os.getenv("OAUTH_PROVIDERS", "").split(",") if os.getenv("OAUTH_PROVIDERS") else []

        # Audit settings
        self.enable_audit_logging: bool = os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true"
        self.audit_log_retention_days: int = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))


# Create settings instance
auth_settings = AuthServiceSettings()

# Export commonly used settings
JWT_ALGORITHM = auth_settings.jwt_algorithm
JWT_ACCESS_EXPIRE_MINUTES = auth_settings.jwt_access_token_expire_minutes
JWT_REFRESH_EXPIRE_DAYS = auth_settings.jwt_refresh_token_expire_days
PASSWORD_MIN_LENGTH = auth_settings.password_min_length
MAX_LOGIN_ATTEMPTS = auth_settings.max_login_attempts
LOCKOUT_DURATION_MINUTES = auth_settings.lockout_duration_minutes