"""
Auth Service Pydantic Models
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
# Import validation functions (will be implemented)
def validate_password_strength(password: str) -> dict:
    """Validate password strength"""
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    return {"valid": len(errors) == 0, "errors": errors}

def sanitize_string(text: str) -> str:
    """Sanitize string input"""
    return text.strip()
from .config import auth_settings


class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    name: str
    role: str = Field(
        default="student",
        pattern=r"^(super_admin|org_admin|dept_admin|instructor|teaching_assistant|content_author|student|auditor|parent_guardian|proctor|support_moderator|career_coach|marketplace_manager|industry_reviewer|alumni)$"
    )

    @validator('name')
    def validate_name(cls, v):
        """Validate and sanitize name"""
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return sanitize_string(v.strip())

    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        return v.lower().strip()


class UserCreate(UserBase):
    """User creation model"""
    password: str

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        validation_result = validate_password_strength(v)
        if not validation_result['valid']:
            raise ValueError(f"Password requirements not met: {', '.join(validation_result['errors'])}")
        return v


class UserUpdate(BaseModel):
    """User update model"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None

    @validator('name')
    def validate_name(cls, v):
        """Validate and sanitize name"""
        if v is not None:
            if len(v.strip()) < 2:
                raise ValueError('Name must be at least 2 characters long')
            return sanitize_string(v.strip())
        return v

    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        if v is not None:
            return v.lower().strip()
        return v

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if v is not None:
            validation_result = validate_password_strength(v)
            if not validation_result['valid']:
                raise ValueError(f"Password requirements not met: {', '.join(validation_result['errors'])}")
        return v

    @validator('role')
    def validate_role(cls, v):
        """Validate role"""
        if v is not None:
            valid_roles = [
                "super_admin", "org_admin", "dept_admin", "instructor",
                "teaching_assistant", "content_author", "student", "auditor",
                "parent_guardian", "proctor", "support_moderator",
                "career_coach", "marketplace_manager", "industry_reviewer", "alumni"
            ]
            if v not in valid_roles:
                raise ValueError(f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        return v


class UserPublic(BaseModel):
    """Public user information"""
    id: str
    email: EmailStr
    name: str
    role: str


class UserPrivate(UserPublic):
    """Private user information (for authenticated users)"""
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    login_attempts: int = 0
    locked_until: Optional[datetime] = None


class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str

    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        return v.lower().strip()


class TokenPair(BaseModel):
    """JWT token pair"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = auth_settings.jwt_access_token_expire_minutes * 60


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr

    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        return v.lower().strip()


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str

    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength"""
        validation_result = validate_password_strength(v)
        if not validation_result['valid']:
            raise ValueError(f"Password requirements not met: {', '.join(validation_result['errors'])}")
        return v


class UserSession(BaseModel):
    """User session model"""
    id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    is_active: bool = True


class AuditLog(BaseModel):
    """Audit log entry"""
    id: str
    event_type: str
    user_id: Optional[str] = None
    timestamp: datetime
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class LoginAttempt(BaseModel):
    """Login attempt tracking"""
    email: str
    success: bool
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    failure_reason: Optional[str] = None


class AccountLockInfo(BaseModel):
    """Account lock information"""
    is_locked: bool
    attempts_remaining: int
    locked_until: Optional[datetime] = None
    can_retry_at: Optional[datetime] = None


class AuthMetrics(BaseModel):
    """Authentication metrics"""
    total_users: int
    active_users_today: int
    login_attempts_today: int
    failed_login_attempts_today: int
    locked_accounts: int
    password_resets_today: int
    average_session_duration: float


class SecuritySettings(BaseModel):
    """Security settings for user"""
    two_factor_enabled: bool = False
    password_last_changed: Optional[datetime] = None
    login_notifications_enabled: bool = True
    suspicious_activity_alerts: bool = True
    allowed_ips: List[str] = []
    blocked_ips: List[str] = []


class UserPreferences(BaseModel):
    """User preferences"""
    theme: str = "light"
    language: str = "en"
    timezone: str = "UTC"
    email_notifications: bool = True
    push_notifications: bool = False
    weekly_digest: bool = True


# Response models
class AuthResponse(BaseModel):
    """Generic auth response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LoginResponse(BaseModel):
    """Login response"""
    success: bool
    message: str
    data: Optional[TokenPair] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UserListResponse(BaseModel):
    """User list response"""
    users: List[UserPublic]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = {}


class MetricsResponse(BaseModel):
    """Metrics response"""
    metrics: AuthMetrics
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Error models
class AuthError(BaseModel):
    """Authentication error"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationError(AuthError):
    """Validation error"""
    field: str
    value: Optional[str] = None


class RateLimitError(AuthError):
    """Rate limit error"""
    retry_after: int
    limit: int
    remaining: int