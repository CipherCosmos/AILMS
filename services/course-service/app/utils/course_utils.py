"""
Course Service Utility Functions
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import jwt

from shared.common.logging import get_logger
from shared.common.errors import AuthenticationError
from shared.config.config import settings

logger = get_logger("course-service-utils")

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

def generate_course_id() -> str:
    """Generate a unique course ID"""
    import uuid
    return str(uuid.uuid4())

def validate_course_data(course_data: Dict[str, Any]) -> List[str]:
    """Validate course data and return list of errors"""
    errors = []

    if not course_data.get("title", "").strip():
        errors.append("Course title is required")

    if len(course_data.get("title", "")) > 200:
        errors.append("Course title must be less than 200 characters")

    if course_data.get("description") and len(course_data["description"]) > 2000:
        errors.append("Course description must be less than 2000 characters")

    if course_data.get("difficulty") not in ["beginner", "intermediate", "advanced"]:
        errors.append("Difficulty must be one of: beginner, intermediate, advanced")

    return errors

def sanitize_course_content(content: str, max_length: int = 50000) -> str:
    """Sanitize and truncate course content"""
    if not content:
        return ""

    # Basic sanitization - remove potentially harmful content
    content = content.strip()

    # Truncate if too long
    if len(content) > max_length:
        content = content[:max_length] + "..."

    return content

def calculate_course_completion(course: Dict[str, Any], user_progress: Dict[str, Any]) -> float:
    """Calculate course completion percentage"""
    if not course.get("lessons"):
        return 100.0 if user_progress.get("completed") else 0.0

    total_lessons = len(course["lessons"])
    if total_lessons == 0:
        return 100.0

    completed_lessons = 0
    lesson_progress = user_progress.get("lesson_progress", {})

    for lesson in course["lessons"]:
        lesson_id = lesson.get("id") or lesson.get("_id")
        if lesson_id and lesson_progress.get(lesson_id, {}).get("completed"):
            completed_lessons += 1

    return (completed_lessons / total_lessons) * 100

def format_course_for_display(course: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    """Format course data for API response"""
    formatted = course.copy()

    # Add computed fields
    formatted["enrollment_count"] = len(course.get("enrolled_user_ids", []))
    formatted["is_enrolled"] = user_id in course.get("enrolled_user_ids", []) if user_id else False
    formatted["is_owner"] = course.get("owner_id") == user_id if user_id else False

    # Remove sensitive fields for non-owners
    if not formatted["is_owner"]:
        formatted.pop("enrolled_user_ids", None)

    return formatted

def build_course_search_query(search_term: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Build MongoDB query for course search"""
    query = {}

    # Text search
    if search_term:
        query["$or"] = [
            {"title": {"$regex": search_term, "$options": "i"}},
            {"description": {"$regex": search_term, "$options": "i"}},
            {"topic": {"$regex": search_term, "$options": "i"}}
        ]

    # Apply filters
    if filters.get("audience"):
        query["audience"] = filters["audience"]

    if filters.get("difficulty"):
        query["difficulty"] = filters["difficulty"]

    if filters.get("published_only"):
        query["published"] = True

    return query

def validate_lesson_data(lesson_data: Dict[str, Any]) -> List[str]:
    """Validate lesson data and return list of errors"""
    errors = []

    if not lesson_data.get("title", "").strip():
        errors.append("Lesson title is required")

    if len(lesson_data.get("title", "")) > 150:
        errors.append("Lesson title must be less than 150 characters")

    if not lesson_data.get("content", "").strip():
        errors.append("Lesson content is required")

    if len(lesson_data.get("content", "")) > 50000:
        errors.append("Lesson content must be less than 50,000 characters")

    if lesson_data.get("order", 0) < 0:
        errors.append("Lesson order must be non-negative")

    return errors

def generate_course_recommendations(user_id: str, user_profile: Dict[str, Any],
                                  enrolled_courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate course recommendations based on user profile and history"""
    recommendations = []

    # Extract user interests and skills
    interests = user_profile.get("interests", [])
    skills = user_profile.get("skills", [])
    learning_goals = user_profile.get("learning_goals", [])

    # Get enrolled course topics
    enrolled_topics = set()
    for course in enrolled_courses:
        if course.get("topic"):
            enrolled_topics.add(course["topic"])
        if course.get("title"):
            # Extract keywords from title
            title_words = course["title"].lower().split()
            enrolled_topics.update(title_words)

    # Generate recommendations based on interests
    for interest in interests:
        if interest.lower() not in [t.lower() for t in enrolled_topics]:
            recommendations.append({
                "topic": interest,
                "reason": f"Based on your interest in {interest}",
                "priority": "high"
            })

    # Generate recommendations based on learning goals
    for goal in learning_goals:
        if goal.lower() not in [t.lower() for t in enrolled_topics]:
            recommendations.append({
                "topic": goal,
                "reason": f"Aligns with your learning goal: {goal}",
                "priority": "high"
            })

    # Generate recommendations for skill gaps
    common_skills = ["python", "javascript", "data analysis", "machine learning", "web development"]
    for skill in common_skills:
        if skill not in [s.lower() for s in skills] and skill not in [t.lower() for t in enrolled_topics]:
            recommendations.append({
                "topic": skill,
                "reason": f"Popular skill: {skill}",
                "priority": "medium"
            })

    return recommendations[:10]  # Return top 10 recommendations