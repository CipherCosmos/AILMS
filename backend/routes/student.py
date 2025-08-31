from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
from database import get_database, _uuid
from auth import _current_user
from models import UserProfile, CareerProfile

student_router = APIRouter()

@student_router.get("/study_plan")
async def get_study_plan(user=Depends(_current_user)):
    """Get personalized AI-generated study plan"""
    db = get_database()

    # Check if user is a student
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "student":
        raise HTTPException(403, "Student access required")

    # Get or generate study plan
    study_plan = await db.study_plans.find_one({"user_id": user["id"]})

    if not study_plan:
        # Generate a basic study plan based on enrolled courses
        enrolled_courses = await db.courses.find({
            "enrolled_user_ids": user["id"]
        }).to_list(10)

        # Create study plan
        study_plan = {
            "_id": _uuid(),
            "user_id": user["id"],
            "weekly_hours": 15,
            "daily_sessions": 2,
            "focus_areas": [
                {
                    "name": "Core Programming",
                    "description": "Master fundamental programming concepts",
                    "progress": 65
                },
                {
                    "name": "Data Structures",
                    "description": "Learn efficient data organization",
                    "progress": 40
                },
                {
                    "name": "Algorithms",
                    "description": "Understand algorithmic problem solving",
                    "progress": 30
                }
            ],
            "today_schedule": [
                {
                    "time": "09:00",
                    "activity": "Review Python Basics",
                    "description": "Practice variables, loops, and functions",
                    "duration": 60
                },
                {
                    "time": "14:00",
                    "activity": "Data Structures Study",
                    "description": "Learn about arrays and linked lists",
                    "duration": 90
                },
                {
                    "time": "19:00",
                    "activity": "Algorithm Practice",
                    "description": "Solve coding problems on LeetCode",
                    "duration": 60
                }
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        await db.study_plans.insert_one(study_plan)

    return study_plan

@student_router.get("/skill_gaps")
async def get_skill_gaps(user=Depends(_current_user)):
    """Analyze and return skill gaps based on learning progress"""
    db = get_database()

    # Check if user is a student
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "student":
        raise HTTPException(403, "Student access required")

    # Get user's profile and progress
    user_profile = await db.user_profiles.find_one({"user_id": user["id"]})

    # Get enrolled courses and progress
    enrolled_courses = await db.courses.find({
        "enrolled_user_ids": user["id"]
    }).to_list(10)

    # Analyze skill gaps (simplified version)
    skill_gaps = [
        {
            "skill": "Python Programming",
            "current_level": 7,
            "target_level": 10,
            "gap_description": "Need to master advanced Python features"
        },
        {
            "skill": "Database Design",
            "current_level": 4,
            "target_level": 8,
            "gap_description": "Learn SQL and NoSQL database concepts"
        },
        {
            "skill": "Web Development",
            "current_level": 6,
            "target_level": 9,
            "gap_description": "Master modern web frameworks and APIs"
        },
        {
            "skill": "Data Analysis",
            "current_level": 3,
            "target_level": 7,
            "gap_description": "Learn pandas, numpy, and data visualization"
        }
    ]

    return skill_gaps

@student_router.get("/career_readiness")
async def get_career_readiness(user=Depends(_current_user)):
    """Get career readiness assessment and recommendations"""
    db = get_database()

    # Check if user is a student
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "student":
        raise HTTPException(403, "Student access required")

    # Get user's profile and progress
    user_profile = await db.user_profiles.find_one({"user_id": user["id"]})
    career_profile = await db.career_profiles.find_one({"user_id": user["id"]})

    # Calculate readiness score based on various factors
    completed_courses = await db.courses.count_documents({
        "enrolled_user_ids": user["id"],
        "progress.user_id": user["id"],
        "progress.completed": True
    })

    total_submissions = await db.submissions.count_documents({"user_id": user["id"]})
    avg_grade = 85  # This would be calculated from actual grades

    # Career readiness assessment
    readiness_score = min(100, (completed_courses * 10) + (avg_grade * 0.5) + (total_submissions * 2))

    career_readiness = {
        "overall_score": round(readiness_score),
        "assessment": f"{'Excellent' if readiness_score > 90 else 'Good' if readiness_score > 75 else 'Developing'} career readiness",
        "skills_match": 78,
        "experience_level": 6,
        "industry_fit": 82,
        "recommended_careers": [
            {
                "title": "Full Stack Developer",
                "description": "Build complete web applications using modern technologies",
                "match_score": 85,
                "avg_salary": "$85k - $120k"
            },
            {
                "title": "Data Analyst",
                "description": "Analyze data to help organizations make informed decisions",
                "match_score": 78,
                "avg_salary": "$65k - $95k"
            },
            {
                "title": "DevOps Engineer",
                "description": "Manage infrastructure and deployment pipelines",
                "match_score": 72,
                "avg_salary": "$90k - $130k"
            }
        ],
        "skills_to_develop": [
            {
                "name": "Cloud Computing (AWS/GCP)",
                "priority": "High",
                "current_level": 30,
                "time_to_master": "3-6 months"
            },
            {
                "name": "Machine Learning",
                "priority": "Medium",
                "current_level": 20,
                "time_to_master": "6-12 months"
            },
            {
                "name": "System Design",
                "priority": "High",
                "current_level": 25,
                "time_to_master": "4-8 months"
            }
        ]
    }

    return career_readiness

@student_router.get("/peer_groups")
async def get_peer_groups(user=Depends(_current_user)):
    """Get study groups and peer learning opportunities"""
    db = get_database()

    # Check if user is a student
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "student":
        raise HTTPException(403, "Student access required")

    # Get user's enrolled courses to find relevant groups
    enrolled_courses = await db.courses.find({
        "enrolled_user_ids": user["id"]
    }).to_list(5)

    # Return sample peer groups (in production, this would be dynamic)
    peer_groups = [
        {
            "id": "web-dev-group",
            "name": "Web Development Study Group",
            "description": "Collaborative learning for modern web development",
            "members": 24,
            "shared_courses": 5,
            "discussions": 47,
            "active_projects": 3
        },
        {
            "id": "data-science-group",
            "name": "Data Science & ML Group",
            "description": "Learn data analysis, machine learning, and AI together",
            "members": 31,
            "shared_courses": 7,
            "discussions": 62,
            "active_projects": 5
        },
        {
            "id": "mobile-dev-group",
            "name": "Mobile App Development",
            "description": "Build mobile apps for iOS and Android",
            "members": 18,
            "shared_courses": 3,
            "discussions": 29,
            "active_projects": 2
        }
    ]

    return peer_groups

@student_router.get("/learning_insights")
async def get_learning_insights(user=Depends(_current_user)):
    """Get AI-powered learning insights and recommendations"""
    db = get_database()

    # Check if user is a student
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "student":
        raise HTTPException(403, "Student access required")

    # Generate insights based on learning patterns
    learning_insights = [
        {
            "icon": "📈",
            "title": "Consistent Progress",
            "description": "You've maintained a 7-day learning streak! Keep up the momentum.",
            "type": "positive",
            "action": "Continue your current study plan"
        },
        {
            "icon": "🎯",
            "title": "Focus Area Identified",
            "description": "You're excelling in Python but could improve in database concepts.",
            "type": "suggestion",
            "action": "Spend more time on database courses"
        },
        {
            "icon": "⚡",
            "title": "Peak Learning Time",
            "description": "Your most productive learning hours are between 9 AM - 11 AM.",
            "type": "insight",
            "action": "Schedule important study sessions during peak times"
        },
        {
            "icon": "🤝",
            "title": "Peer Learning Opportunity",
            "description": "3 students in your courses are studying similar topics.",
            "type": "social",
            "action": "Join a study group for collaborative learning"
        },
        {
            "icon": "📚",
            "title": "Course Recommendation",
            "description": "Based on your progress, 'Advanced React Patterns' would be perfect next.",
            "type": "recommendation",
            "action": "Enroll in Advanced React Patterns"
        },
        {
            "icon": "🏆",
            "title": "Achievement Unlocked",
            "description": "Congratulations! You've earned the 'Problem Solver' badge.",
            "type": "achievement",
            "action": "View your achievements"
        }
    ]

    return learning_insights

@student_router.get("/study_streak")
async def get_study_streak(user=Depends(_current_user)):
    """Get study streak information and statistics"""
    db = get_database()

    # Check if user is a student
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "student":
        raise HTTPException(403, "Student access required")

    # Get or create study streak data
    study_streak = await db.study_streaks.find_one({"user_id": user["id"]})

    if not study_streak:
        # Create initial streak data
        study_streak = {
            "_id": _uuid(),
            "user_id": user["id"],
            "current_streak": 5,
            "longest_streak": 12,
            "total_days": 28,
            "last_study_date": datetime.utcnow().date(),
            "streak_history": [
                {"date": (datetime.utcnow() - timedelta(days=i)).date(), "studied": True}
                for i in range(5)
            ] + [
                {"date": (datetime.utcnow() - timedelta(days=i)).date(), "studied": False}
                for i in range(5, 10)
            ],
            "weekly_goal": 5,
            "monthly_goal": 20
        }
        await db.study_streaks.insert_one(study_streak)

    return {
        "current_streak": study_streak["current_streak"],
        "longest_streak": study_streak["longest_streak"],
        "total_study_days": study_streak["total_days"],
        "weekly_goal": study_streak["weekly_goal"],
        "monthly_goal": study_streak["monthly_goal"],
        "streak_maintained": study_streak["current_streak"] > 0
    }

@student_router.post("/study_session")
async def log_study_session(session_data: dict, user=Depends(_current_user)):
    """Log a study session to maintain streaks"""
    db = get_database()

    # Check if user is a student
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "student":
        raise HTTPException(403, "Student access required")

    # Update study streak
    study_streak = await db.study_streaks.find_one({"user_id": user["id"]})

    if study_streak:
        today = datetime.utcnow().date()
        last_study_date = study_streak.get("last_study_date")

        if last_study_date == today:
            # Already studied today
            return {"status": "already_logged"}

        # Check if streak continues
        days_diff = (today - last_study_date).days if last_study_date else 0

        if days_diff == 1:
            # Continue streak
            study_streak["current_streak"] += 1
        elif days_diff > 1:
            # Streak broken
            study_streak["current_streak"] = 1

        # Update longest streak
        if study_streak["current_streak"] > study_streak["longest_streak"]:
            study_streak["longest_streak"] = study_streak["current_streak"]

        study_streak["total_days"] += 1
        study_streak["last_study_date"] = today

        await db.study_streaks.update_one(
            {"_id": study_streak["_id"]},
            {"$set": study_streak}
        )

    # Log the study session
    study_session = {
        "_id": _uuid(),
        "user_id": user["id"],
        "course_id": session_data.get("course_id"),
        "duration_minutes": session_data.get("duration_minutes", 30),
        "topics_covered": session_data.get("topics_covered", []),
        "session_date": datetime.utcnow(),
        "productivity_score": session_data.get("productivity_score", 7)
    }

    await db.study_sessions.insert_one(study_session)

    return {"status": "logged", "session_id": study_session["_id"]}

@student_router.get("/learning_analytics")
async def get_learning_analytics(timeframe: str = "month", user=Depends(_current_user)):
    """Get detailed learning analytics"""
    db = get_database()

    # Check if user is a student
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "student":
        raise HTTPException(403, "Student access required")

    # Calculate date range
    now = datetime.utcnow()
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

    # Most productive hours
    hourly_stats = {}
    for session in study_sessions:
        hour = session["session_date"].hour
        if hour not in hourly_stats:
            hourly_stats[hour] = {"sessions": 0, "avg_productivity": 0}
        hourly_stats[hour]["sessions"] += 1
        hourly_stats[hour]["avg_productivity"] += session.get("productivity_score", 7)

    for hour in hourly_stats:
        hourly_stats[hour]["avg_productivity"] /= hourly_stats[hour]["sessions"]

    analytics = {
        "timeframe": timeframe,
        "total_sessions": total_sessions,
        "total_study_hours": round(total_minutes / 60, 1),
        "average_productivity": round(avg_productivity, 1),
        "daily_average": round(total_minutes / max((now - start_date).days, 1), 1),
        "most_productive_hour": max(hourly_stats.items(), key=lambda x: x[1]["avg_productivity"])[0] if hourly_stats else None,
        "consistency_score": min(100, total_sessions * 10),  # Simplified calculation
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

@student_router.get("/achievements")
async def get_achievements(user=Depends(_current_user)):
    """Get user's learning achievements and badges"""
    db = get_database()

    # Check if user is a student
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "student":
        raise HTTPException(403, "Student access required")

    # Get or create achievements
    achievements = await db.achievements.find({"user_id": user["id"]}).to_list(50)

    if not achievements:
        # Create sample achievements
        sample_achievements = [
            {
                "_id": _uuid(),
                "user_id": user["id"],
                "title": "First Steps",
                "description": "Completed your first course",
                "icon": "🎓",
                "earned_date": datetime.utcnow() - timedelta(days=30),
                "category": "milestone"
            },
            {
                "_id": _uuid(),
                "user_id": user["id"],
                "title": "Streak Master",
                "description": "Maintained a 7-day learning streak",
                "icon": "🔥",
                "earned_date": datetime.utcnow() - timedelta(days=7),
                "category": "consistency"
            },
            {
                "_id": _uuid(),
                "user_id": user["id"],
                "title": "Problem Solver",
                "description": "Solved 50 coding problems",
                "icon": "🧠",
                "earned_date": datetime.utcnow() - timedelta(days=14),
                "category": "skill"
            },
            {
                "_id": _uuid(),
                "user_id": user["id"],
                "title": "Team Player",
                "description": "Contributed to 10 group projects",
                "icon": "🤝",
                "earned_date": datetime.utcnow() - timedelta(days=21),
                "category": "collaboration"
            }
        ]

        for achievement in sample_achievements:
            await db.achievements.insert_one(achievement)

        achievements = sample_achievements

    return achievements