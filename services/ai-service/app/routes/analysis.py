"""
Performance analysis routes for AI Service
"""
from fastapi import APIRouter, Depends
from typing import Optional

from shared.common.errors import ValidationError, AuthorizationError
from shared.common.logging import get_logger

from utils.ai_utils import get_current_user, require_role
from services.ai_service import ai_service
from models import (
    PerformanceAnalysisRequest, PerformanceAnalysisResponse,
    CoursePerformanceAnalysisRequest, CoursePerformanceAnalysisResponse,
    PerformancePredictionRequest, PerformancePredictionResponse
)

logger = get_logger("ai-service")
router = APIRouter()

@router.post("/analyze-performance", response_model=PerformanceAnalysisResponse)
async def analyze_performance(request: PerformanceAnalysisRequest, user=Depends(get_current_user)):
    """
    Analyze student performance using AI.

    - **user_id**: Student user ID to analyze
    - **course_id**: Specific course to analyze (optional)
    - **timeframe**: Analysis timeframe (optional)
    """
    try:
        # Check permissions (admin, instructor, or analyzing own performance)
        if user["id"] != request.user_id and user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to analyze this user's performance")

        logger.info("Starting performance analysis", extra={
            "target_user_id": request.user_id,
            "course_id": request.course_id,
            "timeframe": request.timeframe,
            "requested_by": user["id"]
        })

        # Use service layer
        result = await ai_service.analyze_performance(
            user_id=request.user_id,
            course_id=request.course_id,
            timeframe=request.timeframe,
            requested_by=user["id"]
        )

        logger.info("Performance analysis completed", extra={
            "target_user_id": request.user_id,
            "performance_level": result.performance_level,
            "requested_by": user["id"]
        })

        return result

    except (AuthorizationError, ValidationError):
        raise
    except Exception as e:
        logger.error("Performance analysis failed", extra={
            "target_user_id": request.user_id,
            "requested_by": user["id"],
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, f"Performance analysis failed: {str(e)}")

@router.post("/analyze-course-performance", response_model=CoursePerformanceAnalysisResponse)
async def analyze_course_performance(request: CoursePerformanceAnalysisRequest, user=Depends(get_current_user)):
    """
    Analyze performance for a specific course using AI.

    - **course_id**: Course to analyze
    - **include_individual_students**: Whether to include individual student analysis
    """
    try:
        # Check permissions
        require_role(user, ["admin", "instructor"])

        logger.info("Starting course performance analysis", extra={
            "course_id": request.course_id,
            "include_individual_students": request.include_individual_students,
            "requested_by": user["id"]
        })

        # Use service layer
        result = await ai_service.analyze_course_performance(
            course_id=request.course_id,
            include_individual_students=request.include_individual_students or False,
            requested_by=user["id"]
        )

        logger.info("Course performance analysis completed", extra={
            "course_id": request.course_id,
            "requested_by": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Course performance analysis failed", extra={
            "course_id": request.course_id,
            "requested_by": user["id"],
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Course performance analysis failed")

@router.post("/predict-performance", response_model=PerformancePredictionResponse)
async def predict_performance(request: PerformancePredictionRequest, user=Depends(get_current_user)):
    """
    Predict student performance using AI.

    - **user_id**: Student to predict performance for
    - **course_id**: Course to predict performance in
    """
    try:
        # Check permissions
        if user["id"] != request.user_id and user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to predict this user's performance")

        logger.info("Starting performance prediction", extra={
            "target_user_id": request.user_id,
            "course_id": request.course_id,
            "requested_by": user["id"]
        })

        # Use service layer
        result = await ai_service.predict_performance(
            user_id=request.user_id,
            course_id=request.course_id,
            requested_by=user["id"]
        )

        logger.info("Performance prediction completed", extra={
            "target_user_id": request.user_id,
            "course_id": request.course_id,
            "requested_by": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Performance prediction failed", extra={
            "target_user_id": request.user_id,
            "course_id": request.course_id,
            "requested_by": user["id"],
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Performance prediction failed")