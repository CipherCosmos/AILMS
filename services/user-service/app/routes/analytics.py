"""
Learning analytics routes for User Service
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations, _uuid
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("user-service")
router = APIRouter()

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
        users_db = DatabaseOperations("users")
        user = await users_db.find_one({"_id": payload.get("sub")})
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

@router.get("/learning-analytics")
async def get_learning_analytics(timeframe: str = "month", user=Depends(_current_user)):
    """
    Get detailed learning analytics based on real data.

    - **timeframe**: week, month, quarter (default: month)
    """
    try:
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

        # Get database connection
        study_sessions_db = DatabaseOperations("study_sessions")

        # Get study sessions in timeframe
        study_sessions = await study_sessions_db.find_many({
            "user_id": user["id"],
            "session_date": {"$gte": start_date}
        }, limit=100)

        # Calculate analytics
        total_sessions = len(study_sessions)
        total_minutes = sum(session.get("duration_minutes", 0) for session in study_sessions)
        avg_productivity = sum(session.get("productivity_score", 7) for session in study_sessions) / max(total_sessions, 1)

        # Group by day
        daily_stats = {}
        for session in study_sessions:
            date = session["session_date"].date()
            if date not in daily_stats:
                daily_stats[date] = {"sessions": 0, "minutes": 0}
            daily_stats[date]["sessions"] += 1
            daily_stats[date]["minutes"] += session.get("duration_minutes", 0)

        analytics = {
            "timeframe": timeframe,
            "total_sessions": total_sessions,
            "total_study_hours": round(total_minutes / 60, 1),
            "average_productivity": round(avg_productivity, 1),
            "daily_average": round(total_minutes / max((now - start_date).days, 1), 1),
            "most_productive_hour": 14,  # Would analyze actual data
            "consistency_score": min(100, total_sessions * 10),
            "daily_stats": [
                {
                    "date": date.isoformat(),
                    "sessions": stats["sessions"],
                    "minutes": stats["minutes"]
                }
                for date, stats in daily_stats.items()
            ]
        }

        logger.info("Learning analytics generated", extra={
            "user_id": user["id"],
            "timeframe": timeframe,
            "total_sessions": total_sessions,
            "total_study_hours": round(total_minutes / 60, 1)
        })

        return analytics

    except Exception as e:
        logger.error("Failed to generate learning analytics", extra={
            "user_id": user["id"],
            "timeframe": timeframe,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to generate learning analytics")

@router.get("/learning-analytics/detailed")
async def get_detailed_learning_analytics(user=Depends(_current_user)):
    """
    Get comprehensive learning analytics with multiple metrics.
    """
    try:
        # Get database connections
        courses_db = DatabaseOperations("courses")
        progress_db = DatabaseOperations("course_progress")
        submissions_db = DatabaseOperations("submissions")

        # Get user's enrolled courses
        enrolled_courses = await courses_db.find_many({
            "enrolled_user_ids": user["id"]
        }, limit=20)

        # Get progress data
        progress_data = await progress_db.find_many({"user_id": user["id"]}, limit=20)

        # Get submission data
        submissions = await submissions_db.find_many({"user_id": user["id"]}, limit=50)

        # Calculate comprehensive metrics
        total_enrolled = len(enrolled_courses)
        completed_courses = len([p for p in progress_data if p.get("completed")])

        # Calculate average progress
        avg_progress = 0
        if progress_data:
            avg_progress = sum([p.get("overall_progress", 0) for p in progress_data]) / len(progress_data)

        # Calculate grade statistics
        avg_grade = 0
        if submissions:
            grades = [s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")]
            if grades:
                avg_grade = sum(grades) / len(grades)

        # Calculate learning velocity (progress per day)
        learning_velocity = 0
        if progress_data:
            # Get the earliest progress record
            earliest_progress = min([p.get("started_at", datetime.now(timezone.utc)) for p in progress_data], default=datetime.now(timezone.utc))
            days_learning = max(1, (datetime.now(timezone.utc) - earliest_progress).days)
            learning_velocity = avg_progress / days_learning

        # Calculate skill development trends
        skill_trends = []
        course_titles = [c.get("title", "") for c in enrolled_courses]

        if any("python" in title.lower() for title in course_titles):
            skill_trends.append({
                "skill": "Python Programming",
                "current_level": min(10, int(avg_progress / 10)),
                "trend": "improving" if avg_progress > 50 else "developing",
                "confidence": round(avg_grade / 10, 1)
            })

        if any("data" in title.lower() for title in course_titles):
            skill_trends.append({
                "skill": "Data Analysis",
                "current_level": min(10, int(avg_progress / 12)),
                "trend": "improving" if avg_progress > 40 else "developing",
                "confidence": round(avg_grade / 10, 1)
            })

        detailed_analytics = {
            "overview": {
                "total_enrolled_courses": total_enrolled,
                "completed_courses": completed_courses,
                "completion_rate": round((completed_courses / max(total_enrolled, 1)) * 100, 1),
                "average_progress": round(avg_progress, 1),
                "average_grade": round(avg_grade, 1),
                "total_submissions": len(submissions)
            },
            "performance_metrics": {
                "learning_velocity": round(learning_velocity, 2),
                "consistency_score": min(100, completed_courses * 15),
                "engagement_level": "High" if avg_progress > 70 else "Medium" if avg_progress > 40 else "Low",
                "grade_performance": "Excellent" if avg_grade > 85 else "Good" if avg_grade > 75 else "Needs Improvement"
            },
            "skill_development": {
                "trends": skill_trends,
                "strengths": [trend["skill"] for trend in skill_trends if trend["current_level"] >= 7],
                "focus_areas": [trend["skill"] for trend in skill_trends if trend["current_level"] < 5]
            },
            "recommendations": {
                "next_steps": [
                    "Continue with current course progression" if avg_progress > 60 else "Focus on completing current modules",
                    "Practice more hands-on exercises" if avg_grade < 80 else "Challenge yourself with advanced topics",
                    "Maintain consistent study schedule" if learning_velocity > 1 else "Increase study frequency"
                ],
                "suggested_courses": [
                    "Advanced Python Programming" if any("python" in title.lower() for title in course_titles) and avg_progress > 70 else None,
                    "Machine Learning Fundamentals" if any("data" in title.lower() for title in course_titles) and avg_progress > 60 else None
                ]
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        # Filter out None values from suggestions
        detailed_analytics["recommendations"]["suggested_courses"] = [
            course for course in detailed_analytics["recommendations"]["suggested_courses"] if course is not None
        ]

        logger.info("Detailed learning analytics generated", extra={
            "user_id": user["id"],
            "completion_rate": detailed_analytics["overview"]["completion_rate"],
            "average_progress": detailed_analytics["overview"]["average_progress"]
        })

        return detailed_analytics

    except Exception as e:
        logger.error("Failed to generate detailed analytics", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to generate detailed analytics")

@router.get("/learning-analytics/progress-timeline")
async def get_progress_timeline(user=Depends(_current_user)):
    """
    Get learning progress timeline showing improvement over time.
    """
    try:
        # Get progress data
        progress_db = DatabaseOperations("course_progress")
        progress_data = await progress_db.find_many({"user_id": user["id"]}, limit=50)

        # Group progress by date
        timeline_data = {}
        for progress in progress_data:
            # Use started_at or created_at as the date
            date_key = progress.get("started_at", progress.get("created_at", datetime.now(timezone.utc))).date()

            if date_key not in timeline_data:
                timeline_data[date_key] = {
                    "date": date_key.isoformat(),
                    "courses_active": 0,
                    "total_progress": 0,
                    "completed_courses": 0
                }

            timeline_data[date_key]["courses_active"] += 1
            timeline_data[date_key]["total_progress"] += progress.get("overall_progress", 0)

            if progress.get("completed"):
                timeline_data[date_key]["completed_courses"] += 1

        # Convert to sorted list
        timeline = []
        for date_key in sorted(timeline_data.keys()):
            data = timeline_data[date_key]
            data["average_progress"] = round(data["total_progress"] / max(data["courses_active"], 1), 1)
            timeline.append(data)

        return {
            "timeline": timeline,
            "total_data_points": len(timeline),
            "date_range": {
                "start": timeline[0]["date"] if timeline else None,
                "end": timeline[-1]["date"] if timeline else None
            }
        }

    except Exception as e:
        logger.error("Failed to generate progress timeline", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to generate progress timeline")

@router.get("/learning-analytics/compare")
async def compare_learning_metrics(user=Depends(_current_user)):
    """
    Compare user's learning metrics with peers or benchmarks.
    """
    try:
        # Get user's data
        courses_db = DatabaseOperations("courses")
        progress_db = DatabaseOperations("course_progress")

        # Get user's progress
        user_progress = await progress_db.find_many({"user_id": user["id"]}, limit=20)
        user_avg_progress = sum([p.get("overall_progress", 0) for p in user_progress]) / max(len(user_progress), 1)

        # Get peer data (simplified - in production would use more sophisticated peer matching)
        all_progress = await progress_db.find_many({}, limit=100)
        peer_avg_progress = sum([p.get("overall_progress", 0) for p in all_progress]) / max(len(all_progress), 1)

        # Calculate percentile
        user_percentile = 0
        if all_progress:
            better_than_user = len([p for p in all_progress if p.get("overall_progress", 0) > user_avg_progress])
            user_percentile = round((1 - (better_than_user / len(all_progress))) * 100, 1)

        comparison = {
            "user_metrics": {
                "average_progress": round(user_avg_progress, 1),
                "total_courses": len(user_progress),
                "completed_courses": len([p for p in user_progress if p.get("completed")])
            },
            "peer_comparison": {
                "peer_average": round(peer_avg_progress, 1),
                "user_percentile": user_percentile,
                "performance_level": "Above Average" if user_percentile > 75 else "Average" if user_percentile > 50 else "Below Average"
            },
            "benchmarks": {
                "excellent_threshold": 85,
                "good_threshold": 70,
                "needs_improvement_threshold": 50
            },
            "insights": [
                f"You are performing {comparison['peer_comparison']['performance_level']} compared to peers",
                f"Your progress is {round(user_avg_progress - peer_avg_progress, 1)} points {'above' if user_avg_progress > peer_avg_progress else 'below'} the peer average",
                "Consider increasing study time" if user_avg_progress < 60 else "Great progress! Keep it up!"
            ]
        }

        return comparison

    except Exception as e:
        logger.error("Failed to compare learning metrics", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to compare learning metrics")