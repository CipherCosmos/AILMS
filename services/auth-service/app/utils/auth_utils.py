"""
Authentication utility functions
"""
import re
import secrets
import string
from typing import Optional, Tuple
from passlib.hash import bcrypt
from shared.common.logging import get_logger

logger = get_logger("auth-utils")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.verify(password, hashed)
    except Exception as e:
        logger.warning("Password verification failed", extra={"error": str(e)})
        return False


def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def validate_email_format(email: str) -> bool:
    """Validate email format using regex"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_user_input(text: str, max_length: int = 255) -> str:
    """Sanitize user input by trimming and limiting length"""
    if not text:
        return ""

    # Trim whitespace
    sanitized = text.strip()

    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>]', '', sanitized)

    return sanitized


def get_client_info(user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> dict:
    """Extract client information from headers"""
    info = {}

    if user_agent:
        info['user_agent'] = sanitize_user_input(user_agent, 500)

        # Extract browser info
        if 'Chrome' in user_agent:
            info['browser'] = 'Chrome'
        elif 'Firefox' in user_agent:
            info['browser'] = 'Firefox'
        elif 'Safari' in user_agent:
            info['browser'] = 'Safari'
        elif 'Edge' in user_agent:
            info['browser'] = 'Edge'
        else:
            info['browser'] = 'Unknown'

        # Extract OS info
        if 'Windows' in user_agent:
            info['os'] = 'Windows'
        elif 'Mac' in user_agent:
            info['os'] = 'macOS'
        elif 'Linux' in user_agent:
            info['os'] = 'Linux'
        elif 'Android' in user_agent:
            info['os'] = 'Android'
        elif 'iOS' in user_agent:
            info['os'] = 'iOS'
        else:
            info['os'] = 'Unknown'

    if ip_address:
        info['ip_address'] = ip_address

    return info


def validate_password_strength(password: str) -> Tuple[bool, list]:
    """
    Validate password strength requirements
    Returns (is_valid, error_messages)
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")

    # Optional: require special characters
    # if not any(c in string.punctuation for c in password):
    #     errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors


def generate_password_reset_token() -> str:
    """Generate a secure password reset token"""
    return generate_secure_token(64)


def generate_email_verification_token() -> str:
    """Generate a secure email verification token"""
    return generate_secure_token(64)


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive data like emails or tokens for logging"""
    if not data or len(data) <= visible_chars:
        return data

    masked_length = len(data) - visible_chars
    mask = '*' * masked_length
    return data[:visible_chars] + mask


def is_valid_role(role: str) -> bool:
    """Validate if a role is valid"""
    valid_roles = [
        "super_admin", "org_admin", "dept_admin", "instructor",
        "teaching_assistant", "content_author", "student", "auditor",
        "parent_guardian", "proctor", "support_moderator",
        "career_coach", "marketplace_manager", "industry_reviewer", "alumni"
    ]
    return role in valid_roles


def get_role_permissions(role: str) -> list:
    """Get permissions for a specific role"""
    # This would be more sophisticated in a real implementation
    # For now, return basic permission sets
    role_permissions = {
        "super_admin": ["*"],  # All permissions
        "org_admin": ["manage_users", "manage_courses", "view_analytics"],
        "dept_admin": ["manage_dept_users", "manage_dept_courses"],
        "instructor": ["create_courses", "grade_assignments", "view_students"],
        "student": ["view_courses", "submit_assignments", "view_grades"],
        "auditor": ["view_all", "view_analytics"]
    }

    return role_permissions.get(role, [])


def calculate_password_entropy(password: str) -> float:
    """Calculate password entropy (bits)"""
    if not password:
        return 0.0

    # Count character types
    char_sets = 0
    if any(c.islower() for c in password):
        char_sets += 26
    if any(c.isupper() for c in password):
        char_sets += 26
    if any(c.isdigit() for c in password):
        char_sets += 10
    if any(c in string.punctuation for c in password):
        char_sets += len(string.punctuation)

    if char_sets == 0:
        return 0.0

    # Calculate entropy
    import math
    entropy = len(password) * math.log2(char_sets)

    return round(entropy, 2)


def should_enforce_password_change(user_data: dict) -> bool:
    """Determine if user should be forced to change password"""
    # Check if password is too old (90 days)
    from datetime import datetime, timezone, timedelta

    password_changed = user_data.get("password_changed_at")
    if password_changed:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
        if isinstance(password_changed, datetime) and password_changed < cutoff_date:
            return True

    # Check if password is weak (low entropy)
    password_hash = user_data.get("password_hash", "")
    if password_hash:
        # This is a simplified check - in reality you'd need the plain password
        # For now, just check if it's an old hash format
        return False

    return False