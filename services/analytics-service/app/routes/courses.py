"""
Course analytics routes for Analytics Service
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations
from shared.common.errors import NotFoundError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("analytics-service")
router = APIRouter()

@router.get("/course/{course_id}")
async def get_course_analytics(
    course_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive analytics for a course.

    - **course_id**: Course identifier
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only instructors can view course analytics")

        # Get course info
        courses_db = DatabaseOperations("courses")
        course = await courses_db.find_one({"_id": course_id})
        if not course:
            raise NotFoundError("Course", course_id)

        # Check if instructor owns the course or is admin
        if not (
            current_user["role"] == "admin" or
            course.get("owner_id") == current_user["id"]
        ):
            raise AuthorizationError("Not authorized to view analytics for this course")

        # Get enrollment data
        courses_db = DatabaseOperations("courses")
        enrollments = len(await courses_db.find_many({"_id": course_id}))

        # Get progress data
        progress_db = DatabaseOperations("course_progress")
        progress_data = await progress_db.find_many({"course_id": course_id})

        # Calculate completion rate
        completed_count = len([p for p in progress_data if p.get("completed")])
        completion_rate = (completed_count / max(enrollments, 1)) * 100

        # Calculate average progress
        avg_progress = 0.0
        if progress_data:
            avg_progress = sum([p.get("overall_progress", 0) for p in progress_data]) / len(progress_data)

        # Get submission data
        submissions_db = DatabaseOperations("submissions")
        submissions = await submissions_db.find_many({
            "assignment_id": {"$in": []}  # Would need assignment IDs from course
        })

        # Calculate engagement metrics
        total_submissions = len(submissions)
        avg_submissions_per_student = total_submissions / max(enrollments, 1)

        # Get time-based analytics (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_progress = await progress_db.find_many({
            "course_id": course_id,
            "last_accessed": {"$gte": thirty_days_ago}
        })

        active_students = len(set([p["user_id"] for p in recent_progress]))

        return {
            "course_id": course_id,
            "course_title": course.get("title"),
            "enrollments": enrollments,
            "active_students": active_students,
            "completion_rate": round(completion_rate, 1),
            "average_progress": round(avg_progress, 1),
            "total_submissions": total_submissions,
            "avg_submissions_per_student": round(avg_submissions_per_student, 1),
            "progress_records": len(progress_data),
            "engagement_rate": round((active_students / max(enrollments, 1)) * 100, 1) if enrollments > 0 else 0
        }

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get course analytics", extra={
            "course_id": course_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve course analytics")

@router.get("/course/{course_id}/detailed")
async def get_detailed_course_analytics(
    course_id: str,
    timeframe: str = "month",
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed analytics for a course with time-based breakdowns.

    - **course_id**: Course identifier
    - **timeframe**: Analysis period (week, month, quarter)
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only instructors can view detailed analytics")

        # Get course info
        courses_db = DatabaseOperations("courses")
        course = await courses_db.find_one({"_id": course_id})
        if not course:
            raise NotFoundError("Course", course_id)

        # Check ownership
        if not (
            current_user["role"] == "admin" or
            course.get("owner_id") == current_user["id"]
        ):
            raise AuthorizationError("Not authorized to view analytics for this course")

        # Calculate date range
        now = datetime.now(timezone.utc)
        if timeframe == "week":
            start_date = now - timedelta(days=7)
        elif timeframe == "month":
            start_date = now - timedelta(days=30)
        elif timeframe == "quarter":
            start_date = now - timedelta(days=90)
        else:
            start_date = now - timedelta(days=30)

        # Get progress data in timeframe
        progress_db = DatabaseOperations("course_progress")
        progress_data = await progress_db.find_many({
            "course_id": course_id,
            "last_accessed": {"$gte": start_date}
        })

        # Group by day
        daily_stats = {}
        for progress in progress_data:
            date = progress.get("last_accessed", progress.get("created_at", now)).date()
            if date not in daily_stats:
                daily_stats[date] = {
                    "active_users": 0,
                    "avg_progress": 0,
                    "completions": 0
                }

            daily_stats[date]["active_users"] += 1
            daily_stats[date]["avg_progress"] += progress.get("overall_progress", 0)
            if progress.get("completed"):
                daily_stats[date]["completions"] += 1

        # Calculate averages
        for date, stats in daily_stats.items():
            if stats["active_users"] > 0:
                stats["avg_progress"] /= stats["active_users"]

        # Get lesson completion breakdown
        lesson_completion = {}
        for progress in progress_data:
            lessons_progress = progress.get("lessons_progress", [])
            for lesson in lessons_progress:
                lesson_id = lesson.get("lesson_id")
                if lesson_id:
                    if lesson_id not in lesson_completion:
                        lesson_completion[lesson_id] = {
                            "completed": 0,
                            "total_attempts": 0
                        }
                    lesson_completion[lesson_id]["total_attempts"] += 1
                    if lesson.get("completed"):
                        lesson_completion[lesson_id]["completed"] += 1

        return {
            "course_id": course_id,
            "course_title": course.get("title"),
            "timeframe": timeframe,
            "total_active_users": len(set([p["user_id"] for p in progress_data])),
            "daily_stats": [
                {
                    "date": date.isoformat(),
                    "active_users": stats["active_users"],
                    "avg_progress": round(stats["avg_progress"], 1),
                    "completions": stats["completions"]
                }
                for date, stats in daily_stats.items()
            ],
            "lesson_completion": [
                {
                    "lesson_id": lesson_id,
                    "completion_rate": round((stats["completed"] / max(stats["total_attempts"], 1)) * 100, 1),
                    "total_attempts": stats["total_attempts"]
                }
                for lesson_id, stats in lesson_completion.items()
            ]
        }

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get detailed course analytics", extra={
            "course_id": course_id,
            "timeframe": timeframe,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve detailed analytics")

@router.get("/courses/overview")
async def get_courses_overview(current_user: dict = Depends(get_current_user)):
    """
    Get overview analytics for all courses (admin/instructor only).
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only instructors can view courses overview")

        # Get all courses (for instructor, only their courses)
        courses_db = DatabaseOperations("courses")
        if current_user["role"] == "admin":
            courses = await courses_db.find_many({})
        else:
            courses = await courses_db.find_many({
                "owner_id": current_user["id"]
            })

        # Calculate overview statistics
        total_courses = len(courses)
        published_courses = len([c for c in courses if c.get("published")])

        # Get enrollment data for all courses
        course_ids = [c["_id"] for c in courses]
        total_enrollments = 0
        total_completions = 0

        progress_db = DatabaseOperations("course_progress")
        for course_id in course_ids:
            enrollments = len(await courses_db.find_many({"_id": course_id}))
            total_enrollments += enrollments

            progress_data = await progress_db.find_many({"course_id": course_id})
            completions = len([p for p in progress_data if p.get("completed")])
            total_completions += completions

        return {
            "total_courses": total_courses,
            "published_courses": published_courses,
            "draft_courses": total_courses - published_courses,
            "total_enrollments": total_enrollments,
            "total_completions": total_completions,
            "overall_completion_rate": round((total_completions / max(total_enrollments, 1)) * 100, 1),
            "avg_enrollments_per_course": round(total_enrollments / max(total_courses, 1), 1)
        }

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get courses overview", extra={"error": str(e)})
        raise HTTPException(500, "Failed to retrieve courses overview")