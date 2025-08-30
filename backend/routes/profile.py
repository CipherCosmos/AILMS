from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional
from datetime import datetime, timedelta
from database import get_database, get_fs_bucket, _uuid
from auth import _current_user
from models import UserProfile, Achievement, LearningStreak, UserPreferences
from config import settings
from bson import ObjectId
import json

# AI integrations
try:
    import google.generativeai as genai
except Exception:
    genai = None

def _get_ai():
    if genai is None:
        raise HTTPException(status_code=500, detail="AI dependency not installed. Please install google-generativeai.")
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="No AI key configured. Set GEMINI_API_KEY in backend/.env")
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(settings.default_llm_model)

def _safe_json_extract(text: str):
    import json
    if not isinstance(text, str):
        text = str(text)
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        import re
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    raise ValueError("Could not parse JSON from AI response")

profile_router = APIRouter()

# Profile Management Routes
@profile_router.get("/profile")
async def get_user_profile(user=Depends(_current_user)):
    """Get current user's profile"""
    db = get_database()
    profile = await db.user_profiles.find_one({"user_id": user["id"]})

    if not profile:
        # Create default profile
        default_profile = UserProfile(user_id=user["id"])
        await db.user_profiles.insert_one(default_profile.dict())
        return default_profile.dict()

    return profile


@profile_router.put("/profile")
async def update_user_profile(profile_data: dict, user=Depends(_current_user)):
    """Update user profile"""
    db = get_database()

    # Validate profile data
    allowed_fields = [
        "bio", "location", "website", "social_links", "skills",
        "interests", "learning_goals", "preferred_learning_style",
        "timezone", "language", "notifications_enabled", "privacy_settings"
    ]

    update_data = {k: v for k, v in profile_data.items() if k in allowed_fields}
    update_data["updated_at"] = datetime.utcnow()

    await db.user_profiles.update_one(
        {"user_id": user["id"]},
        {"$set": update_data},
        upsert=True
    )

    return {"status": "updated", "message": "Profile updated successfully"}


@profile_router.post("/profile/avatar")
async def upload_avatar(file: UploadFile = File(...), user=Depends(_current_user)):
    """Upload user avatar"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    db = get_database()
    fs_bucket = get_fs_bucket()

    # Delete old avatar if exists
    profile = await db.user_profiles.find_one({"user_id": user["id"]})
    if profile and profile.get("avatar_file_id"):
        try:
            await fs_bucket.delete(profile["avatar_file_id"])
        except:
            pass  # Ignore if file doesn't exist

    # Upload new avatar
    file_id = _uuid()
    grid_in = fs_bucket.open_upload_stream_with_id(
        file_id,
        f"avatar_{user['id']}_{file.filename}",
        metadata={"user_id": user["id"], "content_type": file.content_type}
    )

    while True:
        chunk = await file.read(1024 * 512)
        if not chunk:
            break
        await grid_in.write(chunk)
    await grid_in.close()

    # Update profile with new avatar
    avatar_url = f"/api/files/{file_id}"
    await db.user_profiles.update_one(
        {"user_id": user["id"]},
        {"$set": {"avatar_url": avatar_url, "avatar_file_id": file_id}},
        upsert=True
    )

    return {"avatar_url": avatar_url, "message": "Avatar uploaded successfully"}


@profile_router.get("/achievements")
async def get_user_achievements(user=Depends(_current_user)):
    """Get user's achievements"""
    db = get_database()
    achievements = await db.achievements.find({"user_id": user["id"]}).sort("earned_at", -1).to_list(100)
    return achievements


@profile_router.get("/streak")
async def get_learning_streak(user=Depends(_current_user)):
    """Get user's learning streak"""
    db = get_database()
    streak = await db.learning_streaks.find_one({"user_id": user["id"]})

    if not streak:
        # Create default streak
        default_streak = LearningStreak(user_id=user["id"])
        await db.learning_streaks.insert_one(default_streak.dict())
        return default_streak.dict()

    return streak


@profile_router.post("/streak/update")
async def update_learning_streak(user=Depends(_current_user)):
    """Update learning streak based on activity"""
    db = get_database()
    today = datetime.utcnow().date()

    streak = await db.learning_streaks.find_one({"user_id": user["id"]})
    if not streak:
        streak = LearningStreak(user_id=user["id"])

    last_activity = streak.get("last_activity_date")
    if last_activity:
        last_activity_date = last_activity.date() if hasattr(last_activity, 'date') else datetime.fromisoformat(last_activity).date()
    else:
        last_activity_date = None

    if last_activity_date == today:
        # Already updated today
        return {"status": "already_updated", "streak": streak}

    if last_activity_date == today - timedelta(days=1):
        # Continue streak
        streak["current_streak"] += 1
        streak["longest_streak"] = max(streak["longest_streak"], streak["current_streak"])
    elif last_activity_date and last_activity_date < today - timedelta(days=1):
        # Streak broken
        streak["current_streak"] = 1
    else:
        # First activity or new streak
        streak["current_streak"] = 1
        if not streak.get("streak_start_date"):
            streak["streak_start_date"] = datetime.utcnow()

    streak["last_activity_date"] = datetime.utcnow()
    streak["total_study_days"] += 1

    await db.learning_streaks.update_one(
        {"user_id": user["id"]},
        {"$set": streak},
        upsert=True
    )

    return {"status": "updated", "streak": streak}


@profile_router.get("/preferences")
async def get_user_preferences(user=Depends(_current_user)):
    """Get user preferences"""
    db = get_database()
    preferences = await db.user_preferences.find_one({"user_id": user["id"]})

    if not preferences:
        # Create default preferences
        default_prefs = UserPreferences(user_id=user["id"])
        await db.user_preferences.insert_one(default_prefs.dict())
        return default_prefs.dict()

    # Convert ObjectId to string for JSON serialization
    if "_id" in preferences:
        preferences["_id"] = str(preferences["_id"])
    if "user_id" in preferences:
        preferences["user_id"] = str(preferences["user_id"])

    return preferences


@profile_router.put("/preferences")
async def update_user_preferences(preferences: dict, user=Depends(_current_user)):
    """Update user preferences"""
    db = get_database()

    # Validate preferences data
    allowed_fields = [
        "theme", "email_notifications", "study_reminders",
        "reminder_time", "dashboard_layout", "quick_actions", "accessibility"
    ]

    update_data = {k: v for k, v in preferences.items() if k in allowed_fields}

    await db.user_preferences.update_one(
        {"user_id": user["id"]},
        {"$set": update_data},
        upsert=True
    )

    return {"status": "updated", "message": "Preferences updated successfully"}


@profile_router.get("/stats")
async def get_user_stats(user=Depends(_current_user)):
    """Get comprehensive user statistics"""
    db = get_database()

    # Get various stats
    enrolled_courses = await db.courses.count_documents({"enrolled_user_ids": user["id"]})
    completed_courses = await db.course_progress.count_documents({"user_id": user["id"], "completed": True})
    total_submissions = await db.submissions.count_documents({"user_id": user["id"]})

    # Calculate average grade
    submissions = await db.submissions.find({"user_id": user["id"]}).to_list(100)
    avg_grade = 0
    if submissions:
        grades = [s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")]
        avg_grade = sum(grades) / len(grades) if grades else 0

    # Get streak info
    streak = await db.learning_streaks.find_one({"user_id": user["id"]})
    current_streak = streak.get("current_streak", 0) if streak else 0

    # Get achievements count
    achievements_count = await db.achievements.count_documents({"user_id": user["id"]})

    # Get total study time (estimated from activities)
    recent_activities = await db.chats.count_documents({
        "session_id": {"$regex": user["id"]},
        "created_at": {"$gte": datetime.utcnow() - timedelta(days=30)}
    })

    return {
        "enrolled_courses": enrolled_courses,
        "completed_courses": completed_courses,
        "completion_rate": (completed_courses / enrolled_courses * 100) if enrolled_courses > 0 else 0,
        "total_submissions": total_submissions,
        "average_grade": round(avg_grade, 1),
        "current_streak": current_streak,
        "achievements_count": achievements_count,
        "estimated_study_sessions": recent_activities,
        "level": min(100, completed_courses * 10 + achievements_count),  # Simple leveling system
        "points": completed_courses * 100 + achievements_count * 50 + total_submissions * 10
    }


@profile_router.get("/public/{user_id}")
async def get_public_profile(user_id: str, current_user=Depends(_current_user)):
    """Get public profile of another user"""
    db = get_database()

    # Get user basic info
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")

    # Get profile
    profile = await db.user_profiles.find_one({"user_id": user_id})

    # Check privacy settings
    if profile and not profile.get("privacy_settings", {}).get("show_profile", True):
        if current_user["id"] != user_id:
            raise HTTPException(403, "Profile is private")

    # Get public achievements
    achievements = await db.achievements.find({"user_id": user_id}).to_list(10)

    # Get completed courses (if privacy allows)
    show_progress = profile.get("privacy_settings", {}).get("show_progress", True) if profile else True
    completed_courses = []
    if show_progress or current_user["id"] == user_id:
        progress_data = await db.course_progress.find({"user_id": user_id, "completed": True}).to_list(20)
        for progress in progress_data:
            course = await db.courses.find_one({"_id": progress["course_id"]})
            if course:
                completed_courses.append({
                    "id": course["_id"],
                    "title": course["title"],
                    "completed_at": progress.get("completed_at")
                })

    return {
        "user": {
            "id": user["_id"],
            "name": user["name"],
            "role": user["role"]
        },
        "profile": profile or {},
        "achievements": achievements,
        "completed_courses": completed_courses,
        "stats": await get_user_stats({"id": user_id})  # This will be called with the target user
    }


@profile_router.post("/achievement/unlock")
async def unlock_achievement(achievement_data: dict, user=Depends(_current_user)):
    """Unlock an achievement for the user (internal use)"""
    db = get_database()

    achievement = Achievement(
        user_id=user["id"],
        type=achievement_data.get("type"),
        title=achievement_data.get("title"),
        description=achievement_data.get("description"),
        icon=achievement_data.get("icon", "🏆"),
        points=achievement_data.get("points", 0),
        metadata=achievement_data.get("metadata", {})
    )

    await db.achievements.insert_one(achievement.dict())

    return {"status": "unlocked", "achievement": achievement.dict()}


# AI-Powered Profile Enhancement
@profile_router.post("/ai/enhance-profile")
async def enhance_profile_with_ai(user=Depends(_current_user)):
    """Use AI to suggest profile improvements and learning recommendations"""
    db = get_database()

    # Get user's current profile and activity
    profile = await db.user_profiles.find_one({"user_id": user["id"]})
    courses = await db.courses.find({"enrolled_user_ids": user["id"]}).to_list(10)
    progress = await db.course_progress.find({"user_id": user["id"]}).to_list(10)
    submissions = await db.submissions.find({"user_id": user["id"]}).to_list(20)

    # Build context for AI
    context = {
        "current_profile": profile or {},
        "enrolled_courses": [{"title": c["title"], "difficulty": c.get("difficulty")} for c in courses],
        "completed_courses": len([p for p in progress if p.get("completed")]),
        "total_submissions": len(submissions),
        "average_grade": sum([s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")]) / len([s for s in submissions if s.get("ai_grade")]) if submissions else 0
    }

    # AI prompt for profile enhancement
    enhancement_prompt = f"""
    Based on this user's learning profile, suggest improvements and recommendations:

    User Profile: {context}

    Please provide:
    1. Suggested skills to add to profile
    2. Learning goals recommendations
    3. Career path suggestions based on completed courses
    4. Next courses to consider
    5. Profile bio suggestions
    6. Social media/networking recommendations

    Format as JSON with keys: skills_suggestions, goals_suggestions, career_suggestions, course_recommendations, bio_suggestions, networking_suggestions
    """

    try:
        model = _get_ai()
        response = model.generate_content(enhancement_prompt)
        suggestions = _safe_json_extract(response.text)

        return {
            "status": "success",
            "suggestions": suggestions,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"AI enhancement failed: {str(e)}",
            "fallback_suggestions": {
                "skills_suggestions": ["Problem Solving", "Critical Thinking", "Communication"],
                "goals_suggestions": ["Complete 5 more courses this year", "Achieve 90%+ average grade"],
                "course_recommendations": ["Advanced topics in your field", "Practical application courses"]
            }
        }


@profile_router.delete("/account")
async def delete_user_account(user=Depends(_current_user)):
    """Delete user account and all associated data"""
    db = get_database()

    user_id = user["id"]

    # Delete user from users collection
    await db.users.delete_one({"_id": user_id})

    # Delete all associated data
    await db.user_profiles.delete_one({"user_id": user_id})
    await db.user_preferences.delete_one({"user_id": user_id})
    await db.learning_streaks.delete_one({"user_id": user_id})
    await db.achievements.delete_many({"user_id": user_id})

    # Remove user from all courses
    await db.courses.update_many(
        {"enrolled_user_ids": user_id},
        {"$pull": {"enrolled_user_ids": user_id}}
    )

    # Delete user's course progress
    await db.course_progress.delete_many({"user_id": user_id})

    # Delete user's submissions
    await db.submissions.delete_many({"user_id": user_id})

    # Delete user's certificates
    await db.certificates.delete_many({"user_id": user_id})

    # Delete user's notifications
    await db.notifications.delete_many({"user_id": user_id})

    # Delete user's chat history (by session_id pattern)
    await db.chats.delete_many({"session_id": {"$regex": user_id}})

    return {"status": "deleted", "message": "Account and all associated data have been permanently deleted"}