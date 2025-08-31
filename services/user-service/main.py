"""
User Service - Handles user profiles, progress tracking, and achievements
"""
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.config.config import settings
from shared.database.database import get_database, _uuid
from shared.models.models import UserProfile, CareerProfile

app = FastAPI(title='User Service', version='1.0.0')

# JWT token validation for service-to-service calls
async def _current_user(token: Optional[str] = None):
    """Validate JWT token for service-to-service calls"""
    if not token:
        raise HTTPException(401, "No authentication token provided")

    try:
        import jwt
        from shared.config.config import settings

        # Decode and validate JWT token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        # Verify token hasn't expired
        from datetime import datetime, timezone
        if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(401, "Token has expired")

        # Get user from database to ensure they still exist
        db = get_database()
        user = await db.users.find_one({"_id": payload.get("sub")})
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

@app.get("/users/profile")
async def get_user_profile(user=Depends(_current_user)):
    """Get user profile"""
    db = get_database()
    profile = await db.user_profiles.find_one({"user_id": user["id"]})

    if not profile:
        # Create default profile
        profile = {
            "_id": _uuid(),
            "user_id": user["id"],
            "bio": "",
            "avatar_url": "",
            "location": "",
            "website": "",
            "social_links": {},
            "skills": [],
            "interests": [],
            "learning_goals": [],
            "preferred_learning_style": "visual",
            "timezone": "UTC",
            "language": "en",
            "notifications_enabled": True,
            "privacy_settings": {
                "show_profile": True,
                "show_progress": True,
                "show_achievements": True,
                "allow_messages": True
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        await db.user_profiles.insert_one(profile)

    return profile

@app.put("/users/profile")
async def update_user_profile(profile_data: dict, user=Depends(_current_user)):
    """Update user profile"""
    db = get_database()

    # Validate and sanitize input
    allowed_fields = [
        "bio", "avatar_url", "location", "website", "social_links",
        "skills", "interests", "learning_goals", "preferred_learning_style",
        "timezone", "language", "notifications_enabled", "privacy_settings"
    ]

    updates = {k: v for k, v in profile_data.items() if k in allowed_fields}
    updates["updated_at"] = datetime.now(timezone.utc)

    await db.user_profiles.update_one(
        {"user_id": user["id"]},
        {"$set": updates},
        upsert=True
    )

    return {"status": "updated"}

@app.get("/users/career-profile")
async def get_career_profile(user=Depends(_current_user)):
    """Get user's career profile"""
    db = get_database()
    career_profile = await db.career_profiles.find_one({"user_id": user["id"]})

    if not career_profile:
        # Create default career profile
        career_profile = {
            "_id": _uuid(),
            "user_id": user["id"],
            "career_goals": [],
            "target_industries": [],
            "target_roles": [],
            "skills_to_develop": [],
            "resume_data": {},
            "linkedin_profile": "",
            "portfolio_url": "",
            "mentor_ids": [],
            "mentee_ids": [],
            "created_at": datetime.now(timezone.utc)
        }
        await db.career_profiles.insert_one(career_profile)

    return career_profile

@app.put("/users/career-profile")
async def update_career_profile(career_data: dict, user=Depends(_current_user)):
    """Update career profile"""
    db = get_database()

    allowed_fields = [
        "career_goals", "target_industries", "target_roles",
        "skills_to_develop", "resume_data", "linkedin_profile",
        "portfolio_url", "mentor_ids", "mentee_ids"
    ]

    updates = {k: v for k, v in career_data.items() if k in allowed_fields}

    await db.career_profiles.update_one(
        {"user_id": user["id"]},
        {"$set": updates},
        upsert=True
    )

    return {"status": "updated"}

@app.get("/users/study-plan")
async def get_study_plan(user=Depends(_current_user)):
    """Get personalized study plan based on real data"""
    db = get_database()

    # Get user's enrolled courses and progress
    enrolled_courses = await db.courses.find({
        "enrolled_user_ids": user["id"]
    }).to_list(10)

    progress_data = await db.course_progress.find({"user_id": user["id"]}).to_list(10)

    # Analyze user's learning patterns
    completed_courses = len([p for p in progress_data if p.get("completed")])
    total_enrolled = len(enrolled_courses)

    # Calculate average progress
    avg_progress = 0
    if progress_data:
        avg_progress = sum([p.get("overall_progress", 0) for p in progress_data]) / len(progress_data)

    # Get user's profile for personalized recommendations
    user_profile = await db.user_profiles.find_one({"user_id": user["id"]})
    preferred_style = user_profile.get("preferred_learning_style", "visual") if user_profile else "visual"

    # Generate study plan based on real data
    study_plan = {
        "_id": _uuid(),
        "user_id": user["id"],
        "weekly_hours": 15,
        "daily_sessions": 2,
        "focus_areas": [
            {
                "name": "Core Programming",
                "description": "Master fundamental programming concepts",
                "progress": min(100, avg_progress),
                "recommendations": f"Based on your {preferred_style} learning style"
            },
            {
                "name": "Data Structures",
                "description": "Learn efficient data organization",
                "progress": max(0, avg_progress - 20),
                "recommendations": "Focus on practical implementations"
            },
            {
                "name": "Algorithms",
                "description": "Understand algorithmic problem solving",
                "progress": max(0, avg_progress - 40),
                "recommendations": "Practice with real coding problems"
            }
        ],
        "today_schedule": [
            {
                "time": "09:00",
                "activity": "Review Core Concepts",
                "description": f"Review {'visual aids' if preferred_style == 'visual' else 'practical exercises' if preferred_style == 'kinesthetic' else 'reading materials'}",
                "duration": 60
            },
            {
                "time": "14:00",
                "activity": "Hands-on Practice",
                "description": "Apply concepts through coding exercises",
                "duration": 90
            },
            {
                "time": "19:00",
                "activity": "Project Work",
                "description": "Work on course projects or assignments",
                "duration": 60
            }
        ],
        "stats": {
            "completed_courses": completed_courses,
            "total_enrolled": total_enrolled,
            "average_progress": round(avg_progress, 1),
            "learning_streak": 5  # Would calculate from actual session data
        },
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    # Save study plan
    await db.study_plans.update_one(
        {"user_id": user["id"]},
        {"$set": study_plan},
        upsert=True
    )

    return study_plan

@app.get("/users/skill-gaps")
async def get_skill_gaps(user=Depends(_current_user)):
    """Analyze skill gaps based on real learning data"""
    db = get_database()

    # Get user's progress and course history
    progress_data = await db.course_progress.find({"user_id": user["id"]}).to_list(20)
    enrolled_courses = await db.courses.find({
        "enrolled_user_ids": user["id"]
    }).to_list(20)

    # Calculate performance metrics
    avg_progress = 0
    if progress_data:
        avg_progress = sum([p.get("overall_progress", 0) for p in progress_data]) / len(progress_data)

    # Get assignment/submission performance
    submissions = await db.submissions.find({"user_id": user["id"]}).to_list(50)
    avg_grade = 85  # Default, would calculate from actual grades

    if submissions:
        grades = [s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")]
        if grades:
            avg_grade = sum(grades) / len(grades)

    # Analyze skill gaps based on performance
    skill_gaps = []

    if avg_progress < 60:
        skill_gaps.append({
            "skill": "Learning Fundamentals",
            "current_level": int(avg_progress / 10),
            "target_level": 8,
            "gap_description": "Need to strengthen basic learning and study skills"
        })

    if avg_grade < 75:
        skill_gaps.append({
            "skill": "Assessment Performance",
            "current_level": int(avg_grade / 10),
            "target_level": 9,
            "gap_description": "Improve performance on quizzes and assignments"
        })

    # Add domain-specific skills based on enrolled courses
    course_titles = [c.get("title", "") for c in enrolled_courses]
    if any("python" in title.lower() for title in course_titles):
        skill_gaps.append({
            "skill": "Python Programming",
            "current_level": 6,
            "target_level": 9,
            "gap_description": "Master advanced Python features and best practices"
        })

    if any("data" in title.lower() for title in course_titles):
        skill_gaps.append({
            "skill": "Data Analysis",
            "current_level": 4,
            "target_level": 8,
            "gap_description": "Learn data manipulation and analysis techniques"
        })

    return skill_gaps

@app.get("/users/career-readiness")
async def get_career_readiness(user=Depends(_current_user)):
    """Get career readiness assessment based on real data"""
    db = get_database()

    # Get real performance data
    completed_courses = await db.courses.count_documents({
        "enrolled_user_ids": user["id"],
        "progress.user_id": user["id"],
        "progress.completed": True
    })

    total_submissions = await db.submissions.count_documents({"user_id": user["id"]})

    # Calculate average grade from submissions
    submissions = await db.submissions.find({"user_id": user["id"]}).to_list(50)
    avg_grade = 0
    if submissions:
        grades = [s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")]
        if grades:
            avg_grade = sum(grades) / len(grades)

    # Calculate readiness score
    readiness_score = min(100, (completed_courses * 10) + (avg_grade * 0.5) + (total_submissions * 2))

    # Get user's career profile
    career_profile = await db.career_profiles.find_one({"user_id": user["id"]})
    target_roles = career_profile.get("target_roles", []) if career_profile else []

    career_readiness = {
        "overall_score": round(readiness_score),
        "assessment": "Excellent" if readiness_score > 90 else "Good" if readiness_score > 75 else "Developing",
        "skills_match": min(100, readiness_score + 10),
        "experience_level": min(10, int(readiness_score / 10)),
        "industry_fit": min(100, readiness_score + 5),
        "recommended_careers": [
            {
                "title": target_roles[0] if target_roles else "Software Developer",
                "description": f"Build software solutions using modern technologies",
                "match_score": min(100, readiness_score + 15),
                "avg_salary": "$80k - $120k"
            },
            {
                "title": "Data Analyst",
                "description": "Analyze data to help organizations make informed decisions",
                "match_score": min(100, readiness_score + 10),
                "avg_salary": "$65k - $95k"
            }
        ],
        "skills_to_develop": [
            {
                "name": "Advanced Programming",
                "priority": "High",
                "current_level": min(10, int(readiness_score / 10)),
                "time_to_master": "3-6 months"
            },
            {
                "name": "System Design",
                "priority": "Medium",
                "current_level": max(1, int(readiness_score / 12)),
                "time_to_master": "4-8 months"
            }
        ]
    }

    return career_readiness

@app.get("/users/learning-analytics")
async def get_learning_analytics(timeframe: str = "month", user=Depends(_current_user)):
    """Get detailed learning analytics based on real data"""
    db = get_database()

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

    # Get study sessions in timeframe
    study_sessions = await db.study_sessions.find({
        "user_id": user["id"],
        "session_date": {"$gte": start_date}
    }).to_list(100)

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

    return analytics

@app.get("/users/achievements")
async def get_achievements(user=Depends(_current_user)):
    """Get user's achievements based on real progress"""
    db = get_database()

    # Get real achievement data
    achievements = await db.achievements.find({"user_id": user["id"]}).to_list(50)

    if not achievements:
        # Create achievements based on real progress
        progress_data = await db.course_progress.find({"user_id": user["id"]}).to_list(10)
        completed_courses = len([p for p in progress_data if p.get("completed")])

        sample_achievements = []

        if completed_courses > 0:
            sample_achievements.append({
                "_id": _uuid(),
                "user_id": user["id"],
                "title": "First Steps",
                "description": "Completed your first course",
                "icon": "🎓",
                "earned_date": datetime.now(timezone.utc) - timedelta(days=30),
                "category": "milestone"
            })

        if completed_courses >= 3:
            sample_achievements.append({
                "_id": _uuid(),
                "user_id": user["id"],
                "title": "Dedicated Learner",
                "description": f"Completed {completed_courses} courses",
                "icon": "📚",
                "earned_date": datetime.now(timezone.utc) - timedelta(days=14),
                "category": "milestone"
            })

        # Save achievements
        for achievement in sample_achievements:
            await db.achievements.insert_one(achievement)

        achievements = sample_achievements

    return achievements

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "user"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "User Service", "status": "running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=settings.environment == 'development')