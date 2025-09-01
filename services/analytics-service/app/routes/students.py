"""
Student analytics routes for Analytics Service
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations
from shared.common.errors import NotFoundError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("analytics-service")
router = APIRouter()

@router.get("/student/{user_id}")
async def get_student_analytics(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive analytics for a student.

    - **user_id**: Student identifier
    """
    try:
        # Check permissions (users can view their own analytics, instructors can view any)
        if user_id != current_user["id"] and current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to view this student's analytics")

        # Get student's progress data
        progress_db = DatabaseOperations("course_progress")
        progress_data = await progress_db.find_many({"user_id": user_id})

        if not progress_data:
            return {
                "user_id": user_id,
                "courses_enrolled": 0,
                "courses_completed": 0,
                "total_time_spent": 0,
                "average_progress": 0.0,
                "lessons_completed": 0,
                "message": "No progress data available"
            }

        # Calculate metrics
        courses_enrolled = len(progress_data)
        courses_completed = len([p for p in progress_data if p.get("completed")])

        lessons_completed = sum([
            len([lp for lp in p.get("lessons_progress", []) if lp.get("completed")])
            for p in progress_data
        ])

        total_time_spent = sum([p.get("time_spent", 0) for p in progress_data])

        avg_progress = sum([p.get("overall_progress", 0) for p in progress_data]) / courses_enrolled

        # Get submission data
        submissions_db = DatabaseOperations("submissions")
        submissions = await submissions_db.find_many({"user_id": user_id})
        total_submissions = len(submissions)

        # Calculate grades
        grades = []
        for submission in submissions:
            if submission.get("manual_grade"):
                grades.append(submission["manual_grade"].get("score", 0))
            elif submission.get("ai_grade"):
                grades.append(submission["ai_grade"].get("score", 0))

        avg_grade = sum(grades) / len(grades) if grades else 0

        # Get recent activity (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_progress = [p for p in progress_data if p.get("last_accessed", p.get("created_at", datetime.min.replace(tzinfo=timezone.utc))) >= thirty_days_ago]

        return {
            "user_id": user_id,
            "courses_enrolled": courses_enrolled,
            "courses_completed": courses_completed,
            "completion_rate": round((courses_completed / max(courses_enrolled, 1)) * 100, 1),
            "lessons_completed": lessons_completed,
            "total_time_spent": total_time_spent,
            "average_progress": round(avg_progress, 1),
            "total_submissions": total_submissions,
            "average_grade": round(avg_grade, 1),
            "recent_activity": len(recent_progress),
            "engagement_score": round((len(recent_progress) / max(courses_enrolled, 1)) * 100, 1)
        }

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get student analytics", extra={
            "user_id": user_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve student analytics")

@router.get("/student/{user_id}/detailed")
async def get_detailed_student_analytics(
    user_id: str,
    timeframe: str = "month",
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed analytics for a student with time-based breakdowns.

    - **user_id**: Student identifier
    - **timeframe**: Analysis period (week, month, quarter)
    """
    try:
        # Check permissions
        if user_id != current_user["id"] and current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to view this student's analytics")

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
            "user_id": user_id,
            "last_accessed": {"$gte": start_date}
        })

        # Group by day
        daily_stats = {}
        for progress in progress_data:
            date = progress.get("last_accessed", progress.get("created_at", now)).date()
            if date not in daily_stats:
                daily_stats[date] = {
                    "time_spent": 0,
                    "lessons_completed": 0,
                    "courses_accessed": 0
                }

            daily_stats[date]["time_spent"] += progress.get("time_spent", 0)
            daily_stats[date]["courses_accessed"] += 1

            lessons_progress = progress.get("lessons_progress", [])
            daily_stats[date]["lessons_completed"] += len([
                lp for lp in lessons_progress
                if lp.get("completed") and lp.get("completed_at", datetime.min.replace(tzinfo=timezone.utc)) >= start_date
            ])

        # Get submission data in timeframe
        submissions_db = DatabaseOperations("submissions")
        submissions = await submissions_db.find_many({
            "user_id": user_id,
            "created_at": {"$gte": start_date}
        })

        # Calculate performance trends
        total_time = sum(stats["time_spent"] for stats in daily_stats.values())
        total_lessons = sum(stats["lessons_completed"] for stats in daily_stats.values())
        avg_daily_time = total_time / max(len(daily_stats), 1)

        return {
            "user_id": user_id,
            "timeframe": timeframe,
            "total_study_time": total_time,
            "total_lessons_completed": total_lessons,
            "total_submissions": len(submissions),
            "average_daily_time": round(avg_daily_time, 1),
            "active_days": len(daily_stats),
            "consistency_score": round((len(daily_stats) / max((now - start_date).days, 1)) * 100, 1),
            "daily_stats": [
                {
                    "date": date.isoformat(),
                    "time_spent": stats["time_spent"],
                    "lessons_completed": stats["lessons_completed"],
                    "courses_accessed": stats["courses_accessed"]
                }
                for date, stats in daily_stats.items()
            ]
        }

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get detailed student analytics", extra={
            "user_id": user_id,
            "timeframe": timeframe,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve detailed analytics")

@router.get("/students/performance")
async def get_students_performance(
    course_id: str = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """
    Get performance overview for multiple students (instructor only).

    - **course_id**: Filter by specific course (optional)
    - **limit**: Maximum number of students to return
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only instructors can view student performance data")

        # Get progress data
        progress_db = DatabaseOperations("course_progress")
        if course_id:
            progress_data = await progress_db.find_many({
                "course_id": course_id
            })
        else:
            # Get all progress data (would need pagination in production)
            progress_data = await progress_db.find_many({})

        # Group by user
        user_stats = {}
        for progress in progress_data:
            user_id = progress["user_id"]
            if user_id not in user_stats:
                user_stats[user_id] = {
                    "courses_enrolled": 0,
                    "courses_completed": 0,
                    "total_progress": 0,
                    "total_time": 0,
                    "lessons_completed": 0
                }

            user_stats[user_id]["courses_enrolled"] += 1
            if progress.get("completed"):
                user_stats[user_id]["courses_completed"] += 1

            user_stats[user_id]["total_progress"] += progress.get("overall_progress", 0)
            user_stats[user_id]["total_time"] += progress.get("time_spent", 0)

            lessons_progress = progress.get("lessons_progress", [])
            user_stats[user_id]["lessons_completed"] += len([
                lp for lp in lessons_progress if lp.get("completed")
            ])

        # Calculate averages and sort
        performance_list = []
        for user_id, stats in user_stats.items():
            avg_progress = stats["total_progress"] / max(stats["courses_enrolled"], 1)
            completion_rate = (stats["courses_completed"] / max(stats["courses_enrolled"], 1)) * 100

            performance_list.append({
                "user_id": user_id,
                "courses_enrolled": stats["courses_enrolled"],
                "courses_completed": stats["courses_completed"],
                "completion_rate": round(completion_rate, 1),
                "average_progress": round(avg_progress, 1),
                "total_time_spent": stats["total_time"],
                "lessons_completed": stats["lessons_completed"]
            })

        # Sort by average progress (descending)
        performance_list.sort(key=lambda x: x["average_progress"], reverse=True)

        return {
            "total_students": len(performance_list),
            "course_filter": course_id,
            "students": performance_list[:limit]
        }

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get students performance", extra={
            "course_id": course_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve students performance")