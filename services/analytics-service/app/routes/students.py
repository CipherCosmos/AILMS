"""
Student analytics routes for Analytics Service
"""
from fastapi import APIRouter, Depends
from typing import Optional

from shared.common.errors import NotFoundError, AuthorizationError
from shared.common.logging import get_logger

from utils.analytics_utils import get_current_user, require_role
from services.analytics_service import analytics_service
from models import (
    StudentAnalytics
)

logger = get_logger("analytics-service")
router = APIRouter()

@router.get("/student/{user_id}", response_model=StudentAnalytics)
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

        logger.info("Getting student analytics", extra={
            "user_id": user_id,
            "requested_by": current_user["id"]
        })

        # Use service layer
        analytics = await analytics_service.get_student_analytics(user_id)

        logger.info("Student analytics retrieved", extra={
            "user_id": user_id,
            "courses_enrolled": analytics.courses_enrolled,
            "courses_completed": analytics.courses_completed
        })

        return analytics

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get student analytics", extra={
            "user_id": user_id,
            "error": str(e)
        })
        from fastapi import HTTPException
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

        logger.info("Getting detailed student analytics", extra={
            "user_id": user_id,
            "timeframe": timeframe,
            "requested_by": current_user["id"]
        })

        # Use service layer - Note: This would need to be implemented in the service
        # For now, return basic analytics structure
        analytics = await analytics_service.get_student_analytics(user_id)

        detailed_data = {
            "user_id": user_id,
            "timeframe": timeframe,
            "total_study_time": analytics.total_study_hours,
            "total_lessons_completed": 0,  # Would be calculated by service
            "total_submissions": 0,  # Would be calculated by service
            "average_daily_time": 0.0,  # Would be calculated by service
            "active_days": 0,  # Would be calculated by service
            "consistency_score": 0.0,  # Would be calculated by service
            "daily_stats": [],  # Would be populated by service
            "generated_at": analytics.last_updated
        }

        logger.info("Detailed student analytics retrieved", extra={
            "user_id": user_id,
            "timeframe": timeframe,
            "total_study_hours": analytics.total_study_hours
        })

        return detailed_data

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get detailed student analytics", extra={
            "user_id": user_id,
            "timeframe": timeframe,
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to retrieve detailed analytics")

@router.get("/students/performance")
async def get_students_performance(
    course_id: Optional[str] = None,
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

        logger.info("Getting students performance overview", extra={
            "course_id": course_id,
            "limit": limit,
            "requested_by": current_user["id"]
        })

        # Use service layer - Note: This would need to be implemented in the service
        # For now, return basic performance structure
        performance_data = {
            "total_students": 0,  # Would be calculated by service
            "course_filter": course_id,
            "students": [],  # Would be populated by service
            "generated_at": "2025-09-01T13:15:00Z"  # Would be current timestamp
        }

        logger.info("Students performance overview retrieved", extra={
            "course_id": course_id,
            "total_students": performance_data["total_students"]
        })

        return performance_data

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get students performance", extra={
            "course_id": course_id,
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to retrieve students performance")