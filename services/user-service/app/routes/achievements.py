"""
Achievements system routes for User Service
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

from shared.common.auth import get_current_user, require_admin
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

from ..services.user_service import user_service

logger = get_logger("user-service")
router = APIRouter()

@router.get("/achievements")
async def get_achievements(user: dict = Depends(get_current_user)):
    """
    Get user's achievements based on real progress.

    Returns all achievements earned by the user, automatically
    generating achievements based on their learning progress.
    """
    try:
        achievements = await user_service.get_user_achievements(user["id"])
        return [achievement.dict() for achievement in achievements]

    except Exception as e:
        logger.error("Failed to get achievements", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve achievements")


@router.get("/achievements/{achievement_id}")
async def get_achievement(achievement_id: str, user: dict = Depends(get_current_user)):
    """
    Get a specific achievement.

    - **achievement_id**: Achievement identifier
    """
    try:
        # Get all user achievements and find the specific one
        achievements = await user_service.get_user_achievements(user["id"])
        achievement = next((a for a in achievements if a.id == achievement_id), None)

        if not achievement:
            raise NotFoundError("Achievement", achievement_id)

        return achievement.dict()

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get achievement", extra={
            "achievement_id": achievement_id,
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve achievement")

@router.get("/achievements/stats")
async def get_achievement_stats(user: dict = Depends(get_current_user)):
    """
    Get achievement statistics for the user.
    """
    try:
        achievements = await user_service.get_user_achievements(user["id"])

        if not achievements:
            return {
                "total_achievements": 0,
                "total_points": 0,
                "categories": {},
                "recent_achievements": [],
                "next_milestones": [
                    {"name": "First Steps", "description": "Complete your first course", "points": 100},
                    {"name": "Dedicated Learner", "description": "Complete 3 courses", "points": 300},
                    {"name": "Knowledge Seeker", "description": "Enroll in 10 courses", "points": 200}
                ]
            }

        # Calculate statistics
        total_points = sum([a.points or 0 for a in achievements])

        # Group by category
        categories = {}
        for achievement in achievements:
            category = achievement.category
            if category not in categories:
                categories[category] = 0
            categories[category] += 1

        # Get recent achievements (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_achievements = [
            a.dict() for a in achievements
            if a.earned_date > thirty_days_ago
        ]

        return {
            "total_achievements": len(achievements),
            "total_points": total_points,
            "categories": categories,
            "recent_achievements": recent_achievements[:5],  # Last 5 achievements
            "next_milestones": [
                {"name": "Dedicated Learner", "description": "Complete 3 more courses", "points": 300},
                {"name": "Knowledge Seeker", "description": "Enroll in 10 courses", "points": 200},
                {"name": "Quick Study", "description": "Complete 5 courses", "points": 500}
            ],
            "achievement_level": "Expert" if total_points > 1000 else "Advanced" if total_points > 500 else "Intermediate" if total_points > 200 else "Beginner"
        }

    except Exception as e:
        logger.error("Failed to get achievement stats", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve achievement statistics")

@router.get("/leaderboard/achievements")
async def get_achievement_leaderboard(limit: int = 10, user: dict = Depends(get_current_user)):
    """
    Get achievement leaderboard.

    - **limit**: Maximum number of users to return
    """
    try:
        # For now, return simplified leaderboard since aggregation
        # would need to be implemented in the service layer
        return {
            "leaderboard": [
                {
                    "rank": 1,
                    "user_id": "sample_user_1",
                    "name": "Top Learner",
                    "total_achievements": 15,
                    "total_points": 2500
                },
                {
                    "rank": 2,
                    "user_id": "sample_user_2",
                    "name": "Knowledge Seeker",
                    "total_achievements": 12,
                    "total_points": 2100
                }
            ],
            "user_rank": 5,  # Would need to calculate user's specific rank
            "total_participants": 50
        }

    except Exception as e:
        logger.error("Failed to get achievement leaderboard", extra={"error": str(e)})
        raise HTTPException(500, "Failed to retrieve achievement leaderboard")

@router.post("/achievements/check")
async def check_new_achievements(user: dict = Depends(get_current_user)):
    """
    Check for new achievements based on recent progress.
    """
    try:
        # Generate achievements (this will create new ones if progress allows)
        new_achievements = await user_service.generate_achievements(user["id"])

        # Get current achievements count
        current_achievements = await user_service.get_user_achievements(user["id"])

        if len(new_achievements) > len(current_achievements):
            new_earned = len(new_achievements) - len(current_achievements)
            return {
                "new_achievements_earned": new_earned,
                "total_achievements": len(new_achievements),
                "message": f"Congratulations! You earned {new_earned} new achievement(s)!"
            }
        else:
            return {
                "new_achievements_earned": 0,
                "total_achievements": len(current_achievements),
                "message": "Keep learning to unlock new achievements!"
            }

    except Exception as e:
        logger.error("Failed to check new achievements", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to check for new achievements")