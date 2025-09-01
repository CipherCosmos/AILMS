"""
Advanced reporting routes for Analytics Service
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations
from shared.common.errors import AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("analytics-service")
router = APIRouter()

@router.get("/reports/summary")
async def get_system_summary_report(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Get system-wide summary report.

    - **days**: Number of days to analyze (default: 30)
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only administrators can access system reports")

        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Get course statistics
        courses_db = DatabaseOperations("courses")
        total_courses = len(await courses_db.find_many({}))
        published_courses = len(await courses_db.find_many({"published": True}))

        # Get user statistics
        users_db = DatabaseOperations("users")
        total_users = len(await users_db.find_many({}))
        progress_db = DatabaseOperations("course_progress")
        active_users = len(await progress_db.find_many({
            "last_accessed": {"$gte": start_date}
        }))

        # Get enrollment statistics
        total_enrollments = 0
        courses = await courses_db.find_many({})
        for course in courses:
            enrollments = len(await courses_db.find_many({"_id": course["_id"]}))
            total_enrollments += enrollments

        # Get progress statistics
        progress_data = await progress_db.find_many({
            "last_accessed": {"$gte": start_date}
        })

        completed_courses = len([p for p in progress_data if p.get("completed")])
        total_progress_records = len(progress_data)

        # Get submission statistics
        submissions_db = DatabaseOperations("submissions")
        submissions = await submissions_db.find_many({
            "created_at": {"$gte": start_date}
        })

        return {
            "report_period": f"{days} days",
            "generated_at": end_date.isoformat(),
            "courses": {
                "total": total_courses,
                "published": published_courses,
                "draft": total_courses - published_courses
            },
            "users": {
                "total": total_users,
                "active": len(set([p["user_id"] for p in progress_data]))
            },
            "enrollments": {
                "total": total_enrollments,
                "average_per_course": round(total_enrollments / max(total_courses, 1), 1)
            },
            "activity": {
                "total_progress_records": total_progress_records,
                "completed_courses": completed_courses,
                "total_submissions": len(submissions),
                "completion_rate": round((completed_courses / max(total_progress_records, 1)) * 100, 1)
            }
        }

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to generate summary report", extra={
            "days": days,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to generate summary report")

@router.get("/reports/course-performance")
async def get_course_performance_report(
    course_id: Optional[str] = None,
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Get course performance report.

    - **course_id**: Specific course ID (optional - if not provided, returns all courses)
    - **days**: Number of days to analyze
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only instructors can access course performance reports")

        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Get courses to analyze
        courses_db = DatabaseOperations("courses")
        if course_id:
            courses = [await courses_db.find_one({"_id": course_id})]
            if not courses[0]:
                raise HTTPException(404, "Course not found")
        else:
            if current_user["role"] == "admin":
                courses = await courses_db.find_many({})
            else:
                courses = await courses_db.find_many({
                    "owner_id": current_user["id"]
                })

        # Analyze each course
        course_reports = []
        for course in courses:
            if not course:
                continue

            # Get progress data
            progress_db = DatabaseOperations("course_progress")
            progress_data = await progress_db.find_many({
                "course_id": course["_id"],
                "last_accessed": {"$gte": start_date}
            })

            # Get enrollment data
            enrollments = len(await courses_db.find_many({"_id": course["_id"]}))

            # Calculate metrics
            active_students = len(set([p["user_id"] for p in progress_data]))
            completed_count = len([p for p in progress_data if p.get("completed")])
            avg_progress = sum([p.get("overall_progress", 0) for p in progress_data]) / max(len(progress_data), 1)

            # Get submission data
            submissions_db = DatabaseOperations("submissions")
            submissions = await submissions_db.find_many({
                "assignment_id": {"$in": []},  # Would need assignment IDs
                "created_at": {"$gte": start_date}
            })

            course_reports.append({
                "course_id": course["_id"],
                "course_title": course.get("title"),
                "enrollments": enrollments,
                "active_students": active_students,
                "completed_courses": completed_count,
                "average_progress": round(avg_progress, 1),
                "completion_rate": round((completed_count / max(active_students, 1)) * 100, 1),
                "total_submissions": len(submissions),
                "engagement_rate": round((active_students / max(enrollments, 1)) * 100, 1)
            })

        return {
            "report_period": f"{days} days",
            "generated_at": end_date.isoformat(),
            "total_courses": len(course_reports),
            "courses": course_reports
        }

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to generate course performance report", extra={
            "course_id": course_id,
            "days": days,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to generate course performance report")

@router.get("/reports/user-engagement")
async def get_user_engagement_report(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user engagement report.

    - **days**: Number of days to analyze
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only administrators can access user engagement reports")

        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Get all progress data in timeframe
        progress_db = DatabaseOperations("course_progress")
        progress_data = await progress_db.find_many({
            "last_accessed": {"$gte": start_date}
        })

        # Group by user
        user_engagement = {}
        for progress in progress_data:
            user_id = progress["user_id"]
            if user_id not in user_engagement:
                user_engagement[user_id] = {
                    "courses_accessed": 0,
                    "total_time": 0,
                    "lessons_completed": 0,
                    "last_activity": progress.get("last_accessed", progress.get("created_at"))
                }

            user_engagement[user_id]["courses_accessed"] += 1
            user_engagement[user_id]["total_time"] += progress.get("time_spent", 0)

            lessons_progress = progress.get("lessons_progress", [])
            user_engagement[user_id]["lessons_completed"] += len([
                lp for lp in lessons_progress if lp.get("completed")
            ])

        # Calculate engagement levels
        highly_engaged = len([u for u in user_engagement.values() if u["courses_accessed"] >= 3])
        moderately_engaged = len([u for u in user_engagement.values() if 1 <= u["courses_accessed"] < 3])
        low_engaged = len([u for u in user_engagement.values() if u["courses_accessed"] == 1])

        # Calculate average metrics
        total_users = len(user_engagement)
        avg_courses_per_user = sum(u["courses_accessed"] for u in user_engagement.values()) / max(total_users, 1)
        avg_time_per_user = sum(u["total_time"] for u in user_engagement.values()) / max(total_users, 1)
        avg_lessons_per_user = sum(u["lessons_completed"] for u in user_engagement.values()) / max(total_users, 1)

        return {
            "report_period": f"{days} days",
            "generated_at": end_date.isoformat(),
            "total_active_users": total_users,
            "engagement_levels": {
                "highly_engaged": highly_engaged,  # 3+ courses
                "moderately_engaged": moderately_engaged,  # 1-2 courses
                "low_engaged": low_engaged  # 1 course
            },
            "averages": {
                "courses_per_user": round(avg_courses_per_user, 1),
                "time_per_user": round(avg_time_per_user, 1),
                "lessons_per_user": round(avg_lessons_per_user, 1)
            },
            "engagement_distribution": {
                "high": round((highly_engaged / max(total_users, 1)) * 100, 1),
                "moderate": round((moderately_engaged / max(total_users, 1)) * 100, 1),
                "low": round((low_engaged / max(total_users, 1)) * 100, 1)
            }
        }

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to generate user engagement report", extra={
            "days": days,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to generate user engagement report")