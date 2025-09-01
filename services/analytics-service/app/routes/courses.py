"""
Course analytics routes for Analytics Service
"""
from fastapi import APIRouter, Depends
from typing import Optional
from datetime import datetime, timezone

from shared.common.errors import NotFoundError, AuthorizationError
from shared.common.logging import get_logger

from utils.analytics_utils import get_current_user, require_role
from services.analytics_service import analytics_service
from models import (
    CourseAnalytics, AnalyticsDashboard
)

logger = get_logger("analytics-service")
router = APIRouter()

@router.get("/course/{course_id}", response_model=CourseAnalytics)
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

        logger.info("Getting course analytics", extra={
            "course_id": course_id,
            "requested_by": current_user["id"]
        })

        # Use service layer
        analytics = await analytics_service.get_course_analytics(course_id)

        logger.info("Course analytics retrieved", extra={
            "course_id": course_id,
            "enrollments": analytics.enrollment_count,
            "completion_rate": analytics.completion_rate
        })

        return analytics

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get course analytics", extra={
            "course_id": course_id,
            "error": str(e)
        })
        from fastapi import HTTPException
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

        logger.info("Getting detailed course analytics", extra={
            "course_id": course_id,
            "timeframe": timeframe,
            "requested_by": current_user["id"]
        })

        # Use service layer - Note: This would need to be implemented in the service
        # For now, return basic analytics
        analytics = await analytics_service.get_course_analytics(course_id)

        # Mock detailed data structure
        detailed_data = {
            "course_id": course_id,
            "timeframe": timeframe,
            "total_active_users": analytics.active_students,
            "daily_stats": [],  # Would be populated by service layer
            "lesson_completion": [],  # Would be populated by service layer
            "generated_at": analytics.last_updated
        }

        logger.info("Detailed course analytics retrieved", extra={
            "course_id": course_id,
            "timeframe": timeframe,
            "active_users": analytics.active_students
        })

        return detailed_data

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get detailed course analytics", extra={
            "course_id": course_id,
            "timeframe": timeframe,
            "error": str(e)
        })
        from fastapi import HTTPException
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

        logger.info("Getting courses overview", extra={
            "requested_by": current_user["id"],
            "user_role": current_user["role"]
        })

        # Use service layer - Note: This would need to be implemented in the service
        # For now, return basic overview structure
        overview_data = {
            "total_courses": 0,  # Would be calculated by service
            "published_courses": 0,
            "draft_courses": 0,
            "total_enrollments": 0,
            "total_completions": 0,
            "overall_completion_rate": 0.0,
            "avg_enrollments_per_course": 0.0,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        logger.info("Courses overview retrieved", extra={
            "requested_by": current_user["id"],
            "total_courses": overview_data["total_courses"]
        })

        return overview_data

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get courses overview", extra={"error": str(e)})
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to retrieve courses overview")