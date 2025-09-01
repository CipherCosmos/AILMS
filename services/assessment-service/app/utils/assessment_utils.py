"""
Assessment Service Utility Functions
"""
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from shared.common.logging import get_logger
from config.config import assessment_service_settings

logger = get_logger("assessment-service-utils")

def generate_submission_hash(content: str, student_id: str, assignment_id: str) -> str:
    """Generate hash for submission content"""
    content_str = f"{content}{student_id}{assignment_id}{datetime.now(timezone.utc).isoformat()}"
    return hashlib.md5(content_str.encode()).hexdigest()

def calculate_late_penalty(due_date: datetime, submitted_at: datetime, max_score: int) -> float:
    """Calculate late submission penalty"""
    if submitted_at <= due_date:
        return 0.0

    # Calculate hours late
    hours_late = (submitted_at - due_date).total_seconds() / 3600

    # Apply penalty based on hours late
    if hours_late <= 24:
        penalty_percent = assessment_service_settings.late_submission_penalty_percent
    else:
        penalty_percent = min(50, assessment_service_settings.late_submission_penalty_percent * (hours_late // 24))

    return (penalty_percent / 100) * max_score

def validate_file_type(filename: str) -> bool:
    """Validate file type for submissions"""
    import os
    _, ext = os.path.splitext(filename.lower())
    return ext in assessment_service_settings.allowed_file_types

def calculate_grade_percentage(score: float, max_score: int) -> float:
    """Calculate grade as percentage"""
    if max_score == 0:
        return 0.0
    return round((score / max_score) * 100, 2)

def convert_to_letter_grade(percentage: float) -> str:
    """Convert percentage to letter grade"""
    if percentage >= 90:
        return "A"
    elif percentage >= 80:
        return "B"
    elif percentage >= 70:
        return "C"
    elif percentage >= 60:
        return "D"
    else:
        return "F"

def check_plagiarism(text: str, assignment_id: str) -> Dict[str, Any]:
    """Check submission for plagiarism"""
    # This would integrate with plagiarism detection service
    # For now, return mock results
    return {
        "similarity_score": 15.5,
        "flagged": False,
        "matches": [],
        "checked_at": datetime.now(timezone.utc).isoformat()
    }

def generate_feedback_suggestions(score: float, max_score: int, assignment_type: str) -> List[str]:
    """Generate feedback suggestions based on score"""
    percentage = calculate_grade_percentage(score, max_score)
    suggestions = []

    if percentage >= 90:
        suggestions.append("Excellent work! Consider challenging yourself with advanced topics.")
    elif percentage >= 80:
        suggestions.append("Good work! Focus on the minor areas for improvement.")
    elif percentage >= 70:
        suggestions.append("Solid effort. Review the key concepts and try again.")
    elif percentage >= 60:
        suggestions.append("Needs improvement. Consider additional study time and practice.")
    else:
        suggestions.append("Significant improvement needed. Consider tutoring or additional resources.")

    return suggestions

def calculate_assignment_progress(assignment: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate assignment progress metrics"""
    due_date = assignment.get("due_date")
    if isinstance(due_date, str):
        due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))

    now = datetime.now(timezone.utc)

    if due_date and now < due_date:
        days_remaining = (due_date - now).days
        progress_percentage = max(0, 100 - (days_remaining * 2))  # Rough estimate
    else:
        days_remaining = 0
        progress_percentage = 100

    return {
        "days_remaining": days_remaining,
        "progress_percentage": progress_percentage,
        "is_overdue": due_date and now > due_date,
        "urgency_level": "high" if days_remaining <= 1 else "medium" if days_remaining <= 3 else "low"
    }

def validate_assignment_deadline(due_date: datetime) -> bool:
    """Validate assignment deadline"""
    now = datetime.now(timezone.utc)
    min_deadline_hours = 1  # Minimum 1 hour from now

    return due_date > now + timedelta(hours=min_deadline_hours)

def generate_assignment_summary(assignment: Dict[str, Any], submissions_count: int) -> Dict[str, Any]:
    """Generate assignment summary"""
    return {
        "assignment_id": assignment.get("_id"),
        "title": assignment.get("title"),
        "due_date": assignment.get("due_date"),
        "total_submissions": submissions_count,
        "status": assignment.get("status", "draft"),
        "max_points": assignment.get("max_points", 100),
        "progress": calculate_assignment_progress(assignment)
    }

def calculate_student_performance_trend(student_grades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate student's performance trend"""
    if not student_grades:
        return {"trend": "no_data", "change": 0.0}

    # Sort by date
    sorted_grades = sorted(student_grades, key=lambda x: x.get("graded_at", datetime.now(timezone.utc)))

    # Calculate trend
    recent_grades = sorted_grades[-5:]  # Last 5 grades
    if len(recent_grades) < 2:
        return {"trend": "stable", "change": 0.0}

    # Calculate percentage scores
    percentages = [calculate_grade_percentage(g.get("score", 0), g.get("max_score", 100)) for g in recent_grades]

    # Calculate trend
    first_avg = sum(percentages[:len(percentages)//2]) / (len(percentages)//2)
    second_avg = sum(percentages[len(percentages)//2:]) / (len(percentages) - len(percentages)//2)

    change = second_avg - first_avg

    if change > 5:
        trend = "improving"
    elif change < -5:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "trend": trend,
        "change": round(change, 2),
        "recent_average": round(second_avg, 2)
    }

def format_grade_for_display(score: float, max_score: int) -> str:
    """Format grade for display"""
    percentage = calculate_grade_percentage(score, max_score)
    letter = convert_to_letter_grade(percentage)

    return f"{score}/{max_score} ({percentage:.1f}%) - {letter}"

def check_assignment_access(user_id: str, assignment: Dict[str, Any], user_role: str) -> bool:
    """Check if user has access to assignment"""
    if user_role == "instructor":
        return assignment.get("instructor_id") == user_id
    elif user_role == "student":
        # Check if student is enrolled in the course
        # This would typically query the course service
        return True  # Simplified for now
    else:
        return False

def generate_assignment_notifications(assignment: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate notifications for assignment events"""
    notifications = []

    # Due date reminder
    progress = calculate_assignment_progress(assignment)
    if progress["urgency_level"] == "high":
        notifications.append({
            "type": "deadline_reminder",
            "message": f"Assignment '{assignment.get('title')}' is due soon!",
            "priority": "high"
        })

    return notifications

def validate_rubric_criteria(rubric: Dict[str, Any]) -> bool:
    """Validate rubric criteria"""
    criteria = rubric.get("criteria", [])
    if not criteria:
        return False

    for criterion in criteria:
        if not criterion.get("name") or not isinstance(criterion.get("max_points", 0), (int, float)):
            return False

    return True

def calculate_rubric_score(rubric_scores: Dict[str, Any], rubric: Dict[str, Any]) -> float:
    """Calculate total score from rubric"""
    total_score = 0.0
    criteria = rubric.get("criteria", [])

    for criterion in criteria:
        criterion_name = criterion.get("name")
        if criterion_name in rubric_scores:
            score = rubric_scores[criterion_name]
            total_score += min(score, criterion.get("max_points", 0))

    return total_score

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