from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from database import get_database, _uuid
from auth import _current_user
from models import WellBeingProfile, WellBeingResource
from config import settings

# AI integrations
try:
    import google.generativeai as genai
except Exception:
    genai = None

wellbeing_router = APIRouter()

def _get_ai():
    if genai is None:
        raise HTTPException(status_code=500, detail="AI dependency not installed")
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="No AI key configured")
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(settings.default_llm_model)


@wellbeing_router.post("/checkin")
async def daily_checkin(checkin_data: dict, user=Depends(_current_user)):
    """Record daily well-being check-in"""
    db = get_database()

    checkin = {
        "_id": _uuid(),
        "user_id": user["id"],
        "stress_level": checkin_data.get("stress_level", 5),
        "sleep_hours": checkin_data.get("sleep_hours"),
        "exercise_frequency": checkin_data.get("exercise_frequency", "rarely"),
        "study_hours": checkin_data.get("study_hours"),
        "social_connections": checkin_data.get("social_connections", 5),
        "mood": checkin_data.get("mood"),
        "notes": checkin_data.get("notes"),
        "date": datetime.utcnow().date(),
        "created_at": datetime.utcnow()
    }

    await db.wellbeing_checkins.insert_one(checkin)

    # Update well-being profile
    await _update_wellbeing_profile(user["id"], checkin)

    # Generate personalized recommendations
    recommendations = await _generate_recommendations(user["id"], checkin)

    return {
        "checkin": checkin,
        "recommendations": recommendations,
        "insights": await _generate_insights(user["id"])
    }


@wellbeing_router.get("/profile")
async def get_wellbeing_profile(user=Depends(_current_user)):
    """Get user's well-being profile"""
    db = get_database()

    profile = await db.wellbeing_profiles.find_one({"user_id": user["id"]})
    if not profile:
        # Create default profile
        profile = WellBeingProfile(user_id=user["id"])
        doc = profile.dict()
        doc["_id"] = profile.id
        await db.wellbeing_profiles.insert_one(doc)

    return profile


@wellbeing_router.put("/profile")
async def update_wellbeing_profile(profile_data: dict, user=Depends(_current_user)):
    """Update well-being profile"""
    db = get_database()

    updates = {}
    for field in ["goals", "support_resources_used"]:
        if field in profile_data:
            updates[field] = profile_data[field]

    if updates:
        await db.wellbeing_profiles.update_one(
            {"user_id": user["id"]},
            {"$set": updates},
            upsert=True
        )

    return {"status": "updated"}


@wellbeing_router.get("/resources")
async def get_wellbeing_resources(category: Optional[str] = None, user=Depends(_current_user)):
    """Get well-being resources"""
    db = get_database()

    query = {"is_active": True}
    if category:
        query["category"] = category

    resources = await db.wellbeing_resources.find(query).sort("created_at", -1).to_list(50)

    return resources


@wellbeing_router.post("/resources")
async def create_wellbeing_resource(resource_data: dict, user=Depends(_current_user)):
    """Create a well-being resource (admin/moderator only)"""
    db = get_database()

    # Check permissions
    if not await _can_manage_resources(user["id"], resource_data.get("tenant_id")):
        raise HTTPException(403, "Insufficient permissions")

    resource = WellBeingResource(
        tenant_id=resource_data["tenant_id"],
        title=resource_data["title"],
        type=resource_data["type"],
        category=resource_data["category"],
        content=resource_data["content"],
        url=resource_data.get("url"),
        is_active=True
    )

    doc = resource.dict()
    doc["_id"] = resource.id
    await db.wellbeing_resources.insert_one(doc)

    return resource


@wellbeing_router.post("/crisis-support")
async def request_crisis_support(support_data: dict, user=Depends(_current_user)):
    """Request crisis support"""
    db = get_database()

    support_request = {
        "_id": _uuid(),
        "user_id": user["id"],
        "urgency": support_data.get("urgency", "medium"),
        "reason": support_data.get("reason"),
        "contact_method": support_data.get("contact_method", "chat"),
        "additional_info": support_data.get("additional_info"),
        "status": "pending",
        "created_at": datetime.utcnow()
    }

    await db.crisis_support_requests.insert_one(support_request)

    # In production, this would trigger notifications to counselors
    # For now, return immediate AI-powered support

    ai_support = await _generate_crisis_support(support_data.get("reason", ""))

    return {
        "request": support_request,
        "immediate_support": ai_support,
        "hotlines": await _get_crisis_hotlines(),
        "message": "Support request submitted. Help is available 24/7."
    }


@wellbeing_router.get("/trends")
async def get_wellbeing_trends(days: int = 30, user=Depends(_current_user)):
    """Get well-being trends over time"""
    db = get_database()

    start_date = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {
            "$match": {
                "user_id": user["id"],
                "created_at": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$created_at"
                    }
                },
                "avg_stress": {"$avg": "$stress_level"},
                "avg_sleep": {"$avg": "$sleep_hours"},
                "avg_social": {"$avg": "$social_connections"},
                "checkins": {"$sum": 1}
            }
        },
        {
            "$sort": {"_id": 1}
        }
    ]

    trends = await db.wellbeing_checkins.aggregate(pipeline).to_list(100)

    return {
        "trends": trends,
        "period_days": days,
        "insights": await _analyze_trends(trends)
    }


@wellbeing_router.post("/ai/coach")
async def get_ai_coaching(coaching_data: dict, user=Depends(_current_user)):
    """Get AI-powered coaching and advice"""
    db = get_database()

    # Get user's recent well-being data
    recent_checkins = await db.wellbeing_checkins.find({
        "user_id": user["id"]
    }).sort("created_at", -1).limit(7).to_list(7)

    context = {
        "recent_checkins": recent_checkins,
        "request": coaching_data.get("request", ""),
        "goal": coaching_data.get("goal", ""),
        "current_challenge": coaching_data.get("current_challenge", "")
    }

    coaching_response = await _generate_coaching_response(context)

    # Log the coaching interaction
    await db.ai_coaching_sessions.insert_one({
        "_id": _uuid(),
        "user_id": user["id"],
        "request": coaching_data,
        "response": coaching_response,
        "created_at": datetime.utcnow()
    })

    return coaching_response


@wellbeing_router.post("/study-break")
async def schedule_study_break(break_data: dict, user=Depends(_current_user)):
    """Schedule a study break with wellness activities"""
    db = get_database()

    study_break = {
        "_id": _uuid(),
        "user_id": user["id"],
        "duration_minutes": break_data.get("duration_minutes", 10),
        "activity_type": break_data.get("activity_type", "breathing"),
        "scheduled_for": datetime.utcnow() + timedelta(minutes=break_data.get("delay_minutes", 0)),
        "completed": False,
        "activities": await _generate_break_activities(break_data.get("activity_type", "breathing")),
        "created_at": datetime.utcnow()
    }

    await db.study_breaks.insert_one(study_break)

    return study_break


@wellbeing_router.post("/study-break/{break_id}/complete")
async def complete_study_break(break_id: str, user=Depends(_current_user)):
    """Mark study break as completed"""
    db = get_database()

    result = await db.study_breaks.update_one(
        {"_id": break_id, "user_id": user["id"]},
        {"$set": {"completed": True, "completed_at": datetime.utcnow()}}
    )

    if result.modified_count == 0:
        raise HTTPException(404, "Study break not found")

    return {"status": "completed", "message": "Great job taking a break!"}


@wellbeing_router.get("/dashboard")
async def get_wellbeing_dashboard(user=Depends(_current_user)):
    """Get comprehensive well-being dashboard"""
    db = get_database()

    # Get recent check-ins
    recent_checkins = await db.wellbeing_checkins.find({
        "user_id": user["id"]
    }).sort("created_at", -1).limit(7).to_list(7)

    # Get profile
    profile = await db.wellbeing_profiles.find_one({"user_id": user["id"]})

    # Get upcoming study breaks
    upcoming_breaks = await db.study_breaks.find({
        "user_id": user["id"],
        "scheduled_for": {"$gt": datetime.utcnow()},
        "completed": False
    }).sort("scheduled_for", 1).limit(3).to_list(3)

    # Get recommended resources
    if profile and recent_checkins:
        avg_stress = sum(c.get("stress_level", 5) for c in recent_checkins) / len(recent_checkins)
        if avg_stress > 7:
            recommended_resources = await db.wellbeing_resources.find({
                "category": {"$in": ["stress", "anxiety", "mindfulness"]},
                "is_active": True
            }).limit(3).to_list(3)
        else:
            recommended_resources = await db.wellbeing_resources.find({
                "category": "motivation",
                "is_active": True
            }).limit(3).to_list(3)
    else:
        recommended_resources = []

    return {
        "recent_checkins": recent_checkins,
        "profile": profile,
        "upcoming_breaks": upcoming_breaks,
        "recommended_resources": recommended_resources,
        "streak_data": await _calculate_streak(user["id"]),
        "insights": await _generate_dashboard_insights(user["id"])
    }


# Helper functions
async def _update_wellbeing_profile(user_id: str, checkin: dict):
    """Update well-being profile based on check-in data"""
    db = get_database()

    # Calculate trends from recent check-ins
    recent_checkins = await db.wellbeing_checkins.find({
        "user_id": user_id
    }).sort("created_at", -1).limit(30).to_list(30)

    if len(recent_checkins) >= 7:
        avg_stress = sum(c.get("stress_level", 5) for c in recent_checkins[:7]) / 7
        avg_sleep = sum(c.get("sleep_hours", 7) for c in recent_checkins[:7] if c.get("sleep_hours")) / 7
        avg_social = sum(c.get("social_connections", 5) for c in recent_checkins[:7]) / 7

        await db.wellbeing_profiles.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "stress_level": avg_stress,
                    "sleep_hours": avg_sleep,
                    "social_connections": avg_social,
                    "last_check_in": datetime.utcnow()
                }
            },
            upsert=True
        )


async def _generate_recommendations(user_id: str, checkin: dict):
    """Generate personalized recommendations based on check-in"""
    recommendations = []

    stress_level = checkin.get("stress_level", 5)
    sleep_hours = checkin.get("sleep_hours")
    exercise_freq = checkin.get("exercise_frequency", "rarely")

    if stress_level > 7:
        recommendations.append({
            "type": "stress_management",
            "title": "Try Deep Breathing",
            "description": "Practice 4-7-8 breathing technique for 5 minutes",
            "action": "breathing_exercise"
        })

    if sleep_hours and sleep_hours < 7:
        recommendations.append({
            "type": "sleep",
            "title": "Improve Sleep Quality",
            "description": "Consider a consistent bedtime routine",
            "action": "sleep_tips"
        })

    if exercise_freq == "rarely":
        recommendations.append({
            "type": "exercise",
            "title": "Add Physical Activity",
            "description": "Even 10 minutes of walking can boost your mood",
            "action": "exercise_suggestion"
        })

    return recommendations[:3]


async def _generate_insights(user_id: str):
    """Generate insights from well-being data"""
    db = get_database()

    # Get last 30 days of data
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    checkins = await db.wellbeing_checkins.find({
        "user_id": user_id,
        "created_at": {"$gte": thirty_days_ago}
    }).to_list(100)

    if len(checkins) < 7:
        return {"message": "Keep checking in daily for personalized insights!"}

    avg_stress = sum(c.get("stress_level", 5) for c in checkins) / len(checkins)
    avg_sleep = sum(c.get("sleep_hours", 7) for c in checkins if c.get("sleep_hours")) / len([c for c in checkins if c.get("sleep_hours")])

    insights = []

    if avg_stress > 6:
        insights.append("Your stress levels have been elevated. Consider incorporating more relaxation techniques.")
    elif avg_stress < 4:
        insights.append("Great job managing stress! Keep up the good work.")

    if avg_sleep < 7:
        insights.append("Your average sleep is below recommended levels. Prioritizing sleep may improve your focus.")

    return {"insights": insights, "averages": {"stress": avg_stress, "sleep": avg_sleep}}


async def _generate_crisis_support(reason: str):
    """Generate immediate AI support for crisis situations"""
    try:
        prompt = f"""
        A student is experiencing distress: {reason}

        Provide immediate, supportive response with:
        1. Validation of their feelings
        2. Immediate coping strategies
        3. When to seek professional help
        4. Available resources

        Keep response empathetic, non-judgmental, and action-oriented.
        """

        model = _get_ai()
        response = model.generate_content(prompt)
        return response.text
    except:
        return """
        I'm here to support you. Remember that it's okay to ask for help.
        Take deep breaths and reach out to a trusted friend, family member, or counselor.
        If you're in immediate danger, please call emergency services.
        """


async def _get_crisis_hotlines():
    """Get crisis hotline information"""
    return [
        {"name": "National Suicide Prevention Lifeline", "number": "988", "available": "24/7"},
        {"name": "Crisis Text Line", "number": "Text HOME to 741741", "available": "24/7"},
        {"name": "International Association for Suicide Prevention", "url": "https://www.iasp.info/resources/Crisis_Centres/"}
    ]


async def _analyze_trends(trends: list):
    """Analyze well-being trends"""
    if len(trends) < 7:
        return {"message": "Need more data for trend analysis"}

    # Simple trend analysis
    recent_stress = [t.get("avg_stress", 5) for t in trends[-7:]]
    stress_trend = "stable"

    if len(recent_stress) >= 2:
        if recent_stress[-1] > recent_stress[0] + 1:
            stress_trend = "increasing"
        elif recent_stress[-1] < recent_stress[0] - 1:
            stress_trend = "decreasing"

    return {
        "stress_trend": stress_trend,
        "consistency_score": len([t for t in trends if t.get("checkins", 0) > 0]) / len(trends),
        "recommendations": _get_trend_recommendations(stress_trend)
    }


def _get_trend_recommendations(trend: str):
    """Get recommendations based on trend"""
    recommendations = {
        "increasing": ["Consider talking to a counselor", "Practice daily mindfulness", "Ensure adequate sleep"],
        "decreasing": ["Keep up the positive habits!", "Share your coping strategies with others"],
        "stable": ["Maintain your current wellness routine", "Consider trying new stress-reduction techniques"]
    }
    return recommendations.get(trend, ["Continue monitoring your well-being"])


async def _generate_coaching_response(context: dict):
    """Generate AI coaching response"""
    try:
        prompt = f"""
        Student well-being context:
        Recent stress levels: {[c.get('stress_level') for c in context.get('recent_checkins', [])]}
        Request: {context.get('request', '')}
        Goal: {context.get('goal', '')}
        Challenge: {context.get('current_challenge', '')}

        Provide personalized coaching advice that's:
        1. Empathetic and supportive
        2. Practical and actionable
        3. Evidence-based where possible
        4. Focused on building resilience

        Keep response to 200-300 words.
        """

        model = _get_ai()
        response = model.generate_content(prompt)
        return {
            "advice": response.text,
            "suggested_actions": [
                "Practice deep breathing for 5 minutes",
                "Take a 10-minute walk outside",
                "Write down 3 things you're grateful for",
                "Connect with a friend or family member"
            ],
            "follow_up_question": "What's one small step you can take today toward your goal?"
        }
    except:
        return {
            "advice": "Remember that taking care of your mental health is just as important as your academic success. Small, consistent actions can make a big difference.",
            "suggested_actions": [
                "Take deep breaths",
                "Go for a short walk",
                "Practice mindfulness",
                "Reach out for support"
            ]
        }


async def _generate_break_activities(activity_type: str):
    """Generate study break activities"""
    activities = {
        "breathing": [
            {"name": "4-7-8 Breathing", "duration": "4 minutes", "instructions": "Inhale for 4, hold for 7, exhale for 8"},
            {"name": "Box Breathing", "duration": "5 minutes", "instructions": "Inhale 4, hold 4, exhale 4, hold 4"}
        ],
        "movement": [
            {"name": "Desk Stretches", "duration": "3 minutes", "instructions": "Neck rolls, shoulder shrugs, wrist circles"},
            {"name": "Walk Around", "duration": "5 minutes", "instructions": "Walk around your space mindfully"}
        ],
        "mindfulness": [
            {"name": "Body Scan", "duration": "5 minutes", "instructions": "Notice sensations in your body from toes to head"},
            {"name": "Gratitude Practice", "duration": "3 minutes", "instructions": "Think of 3 things you're grateful for"}
        ]
    }

    return activities.get(activity_type, activities["breathing"])


async def _calculate_streak(user_id: str):
    """Calculate current well-being check-in streak"""
    db = get_database()

    # Get check-ins for last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    checkins = await db.wellbeing_checkins.find({
        "user_id": user_id,
        "created_at": {"$gte": thirty_days_ago}
    }).sort("date", -1).to_list(30)

    # Calculate streak
    current_streak = 0
    longest_streak = 0
    temp_streak = 0

    dates = set(c["date"] for c in checkins)
    today = datetime.utcnow().date()

    # Current streak
    for i in range(30):
        check_date = today - timedelta(days=i)
        if check_date in dates:
            current_streak += 1
        else:
            break

    # Longest streak
    sorted_dates = sorted(dates)
    for i, date in enumerate(sorted_dates):
        if i == 0 or (date - sorted_dates[i-1]).days == 1:
            temp_streak += 1
        else:
            longest_streak = max(longest_streak, temp_streak)
            temp_streak = 1
    longest_streak = max(longest_streak, temp_streak)

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_checkins": len(checkins)
    }


async def _generate_dashboard_insights(user_id: str):
    """Generate dashboard insights"""
    db = get_database()

    # Get recent data
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_checkins = await db.wellbeing_checkins.find({
        "user_id": user_id,
        "created_at": {"$gte": week_ago}
    }).to_list(10)

    if len(recent_checkins) < 3:
        return {"message": "Keep checking in to see personalized insights!"}

    avg_stress = sum(c.get("stress_level", 5) for c in recent_checkins) / len(recent_checkins)

    insights = []
    if avg_stress > 6:
        insights.append("Consider incorporating more stress-reduction techniques into your routine.")
    if len(recent_checkins) >= 7:
        insights.append("Great job maintaining consistent check-ins!")

    return {"insights": insights, "avg_stress_this_week": avg_stress}


async def _can_manage_resources(user_id: str, tenant_id: str):
    """Check if user can manage well-being resources"""
    from routes.rbac import check_permission
    return await check_permission(user_id, "wellbeing:manage", tenant_id)