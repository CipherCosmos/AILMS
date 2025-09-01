"""
Progress tracking routes for Course Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations, _require
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("course-service")
router = APIRouter()
courses_db = DatabaseOperations("courses")
progress_db = DatabaseOperations("course_progress")

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

@router.post("/{course_id}/progress")
async def update_progress(course_id: str, progress_data: dict, user=Depends(_current_user)):
    """
    Update course progress for a user.

    - **course_id**: Course identifier
    - **lesson_id**: Lesson identifier (optional)
    - **completed**: Whether lesson is completed
    - **quiz_score**: Quiz score (optional)
    """
    try:
        # Get course
        course = await _require("courses", {"_id": course_id}, "Course not found")

        # Check if user is enrolled
        if user["id"] not in course.get("enrolled_user_ids", []):
            raise AuthorizationError("Not enrolled in this course")

        # Get or create progress document
        progress_doc = await progress_db.find_one({
            "course_id": course_id,
            "user_id": user["id"]
        })

        if not progress_doc:
            progress_doc = {
                "course_id": course_id,
                "user_id": user["id"],
                "lessons_progress": [],
                "overall_progress": 0,
                "completed": False,
                "started_at": datetime.now(timezone.utc)
            }

        lesson_id = progress_data.get("lesson_id")
        completed = progress_data.get("completed", False)
        quiz_score = progress_data.get("quiz_score")

        # Update lesson progress if lesson_id provided
        if lesson_id:
            lesson_progress = next(
                (lp for lp in progress_doc["lessons_progress"] if lp["lesson_id"] == lesson_id),
                None
            )

            if not lesson_progress:
                lesson_progress = {"lesson_id": lesson_id, "completed": False}
                progress_doc["lessons_progress"].append(lesson_progress)

            if completed and not lesson_progress["completed"]:
                lesson_progress["completed"] = True
                lesson_progress["completed_at"] = datetime.now(timezone.utc)

            if quiz_score is not None:
                lesson_progress["quiz_score"] = quiz_score
                lesson_progress["quiz_completed"] = True
                lesson_progress["quiz_completed_at"] = datetime.now(timezone.utc)

        # Calculate overall progress
        total_lessons = len(course.get("lessons", []))
        completed_lessons = sum(1 for lp in progress_doc["lessons_progress"] if lp["completed"])
        progress_doc["overall_progress"] = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

        # Check if course is completed
        if progress_doc["overall_progress"] >= 100 and not progress_doc.get("completed", False):
            progress_doc["completed"] = True
            progress_doc["completed_at"] = datetime.now(timezone.utc)

        # Save progress
        await progress_db.update_one(
            {"course_id": course_id, "user_id": user["id"]},
            {"$set": progress_doc},
            upsert=True
        )

        logger.info("Progress updated", extra={
            "course_id": course_id,
            "user_id": user["id"],
            "overall_progress": progress_doc["overall_progress"],
            "completed": progress_doc["completed"]
        })

        return {
            "progress": progress_doc.get("overall_progress", 0),
            "completed": progress_doc.get("completed", False),
            "message": "Progress updated successfully"
        }

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to update progress", extra={
            "course_id": course_id,
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to update progress")

@router.get("/{course_id}/progress")
async def get_progress(course_id: str, user=Depends(_current_user)):
    """
    Get course progress for a user.

    - **course_id**: Course identifier
    """
    try:
        # Verify course exists
        await _require("courses", {"_id": course_id}, "Course not found")

        # Get progress
        progress = await progress_db.find_one({
            "course_id": course_id,
            "user_id": user["id"]
        })

        if not progress:
            return {
                "course_id": course_id,
                "user_id": user["id"],
                "lessons_progress": [],
                "overall_progress": 0.0,
                "completed": False,
                "message": "No progress found"
            }

        return progress

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to get progress", extra={
            "course_id": course_id,
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve progress")

@router.get("/{course_id}/progress/stats")
async def get_progress_stats(course_id: str, user=Depends(_current_user)):
    """
    Get detailed progress statistics for a course.

    - **course_id**: Course identifier
    """
    try:
        # Get course
        course = await _require("courses", {"_id": course_id}, "Course not found")

        # Check permissions (only enrolled users or instructors can view progress)
        if not (
            user["role"] in ["admin", "instructor"]
            or course.get("owner_id") == user["id"]
            or user["id"] in course.get("enrolled_user_ids", [])
        ):
            raise AuthorizationError("Not authorized to view progress for this course")

        # Get all progress records for this course
        all_progress = await progress_db.find_many({"course_id": course_id})

        if not all_progress:
            return {
                "course_id": course_id,
                "total_enrolled": len(course.get("enrolled_user_ids", [])),
                "total_with_progress": 0,
                "average_progress": 0,
                "completion_rate": 0,
                "message": "No progress data available"
            }

        # Calculate statistics
        total_enrolled = len(course.get("enrolled_user_ids", []))
        total_with_progress = len(all_progress)
        completed_count = sum(1 for p in all_progress if p.get("completed", False))

        average_progress = sum(p.get("overall_progress", 0) for p in all_progress) / len(all_progress)
        completion_rate = (completed_count / max(total_with_progress, 1)) * 100

        return {
            "course_id": course_id,
            "total_enrolled": total_enrolled,
            "total_with_progress": total_with_progress,
            "average_progress": round(average_progress, 1),
            "completion_rate": round(completion_rate, 1),
            "completed_students": completed_count
        }

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get progress stats", extra={
            "course_id": course_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve progress statistics")

@router.get("/user/progress")
async def get_user_all_progress(user=Depends(_current_user)):
    """
    Get progress for all courses the user is enrolled in.
    """
    try:
        # Get all progress records for user
        all_progress = await progress_db.find_many({"user_id": user["id"]})

        if not all_progress:
            return {
                "user_id": user["id"],
                "courses_progress": [],
                "total_courses": 0,
                "completed_courses": 0,
                "average_progress": 0,
                "message": "No progress data found"
            }

        # Calculate summary statistics
        total_courses = len(all_progress)
        completed_courses = sum(1 for p in all_progress if p.get("completed", False))
        average_progress = sum(p.get("overall_progress", 0) for p in all_progress) / total_courses

        return {
            "user_id": user["id"],
            "courses_progress": all_progress,
            "total_courses": total_courses,
            "completed_courses": completed_courses,
            "average_progress": round(average_progress, 1),
            "completion_percentage": round((completed_courses / total_courses) * 100, 1)
        }

    except Exception as e:
        logger.error("Failed to get user progress", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve user progress")

@router.post("/{course_id}/progress/reset")
async def reset_progress(course_id: str, user=Depends(_current_user)):
    """
    Reset progress for a course (admin/instructor only).

    - **course_id**: Course identifier
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "instructor"])

        # Verify course exists
        await _require("courses", {"_id": course_id}, "Course not found")

        # Reset progress (set to empty state)
        reset_data = {
            "course_id": course_id,
            "user_id": user["id"],  # Reset for the requesting user
            "lessons_progress": [],
            "overall_progress": 0,
            "completed": False,
            "reset_at": datetime.now(timezone.utc)
        }

        await progress_db.update_one(
            {"course_id": course_id, "user_id": user["id"]},
            {"$set": reset_data},
            upsert=True
        )

        logger.info("Progress reset", extra={
            "course_id": course_id,
            "reset_by": user["id"]
        })

        return {"status": "reset", "message": "Progress reset successfully"}

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to reset progress", extra={
            "course_id": course_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to reset progress")