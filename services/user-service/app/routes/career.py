"""
Career development routes for User Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from shared.common.auth import get_current_user, require_admin
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

from services.user_service import user_service
from models import CareerProfileUpdate

logger = get_logger("user-service")
router = APIRouter()

@router.get("/career-profile")
async def get_career_profile(user: dict = Depends(get_current_user)):
    """
    Get user's career profile.

    Returns career goals, target industries, skills to develop, etc.
    """
    try:
        career_profile = await user_service.get_career_profile(user["id"])
        return career_profile.dict()

    except NotFoundError:
        # Create default career profile if not found
        profile_data = CareerProfileUpdate()  # Empty update creates default profile
        career_profile = await user_service.update_career_profile(user["id"], profile_data)
        return career_profile.dict()

    except Exception as e:
        logger.error("Failed to get career profile", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve career profile")

@router.put("/career-profile")
async def update_career_profile(career_data: CareerProfileUpdate, user: dict = Depends(get_current_user)):
    """
    Update user's career profile.

    - **career_goals**: List of career objectives
    - **target_industries**: Industries of interest
    - **target_roles**: Desired job roles
    - **skills_to_develop**: Skills to acquire
    - **resume_data**: Resume information
    - **linkedin_profile**: LinkedIn profile URL
    - **portfolio_url**: Portfolio website URL
    - **mentor_ids**: IDs of mentors
    - **mentee_ids**: IDs of mentees
    """
    try:
        updated_profile = await user_service.update_career_profile(user["id"], career_data)

        logger.info("Career profile updated", extra={
            "user_id": user["id"]
        })

        return {"status": "updated", "message": "Career profile updated successfully"}

    except ValidationError:
        raise
    except Exception as e:
        logger.error("Failed to update career profile", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to update career profile")

@router.get("/study-plan")
async def get_study_plan(user: dict = Depends(get_current_user)):
    """
    Get personalized study plan based on real data.

    Analyzes user's enrolled courses, progress, and learning patterns
    to generate a customized study schedule.
    """
    try:
        study_plan = await user_service.get_study_plan(user["id"])
        return study_plan.dict()

    except Exception as e:
        logger.error("Failed to generate study plan", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to generate study plan")

@router.get("/skill-gaps")
async def get_skill_gaps(user: dict = Depends(get_current_user)):
    """
    Analyze skill gaps based on real learning data.

    Evaluates user's performance, course history, and identifies areas for improvement.
    """
    try:
        skill_gaps = await user_service.get_skill_gaps(user["id"])
        return [gap.dict() for gap in skill_gaps]

    except Exception as e:
        logger.error("Failed to analyze skill gaps", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to analyze skill gaps")

@router.get("/career-readiness")
async def get_career_readiness(user: dict = Depends(get_current_user)):
    """
    Get career readiness assessment based on real data.

    Evaluates user's learning progress, skills, and career profile
    to provide comprehensive career readiness metrics.
    """
    try:
        career_readiness = await user_service.get_career_readiness(user["id"])
        return career_readiness.dict()

    except Exception as e:
        logger.error("Failed to assess career readiness", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to assess career readiness")