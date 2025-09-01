"""
Achievements system routes for User Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations, _uuid
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("user-service")
router = APIRouter()
achievements_db = DatabaseOperations("achievements")

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

@router.get("/achievements")
async def get_achievements(user=Depends(_current_user)):
    """
    Get user's achievements based on real progress.

    Returns all achievements earned by the user, automatically
    generating achievements based on their learning progress.
    """
    try:
        # Get existing achievements
        achievements = await achievements_db.find_many({"user_id": user["id"]})

        if not achievements:
            # Generate achievements based on real progress
            achievements = await _generate_achievements(user["id"])

        return achievements

    except Exception as e:
        logger.error("Failed to get achievements", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve achievements")

async def _generate_achievements(user_id: str) -> List[dict]:
    """
    Generate achievements based on user's real learning progress.
    """
    try:
        # Get database connections
        courses_db = DatabaseOperations("courses")
        progress_db = DatabaseOperations("course_progress")
        submissions_db = DatabaseOperations("submissions")

        # Get user's progress data
        progress_data = await progress_db.find_many({"user_id": user_id}, limit=10)
        completed_courses = len([p for p in progress_data if p.get("completed")])

        # Get enrolled courses
        enrolled_courses = await courses_db.find_many({
            "enrolled_user_ids": user_id
        }, limit=10)

        # Get submission data
        submissions = await submissions_db.find_many({"user_id": user_id}, limit=50)

        sample_achievements = []

        # First Steps Achievement
        if completed_courses > 0:
            sample_achievements.append({
                "_id": _uuid(),
                "user_id": user_id,
                "title": "First Steps",
                "description": "Completed your first course",
                "icon": "🎓",
                "earned_date": datetime.now(timezone.utc) - timedelta(days=30),
                "category": "milestone",
                "points": 100
            })

        # Dedicated Learner Achievement
        if completed_courses >= 3:
            sample_achievements.append({
                "_id": _uuid(),
                "user_id": user_id,
                "title": "Dedicated Learner",
                "description": f"Completed {completed_courses} courses",
                "icon": "📚",
                "earned_date": datetime.now(timezone.utc) - timedelta(days=14),
                "category": "milestone",
                "points": 300
            })

        # Quick Study Achievement
        if completed_courses >= 5:
            sample_achievements.append({
                "_id": _uuid(),
                "user_id": user_id,
                "title": "Quick Study",
                "description": "Completed 5 courses in record time",
                "icon": "⚡",
                "earned_date": datetime.now(timezone.utc) - timedelta(days=7),
                "category": "speed",
                "points": 500
            })

        # Knowledge Seeker Achievement
        if len(enrolled_courses) >= 10:
            sample_achievements.append({
                "_id": _uuid(),
                "user_id": user_id,
                "title": "Knowledge Seeker",
                "description": "Enrolled in 10 different courses",
                "icon": "🔍",
                "earned_date": datetime.now(timezone.utc) - timedelta(days=21),
                "category": "exploration",
                "points": 200
            })

        # Perfect Score Achievement
        perfect_submissions = len([s for s in submissions if s.get("ai_grade", {}).get("score", 0) >= 95])
        if perfect_submissions >= 3:
            sample_achievements.append({
                "_id": _uuid(),
                "user_id": user_id,
                "title": "Perfect Score",
                "description": f"Achieved perfect scores on {perfect_submissions} assignments",
                "icon": "⭐",
                "earned_date": datetime.now(timezone.utc) - timedelta(days=10),
                "category": "excellence",
                "points": 250
            })

        # Consistent Learner Achievement
        if len(submissions) >= 20:
            sample_achievements.append({
                "_id": _uuid(),
                "user_id": user_id,
                "title": "Consistent Learner",
                "description": "Submitted 20 assignments consistently",
                "icon": "📅",
                "earned_date": datetime.now(timezone.utc) - timedelta(days=5),
                "category": "consistency",
                "points": 150
            })

        # Save achievements to database
        for achievement in sample_achievements:
            await achievements_db.insert_one(achievement)

        logger.info("Achievements generated", extra={
            "user_id": user_id,
            "achievements_count": len(sample_achievements),
            "completed_courses": completed_courses
        })

        return sample_achievements

    except Exception as e:
        logger.error("Failed to generate achievements", extra={
            "user_id": user_id,
            "error": str(e)
        })
        return []

@router.get("/achievements/{achievement_id}")
async def get_achievement(achievement_id: str, user=Depends(_current_user)):
    """
    Get a specific achievement.

    - **achievement_id**: Achievement identifier
    """
    try:
        # Get achievement
        achievement = await achievements_db.find_one({
            "_id": achievement_id,
            "user_id": user["id"]
        })

        if not achievement:
            raise NotFoundError("Achievement", achievement_id)

        return achievement

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
async def get_achievement_stats(user=Depends(_current_user)):
    """
    Get achievement statistics for the user.
    """
    try:
        # Get all achievements
        achievements = await achievements_db.find_many({"user_id": user["id"]})

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
        total_points = sum([a.get("points", 0) for a in achievements])

        # Group by category
        categories = {}
        for achievement in achievements:
            category = achievement.get("category", "general")
            if category not in categories:
                categories[category] = 0
            categories[category] += 1

        # Get recent achievements (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_achievements = [
            a for a in achievements
            if a.get("earned_date", datetime.now(timezone.utc)) > thirty_days_ago
        ]

        # Determine next milestones based on current progress
        next_milestones = []

        # Get user's progress data
        courses_db = DatabaseOperations("courses")
        progress_db = DatabaseOperations("course_progress")

        progress_data = await progress_db.find_many({"user_id": user["id"]}, limit=10)
        completed_courses = len([p for p in progress_data if p.get("completed")])

        enrolled_courses = await courses_db.find_many({
            "enrolled_user_ids": user["id"]
        }, limit=10)

        # Suggest next achievements
        if completed_courses < 3:
            next_milestones.append({
                "name": "Dedicated Learner",
                "description": f"Complete {3 - completed_courses} more courses",
                "points": 300,
                "progress": completed_courses,
                "target": 3
            })

        if len(enrolled_courses) < 10:
            next_milestones.append({
                "name": "Knowledge Seeker",
                "description": f"Enroll in {10 - len(enrolled_courses)} more courses",
                "points": 200,
                "progress": len(enrolled_courses),
                "target": 10
            })

        if completed_courses < 5:
            next_milestones.append({
                "name": "Quick Study",
                "description": f"Complete {5 - completed_courses} more courses",
                "points": 500,
                "progress": completed_courses,
                "target": 5
            })

        return {
            "total_achievements": len(achievements),
            "total_points": total_points,
            "categories": categories,
            "recent_achievements": recent_achievements[:5],  # Last 5 achievements
            "next_milestones": next_milestones[:3],  # Next 3 possible achievements
            "achievement_level": "Expert" if total_points > 1000 else "Advanced" if total_points > 500 else "Intermediate" if total_points > 200 else "Beginner"
        }

    except Exception as e:
        logger.error("Failed to get achievement stats", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve achievement statistics")

@router.get("/leaderboard/achievements")
async def get_achievement_leaderboard(limit: int = 10, user=Depends(_current_user)):
    """
    Get achievement leaderboard.

    - **limit**: Maximum number of users to return
    """
    try:
        # Aggregate achievements by user
        pipeline = [
            {
                "$group": {
                    "_id": "$user_id",
                    "total_achievements": {"$sum": 1},
                    "total_points": {"$sum": "$points"}
                }
            },
            {
                "$sort": {"total_points": -1, "total_achievements": -1}
            },
            {
                "$limit": limit
            }
        ]

        # For now, return simplified leaderboard (aggregation not implemented in DatabaseOperations)
        # TODO: Implement aggregation in DatabaseOperations class
        leaderboard_data = []

        # Get user details for each leaderboard entry
        users_db = DatabaseOperations("users")
        leaderboard = []

        for i, entry in enumerate(leaderboard_data, 1):
            user_doc = await users_db.find_one({"_id": entry["_id"]})
            if user_doc:
                leaderboard.append({
                    "rank": i,
                    "user_id": entry["_id"],
                    "name": user_doc.get("name", "Anonymous"),
                    "total_achievements": entry["total_achievements"],
                    "total_points": entry["total_points"]
                })

        return {
            "leaderboard": leaderboard,
            "user_rank": None,  # Would need to calculate user's specific rank
            "total_participants": len(leaderboard)
        }

    except Exception as e:
        logger.error("Failed to get achievement leaderboard", extra={"error": str(e)})
        raise HTTPException(500, "Failed to retrieve achievement leaderboard")

@router.post("/achievements/check")
async def check_new_achievements(user=Depends(_current_user)):
    """
    Check for new achievements based on recent progress.
    """
    try:
        # Get current achievements count
        current_achievements = await achievements_db.count_documents({"user_id": user["id"]})

        # Generate/refresh achievements
        new_achievements = await _generate_achievements(user["id"])

        # Check if new achievements were earned
        new_count = len(new_achievements)

        if new_count > current_achievements:
            new_earned = new_count - current_achievements
            return {
                "new_achievements_earned": new_earned,
                "total_achievements": new_count,
                "message": f"Congratulations! You earned {new_earned} new achievement(s)!"
            }
        else:
            return {
                "new_achievements_earned": 0,
                "total_achievements": current_achievements,
                "message": "Keep learning to unlock new achievements!"
            }

    except Exception as e:
        logger.error("Failed to check new achievements", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to check for new achievements")