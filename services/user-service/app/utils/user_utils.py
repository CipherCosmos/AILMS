"""
User Service Utility Functions
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import jwt

from shared.common.logging import get_logger
from shared.common.errors import AuthenticationError
from shared.config.config import settings

logger = get_logger("user-service-utils")

async def get_current_user(token: Optional[str] = None) -> Dict[str, Any]:
    """Get current authenticated user from JWT token"""
    if not token:
        raise AuthenticationError("No authentication token provided")

    try:
        # Decode and validate JWT token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        # Verify token hasn't expired
        if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            raise AuthenticationError("Token has expired")

        # Get user from database (simplified for now)
        # In production, this would query the auth service or user database
        user = {
            "id": payload.get("sub"),
            "role": payload.get("role", "student"),
            "email": payload.get("email", ""),
            "name": payload.get("name", "")
        }

        if not user["id"]:
            raise AuthenticationError("Invalid token: missing user ID")

        return user

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
    except Exception as e:
        logger.error("Authentication failed", extra={"error": str(e)})
        raise AuthenticationError(f"Authentication failed: {str(e)}")

def require_role(user: Dict[str, Any], allowed_roles: list[str]) -> None:
    """Check if user has required role"""
    if user.get("role") not in allowed_roles:
        from shared.common.errors import AuthorizationError
        raise AuthorizationError("Insufficient permissions")

def generate_user_id() -> str:
    """Generate a unique user ID"""
    import uuid
    return str(uuid.uuid4())

def validate_email_format(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input text"""
    if not text:
        return ""

    # Remove potentially harmful characters
    import re
    text = re.sub(r'[<>]', '', text)

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text.strip()

def calculate_profile_completeness(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate profile completeness score"""
    fields_to_check = [
        "bio", "avatar_url", "location", "website",
        "social_links", "skills", "interests", "learning_goals",
        "preferred_learning_style", "timezone", "language",
        "privacy_settings"
    ]

    completed_fields = 0
    missing_fields = []

    for field in fields_to_check:
        value = profile.get(field)
        if value is not None and value != "" and value != [] and value != {}:
            completed_fields += 1
        else:
            missing_fields.append(field)

    completeness_score = int((completed_fields / len(fields_to_check)) * 100)

    return {
        "completeness_score": completeness_score,
        "completed_fields": completed_fields,
        "total_fields": len(fields_to_check),
        "missing_fields": missing_fields,
        "profile_quality": "Excellent" if completeness_score > 80 else "Good" if completeness_score > 60 else "Needs Improvement"
    }

def format_user_display_name(user: Dict[str, Any]) -> str:
    """Format user display name"""
    name = user.get("name", "").strip()
    email = user.get("email", "").strip()

    if name:
        return name
    elif email:
        # Return username part of email
        return email.split('@')[0]
    else:
        return "Anonymous User"

def is_valid_skill(skill: str) -> bool:
    """Validate skill name"""
    if not skill or not isinstance(skill, str):
        return False

    skill = skill.strip()
    # Check length
    if len(skill) < 2 or len(skill) > 50:
        return False

    # Check for valid characters (letters, numbers, spaces, hyphens)
    import re
    if not re.match(r'^[a-zA-Z0-9\s\-]+$', skill):
        return False

    return True

def normalize_skills(skills: list) -> list:
    """Normalize and validate skills list"""
    if not skills:
        return []

    normalized = []
    seen = set()

    for skill in skills:
        if isinstance(skill, str):
            skill = skill.strip().title()
            if is_valid_skill(skill) and skill not in seen:
                normalized.append(skill)
                seen.add(skill)

    return normalized[:50]  # Limit to 50 skills

def calculate_learning_streak(study_sessions: list) -> int:
    """Calculate current learning streak in days"""
    if not study_sessions:
        return 0

    # Sort sessions by date
    sorted_sessions = sorted(study_sessions, key=lambda x: x.get("session_date", datetime.now(timezone.utc)), reverse=True)

    streak = 0
    current_date = datetime.now(timezone.utc).date()

    for session in sorted_sessions:
        session_date = session.get("session_date", datetime.now(timezone.utc))
        if isinstance(session_date, str):
            session_date = datetime.fromisoformat(session_date.replace('Z', '+00:00'))

        session_date = session_date.date()

        if session_date == current_date:
            streak += 1
            current_date = current_date - timedelta(days=1)
        elif session_date == current_date - timedelta(days=1):
            streak += 1
            current_date = session_date
        else:
            break

    return streak

def generate_achievement_recommendations(user_progress: Dict[str, Any]) -> list:
    """Generate achievement recommendations based on user progress"""
    recommendations = []

    completed_courses = user_progress.get("completed_courses", 0)
    total_enrolled = user_progress.get("total_enrolled", 0)
    avg_progress = user_progress.get("average_progress", 0)

    if completed_courses == 0:
        recommendations.append({
            "achievement": "First Steps",
            "description": "Complete your first course",
            "progress": 0,
            "target": 1
        })

    if completed_courses < 3:
        recommendations.append({
            "achievement": "Dedicated Learner",
            "description": f"Complete {3 - completed_courses} more courses",
            "progress": completed_courses,
            "target": 3
        })

    if avg_progress < 70:
        recommendations.append({
            "achievement": "Progress Master",
            "description": "Increase average course progress",
            "progress": int(avg_progress),
            "target": 70
        })

    return recommendations[:5]  # Return top 5 recommendations