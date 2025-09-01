"""
Lesson management routes for Course Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations, _require
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger
from shared.models.models import CourseLesson, LessonCreate

logger = get_logger("course-service")
router = APIRouter()
courses_db = DatabaseOperations("courses")

async def _current_user(token: Optional[str] = None):
    """Get current authenticated user"""
    if not token:
        raise HTTPException(401, "No authentication token provided")

    try:
        import jwt
        from shared.config.config import settings

        # Decode and validate JWT token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        # Verify token hasn't expired
        if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(401, "Token has expired")

        # Get user from database
        db = await DatabaseOperations("users").get_database()
        user = await db.users.find_one({"_id": payload.get("sub")})
        if not user:
            raise HTTPException(401, "User not found")

        return {
            "id": user["_id"],
            "role": user.get("role", "student"),
            "email": user.get("email", ""),
            "name": user.get("name", "")
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    except Exception as e:
        raise HTTPException(401, f"Authentication failed: {str(e)}")

def _require_role(user, allowed: list[str]):
    """Check if user has required role"""
    if user.get("role") not in allowed:
        raise HTTPException(403, "Insufficient permissions")

@router.post("/{course_id}/lessons", response_model=dict)
async def add_lesson(course_id: str, body: LessonCreate, user=Depends(_current_user)):
    """
    Add a lesson to a course.

    - **course_id**: Course identifier
    - **title**: Lesson title
    - **content**: Lesson content
    """
    try:
        # Get course
        course = await _require("courses", {"_id": course_id}, "Course not found")

        # Check permissions
        if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
            raise AuthorizationError("Not authorized to add lessons to this course")

        # Create lesson
        lesson = CourseLesson(
            title=body.title,
            content=body.content
        )

        # Add lesson to course
        await courses_db.update_one(
            {"_id": course_id},
            {"$push": {"lessons": lesson.dict()}}
        )

        logger.info("Lesson added to course", extra={
            "course_id": course_id,
            "lesson_title": lesson.title,
            "added_by": user["id"]
        })

        return {
            "status": "added",
            "lesson_id": lesson.id,
            "message": "Lesson added successfully"
        }

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to add lesson", extra={
            "course_id": course_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to add lesson")

@router.get("/{course_id}/lessons")
async def get_course_lessons(course_id: str, user=Depends(_current_user)):
    """
    Get all lessons for a course.

    - **course_id**: Course identifier
    """
    try:
        # Get course
        course = await _require("courses", {"_id": course_id}, "Course not found")

        # Check permissions
        if not (
            course.get("published")
            or course.get("owner_id") == user["id"]
            or user["role"] in ["admin", "auditor"]
            or user["id"] in course.get("enrolled_user_ids", [])
        ):
            raise AuthorizationError("Not authorized to view this course")

        lessons = course.get("lessons", [])

        return {
            "course_id": course_id,
            "lessons": lessons,
            "total_lessons": len(lessons)
        }

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get course lessons", extra={
            "course_id": course_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve lessons")

@router.get("/{course_id}/lessons/{lesson_id}")
async def get_lesson(course_id: str, lesson_id: str, user=Depends(_current_user)):
    """
    Get a specific lesson from a course.

    - **course_id**: Course identifier
    - **lesson_id**: Lesson identifier
    """
    try:
        # Get course
        course = await _require("courses", {"_id": course_id}, "Course not found")

        # Check permissions
        if not (
            course.get("published")
            or course.get("owner_id") == user["id"]
            or user["role"] in ["admin", "auditor"]
            or user["id"] in course.get("enrolled_user_ids", [])
        ):
            raise AuthorizationError("Not authorized to view this course")

        # Find lesson
        lessons = course.get("lessons", [])
        lesson = next((l for l in lessons if l.get("id") == lesson_id), None)

        if not lesson:
            raise NotFoundError("Lesson", lesson_id)

        return lesson

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get lesson", extra={
            "course_id": course_id,
            "lesson_id": lesson_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve lesson")

@router.put("/{course_id}/lessons/{lesson_id}")
async def update_lesson(
    course_id: str,
    lesson_id: str,
    lesson_data: dict,
    user=Depends(_current_user)
):
    """
    Update a lesson in a course.

    - **course_id**: Course identifier
    - **lesson_id**: Lesson identifier
    - **lesson_data**: Updated lesson data
    """
    try:
        # Get course
        course = await _require("courses", {"_id": course_id}, "Course not found")

        # Check permissions
        if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
            raise AuthorizationError("Not authorized to update lessons in this course")

        # Prepare update
        allowed_fields = ["title", "content", "content_type", "resources", "estimated_time"]
        updates = {k: v for k, v in lesson_data.items() if k in allowed_fields and v is not None}

        if not updates:
            raise ValidationError("No valid fields to update", "lesson_data")

        # Update lesson in array
        await courses_db.update_one(
            {"_id": course_id, "lessons.id": lesson_id},
            {"$set": {f"lessons.$.{k}": v for k, v in updates.items()}}
        )

        logger.info("Lesson updated", extra={
            "course_id": course_id,
            "lesson_id": lesson_id,
            "updated_by": user["id"],
            "updated_fields": list(updates.keys())
        })

        return {"status": "updated", "message": "Lesson updated successfully"}

    except (NotFoundError, ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to update lesson", extra={
            "course_id": course_id,
            "lesson_id": lesson_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to update lesson")

@router.delete("/{course_id}/lessons/{lesson_id}")
async def delete_lesson(course_id: str, lesson_id: str, user=Depends(_current_user)):
    """
    Delete a lesson from a course.

    - **course_id**: Course identifier
    - **lesson_id**: Lesson identifier
    """
    try:
        # Get course
        course = await _require("courses", {"_id": course_id}, "Course not found")

        # Check permissions
        if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
            raise AuthorizationError("Not authorized to delete lessons from this course")

        # Remove lesson from array
        await courses_db.update_one(
            {"_id": course_id},
            {"$pull": {"lessons": {"id": lesson_id}}}
        )

        logger.info("Lesson deleted", extra={
            "course_id": course_id,
            "lesson_id": lesson_id,
            "deleted_by": user["id"]
        })

        return {"status": "deleted", "message": "Lesson deleted successfully"}

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to delete lesson", extra={
            "course_id": course_id,
            "lesson_id": lesson_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to delete lesson")

@router.put("/{course_id}/lessons/reorder")
async def reorder_lessons(course_id: str, lesson_order: List[str], user=Depends(_current_user)):
    """
    Reorder lessons in a course.

    - **course_id**: Course identifier
    - **lesson_order**: List of lesson IDs in desired order
    """
    try:
        # Get course
        course = await _require("courses", {"_id": course_id}, "Course not found")

        # Check permissions
        if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
            raise AuthorizationError("Not authorized to reorder lessons in this course")

        # Get current lessons
        lessons = course.get("lessons", [])

        # Validate lesson order
        current_lesson_ids = [l.get("id") for l in lessons]
        if set(lesson_order) != set(current_lesson_ids):
            raise ValidationError("Lesson order doesn't match existing lessons", "lesson_order")

        # Reorder lessons
        reordered_lessons = []
        for lesson_id in lesson_order:
            lesson = next((l for l in lessons if l.get("id") == lesson_id), None)
            if lesson:
                lesson_copy = lesson.copy()
                lesson_copy["order_index"] = len(reordered_lessons)
                reordered_lessons.append(lesson_copy)

        # Update course
        await courses_db.update_one(
            {"_id": course_id},
            {"$set": {"lessons": reordered_lessons}}
        )

        logger.info("Lessons reordered", extra={
            "course_id": course_id,
            "reordered_by": user["id"],
            "new_order": lesson_order
        })

        return {"status": "reordered", "message": "Lessons reordered successfully"}

    except (NotFoundError, ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to reorder lessons", extra={
            "course_id": course_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to reorder lessons")