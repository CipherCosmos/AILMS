"""
Notification Service Utility Functions
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import re

from shared.common.logging import get_logger

from config.config import notification_service_settings

logger = get_logger("notification-service-utils")

async def get_current_user(token: Optional[str] = None):
    """Get current authenticated user from JWT token"""
    if not token:
        from fastapi import HTTPException
        raise HTTPException(401, "No authentication token provided")

    try:
        import jwt
        from shared.config.config import settings

        # Decode and validate JWT token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        # Verify token hasn't expired
        if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            from fastapi import HTTPException
            raise HTTPException(401, "Token has expired")

        # Get user from database (simplified for now)
        # In production, this would query the auth service or user database
        user = {
            "id": payload.get("sub"),
            "role": payload.get("role", "student"),
            "email": payload.get("email", ""),
            "name": payload.get("name", "")
        }

        if not user["id"]:
            from fastapi import HTTPException
            raise HTTPException(401, "Invalid token: missing user ID")

        return user

    except jwt.ExpiredSignatureError:
        from fastapi import HTTPException
        raise HTTPException(401, "Token has expired")
    except jwt.InvalidTokenError:
        from fastapi import HTTPException
        raise HTTPException(401, "Invalid token")
    except Exception as e:
        logger.error("Authentication failed", extra={"error": str(e)})
        from fastapi import HTTPException
        raise HTTPException(401, f"Authentication failed: {str(e)}")

def require_role(user, allowed: list[str]):
    """Check if user has required role"""
    if user.get("role") not in allowed:
        from fastapi import HTTPException
        raise HTTPException(403, "Insufficient permissions")

def validate_notification_data(title: str, message: str) -> bool:
    """Validate notification title and message"""
    if len(title.strip()) == 0:
        return False

    if len(message.strip()) == 0:
        return False

    if len(title) > notification_service_settings.max_title_length:
        return False

    if len(message) > notification_service_settings.max_message_length:
        return False

    return True

def sanitize_notification_content(text: str) -> str:
    """Sanitize notification content"""
    # Remove potentially harmful HTML/script tags
    text = re.sub(r'<[^>]+>', '', text)

    # Trim whitespace
    text = text.strip()

    # Limit length
    if len(text) > notification_service_settings.max_message_length:
        text = text[:notification_service_settings.max_message_length - 3] + "..."

    return text

def format_notification_message(template: str, variables: Dict[str, Any]) -> str:
    """Format notification message using template and variables"""
    try:
        message = template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            message = message.replace(placeholder, str(value))

        return message
    except Exception as e:
        logger.error("Failed to format notification message", extra={"error": str(e)})
        return template

def get_notification_priority_score(priority: str, type: str) -> int:
    """Calculate notification priority score for queuing"""
    base_score = 0

    # Priority multiplier
    if priority == "urgent":
        base_score += 100
    elif priority == "high":
        base_score += 50
    elif priority == "medium":
        base_score += 25
    else:  # low
        base_score += 10

    # Type multiplier
    if type in ["system_announcement", "deadline_warning"]:
        base_score += 20
    elif type in ["assignment_due", "grade_available"]:
        base_score += 15
    elif type == "achievement_unlocked":
        base_score += 10

    return base_score

def should_send_notification(user_settings: Dict[str, Any], notification_type: str,
                           channels: List[str]) -> List[str]:
    """Determine which channels should be used for notification"""
    allowed_channels = []

    # Check user preferences
    for channel in channels:
        channel_enabled = False

        if channel == "email":
            channel_enabled = user_settings.get("email_enabled", True)
        elif channel == "in_app":
            channel_enabled = user_settings.get("in_app_enabled", True)
        elif channel == "sms":
            channel_enabled = user_settings.get("sms_enabled", False)
        elif channel == "push":
            channel_enabled = user_settings.get("push_enabled", False)

        # Check type-specific preferences
        type_enabled = True
        if notification_type == "course_update":
            type_enabled = user_settings.get("course_updates", True)
        elif notification_type in ["assignment_due", "deadline_warning"]:
            type_enabled = user_settings.get("assignment_deadlines", True)
        elif notification_type == "grade_available":
            type_enabled = user_settings.get("grade_notifications", True)
        elif notification_type == "achievement_unlocked":
            type_enabled = user_settings.get("achievement_notifications", True)
        elif notification_type == "system_announcement":
            type_enabled = user_settings.get("system_announcements", True)

        if channel_enabled and type_enabled:
            allowed_channels.append(channel)

    return allowed_channels

def calculate_delivery_success_rate(delivered: int, total: int) -> float:
    """Calculate delivery success rate"""
    if total == 0:
        return 0.0
    return round((delivered / total) * 100, 2)

def calculate_read_rate(read: int, delivered: int) -> float:
    """Calculate read rate"""
    if delivered == 0:
        return 0.0
    return round((read / delivered) * 100, 2)

def group_notifications_by_priority(notifications: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group notifications by priority for batch processing"""
    groups = {
        "urgent": [],
        "high": [],
        "medium": [],
        "low": []
    }

    for notification in notifications:
        priority = notification.get("priority", "medium")
        groups[priority].append(notification)

    return groups

def validate_email_format(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone_format(phone: str) -> bool:
    """Validate phone number format"""
    # Basic international phone number validation
    pattern = r'^\+?[1-9]\d{1,14}$'
    return re.match(pattern, phone) is not None

def generate_notification_id() -> str:
    """Generate unique notification ID"""
    import uuid
    return f"notif_{uuid.uuid4().hex}"

def get_notification_expiry_date(priority: str) -> datetime:
    """Get notification expiry date based on priority"""
    now = datetime.now(timezone.utc)

    if priority == "urgent":
        # Expire in 1 hour
        return now.replace(hour=now.hour + 1)
    elif priority == "high":
        # Expire in 24 hours
        return now.replace(day=now.day + 1)
    elif priority == "medium":
        # Expire in 7 days
        return now.replace(day=now.day + 7)
    else:  # low
        # Expire in 30 days
        return now.replace(day=now.day + 30)

def is_notification_expired(created_at: datetime, priority: str) -> bool:
    """Check if notification has expired"""
    expiry_date = get_notification_expiry_date(priority)
    return datetime.now(timezone.utc) > expiry_date

def get_channel_retry_count(channel: str) -> int:
    """Get retry count for notification channel"""
    retry_counts = {
        "email": 3,
        "sms": 2,
        "push": 3,
        "in_app": 1
    }

    return retry_counts.get(channel, 1)

def should_retry_delivery(attempt_count: int, channel: str) -> bool:
    """Determine if delivery should be retried"""
    max_attempts = get_channel_retry_count(channel)
    return attempt_count < max_attempts