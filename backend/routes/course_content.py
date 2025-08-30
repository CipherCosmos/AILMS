from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime
import json
from database import get_database, _insert_one, _update_one, _find_one
from auth import _current_user, _require_role
from models import (
    CourseContent, ModuleProgress, StudentCourseProgress,
    QuizAttempt, DiscussionThread, DiscussionReply,
    GamificationData, AdaptiveLearningProfile
)

course_content_router = APIRouter()

# Course Content Management
@course_content_router.post("/courses/{course_id}/content")
async def create_course_content(course_id: str, content: Dict[str, Any], user=Depends(_current_user)):
    _require_role(user, ["admin", "instructor"])

    # Verify course ownership
    course = await _find_one("courses", {"_id": course_id})
    if not course:
        raise HTTPException(404, "Course not found")
    if user["role"] != "admin" and course.get("owner_id") != user["id"]:
        raise HTTPException(403, "Not authorized")

    course_content = CourseContent(
        course_id=course_id,
        title=content.get("title", ""),
        description=content.get("description", ""),
        modules=content.get("modules", []),
        assessment_types=content.get("assessment_types", []),
        certification=content.get("certification", {}),
        gamification_elements=content.get("gamification_elements", {}),
        adaptive_features=content.get("adaptive_features", {}),
        collaboration_features=content.get("collaboration_features", {}),
        analytics_and_reporting=content.get("analytics_and_reporting", {}),
        accessibility_features=content.get("accessibility_features", {}),
        integration_capabilities=content.get("integration_capabilities", {})
    )

    doc = course_content.dict()
    doc["_id"] = course_content.id

    db = get_database()
    await db.course_content.insert_one(doc)
    return course_content

@course_content_router.get("/courses/{course_id}/content")
async def get_course_content(course_id: str, user=Depends(_current_user)):
    # Check if user has access to course
    course = await _find_one("courses", {"_id": course_id})
    if not course:
        raise HTTPException(404, "Course not found")

    # Check permissions
    has_access = (
        course.get("published") or
        course.get("owner_id") == user["id"] or
        user["role"] in ["admin", "auditor"] or
        user["id"] in course.get("enrolled_user_ids", [])
    )

    if not has_access:
        raise HTTPException(403, "Not authorized to access course content")

    db = get_database()
    content = await db.course_content.find_one({"course_id": course_id})
    if not content:
        raise HTTPException(404, "Course content not found")

    return content

@course_content_router.put("/courses/{course_id}/content")
async def update_course_content(course_id: str, updates: Dict[str, Any], user=Depends(_current_user)):
    _require_role(user, ["admin", "instructor"])

    # Verify course ownership
    course = await _find_one("courses", {"_id": course_id})
    if not course or (user["role"] != "admin" and course.get("owner_id") != user["id"]):
        raise HTTPException(403, "Not authorized")

    db = get_database()
    updates["updated_at"] = datetime.utcnow()
    await db.course_content.update_one(
        {"course_id": course_id},
        {"$set": updates}
    )

    content = await db.course_content.find_one({"course_id": course_id})
    return content

# Student Progress Tracking
@course_content_router.post("/courses/{course_id}/progress")
async def update_student_progress(course_id: str, progress_data: Dict[str, Any], user=Depends(_current_user)):
    db = get_database()

    # Check enrollment
    course = await _find_one("courses", {"_id": course_id})
    if not course or user["id"] not in course.get("enrolled_user_ids", []):
        raise HTTPException(403, "Not enrolled in course")

    # Get or create progress record
    progress = await db.student_course_progress.find_one({
        "user_id": user["id"],
        "course_id": course_id
    })

    if not progress:
        progress = {
            "user_id": user["id"],
            "course_id": course_id,
            "overall_progress": 0.0,
            "modules_progress": [],
            "current_module": progress_data.get("current_module", ""),
            "started_at": datetime.utcnow(),
            "last_accessed": datetime.utcnow(),
            "gamification_data": {},
            "adaptive_settings": {}
        }

    # Update progress
    progress["last_accessed"] = datetime.utcnow()
    progress["overall_progress"] = progress_data.get("overall_progress", progress["overall_progress"])
    progress["current_module"] = progress_data.get("current_module", progress["current_module"])

    # Update module progress
    if "modules_progress" in progress_data:
        progress["modules_progress"] = progress_data["modules_progress"]

    await db.student_course_progress.update_one(
        {"user_id": user["id"], "course_id": course_id},
        {"$set": progress},
        upsert=True
    )

    return progress

@course_content_router.get("/courses/{course_id}/progress")
async def get_student_progress(course_id: str, user=Depends(_current_user)):
    db = get_database()
    progress = await db.student_course_progress.find_one({
        "user_id": user["id"],
        "course_id": course_id
    })

    if not progress:
        return {
            "user_id": user["id"],
            "course_id": course_id,
            "overall_progress": 0.0,
            "modules_progress": [],
            "current_module": "",
            "started_at": datetime.utcnow(),
            "last_accessed": datetime.utcnow(),
            "completed": False,
            "gamification_data": {},
            "adaptive_settings": {}
        }

    return progress

# Quiz Attempts
@course_content_router.post("/courses/{course_id}/quizzes/{quiz_id}/attempt")
async def submit_quiz_attempt(course_id: str, quiz_id: str, attempt_data: Dict[str, Any], user=Depends(_current_user)):
    db = get_database()

    # Check enrollment
    course = await _find_one("courses", {"_id": course_id})
    if not course or user["id"] not in course.get("enrolled_user_ids", []):
        raise HTTPException(403, "Not enrolled in course")

    attempt = QuizAttempt(
        user_id=user["id"],
        course_id=course_id,
        module_id=attempt_data.get("module_id", ""),
        quiz_id=quiz_id,
        answers=attempt_data.get("answers", {}),
        score=attempt_data.get("score", 0.0),
        max_score=attempt_data.get("max_score", 0.0),
        time_taken=attempt_data.get("time_taken", 0),
        feedback=attempt_data.get("feedback", {})
    )

    doc = attempt.dict()
    doc["_id"] = attempt.id
    await db.quiz_attempts.insert_one(doc)

    return attempt

@course_content_router.get("/courses/{course_id}/quizzes/{quiz_id}/attempts")
async def get_quiz_attempts(course_id: str, quiz_id: str, user=Depends(_current_user)):
    db = get_database()
    attempts = await db.quiz_attempts.find({
        "user_id": user["id"],
        "course_id": course_id,
        "quiz_id": quiz_id
    }).sort("completed_at", -1).to_list(10)

    return attempts

# Discussion Forums
@course_content_router.post("/courses/{course_id}/discussions")
async def create_discussion_thread(course_id: str, thread_data: Dict[str, Any], user=Depends(_current_user)):
    # Check enrollment
    course = await _find_one("courses", {"_id": course_id})
    if not course or user["id"] not in course.get("enrolled_user_ids", []):
        raise HTTPException(403, "Not enrolled in course")

    thread = DiscussionThread(
        course_id=course_id,
        module_id=thread_data.get("module_id", ""),
        user_id=user["id"],
        title=thread_data["title"],
        content=thread_data["content"],
        tags=thread_data.get("tags", [])
    )

    doc = thread.dict()
    doc["_id"] = thread.id

    db = get_database()
    await db.discussion_threads.insert_one(doc)
    return thread

@course_content_router.get("/courses/{course_id}/discussions")
async def get_discussion_threads(course_id: str, user=Depends(_current_user)):
    # Check access
    course = await _find_one("courses", {"_id": course_id})
    if not course:
        raise HTTPException(404, "Course not found")

    has_access = (
        course.get("published") or
        course.get("owner_id") == user["id"] or
        user["role"] in ["admin", "auditor"] or
        user["id"] in course.get("enrolled_user_ids", [])
    )

    if not has_access:
        raise HTTPException(403, "Not authorized")

    db = get_database()
    threads = await db.discussion_threads.find({"course_id": course_id}).sort("created_at", -1).to_list(50)
    return threads

@course_content_router.post("/discussions/{thread_id}/replies")
async def create_discussion_reply(thread_id: str, reply_data: Dict[str, Any], user=Depends(_current_user)):
    db = get_database()

    # Verify thread exists
    thread = await db.discussion_threads.find_one({"_id": thread_id})
    if not thread:
        raise HTTPException(404, "Discussion thread not found")

    reply = DiscussionReply(
        thread_id=thread_id,
        user_id=user["id"],
        content=reply_data["content"],
        is_instructor_reply=user["role"] in ["admin", "instructor"]
    )

    doc = reply.dict()
    doc["_id"] = reply.id
    await db.discussion_replies.insert_one(doc)

    # Update thread reply count
    await db.discussion_threads.update_one(
        {"_id": thread_id},
        {"$inc": {"replies_count": 1}}
    )

    return reply

@course_content_router.get("/discussions/{thread_id}/replies")
async def get_discussion_replies(thread_id: str, user=Depends(_current_user)):
    db = get_database()
    replies = await db.discussion_replies.find({"thread_id": thread_id}).sort("created_at", 1).to_list(100)
    return replies

# Gamification
@course_content_router.post("/courses/{course_id}/gamification/points")
async def award_points(course_id: str, points_data: Dict[str, Any], user=Depends(_current_user)):
    _require_role(user, ["admin", "instructor"])

    db = get_database()
    gamification = await db.gamification_data.find_one({
        "user_id": points_data["user_id"],
        "course_id": course_id
    })

    if not gamification:
        gamification = {
            "user_id": points_data["user_id"],
            "course_id": course_id,
            "total_points": 0,
            "badges_earned": [],
            "streak_days": 0,
            "achievements": {},
            "leaderboard_position": 0
        }

    gamification["total_points"] += points_data["points"]
    gamification["last_activity"] = datetime.utcnow()

    await db.gamification_data.update_one(
        {"user_id": points_data["user_id"], "course_id": course_id},
        {"$set": gamification},
        upsert=True
    )

    return gamification

@course_content_router.get("/courses/{course_id}/gamification/leaderboard")
async def get_leaderboard(course_id: str, user=Depends(_current_user)):
    db = get_database()
    leaderboard = await db.gamification_data.find({"course_id": course_id}).sort("total_points", -1).limit(10).to_list(10)
    return leaderboard

# Adaptive Learning
@course_content_router.post("/courses/{course_id}/adaptive/profile")
async def update_adaptive_profile(course_id: str, profile_data: Dict[str, Any], user=Depends(_current_user)):
    db = get_database()

    profile = AdaptiveLearningProfile(
        user_id=user["id"],
        course_id=course_id,
        learning_style=profile_data.get("learning_style", "visual"),
        preferred_pace=profile_data.get("preferred_pace", "moderate"),
        difficulty_preference=profile_data.get("difficulty_preference", "adaptive"),
        content_preferences=profile_data.get("content_preferences", {}),
        performance_history=profile_data.get("performance_history", []),
        recommended_adjustments=profile_data.get("recommended_adjustments", {})
    )

    doc = profile.dict()
    doc["_id"] = profile.id

    await db.adaptive_learning_profiles.update_one(
        {"user_id": user["id"], "course_id": course_id},
        {"$set": doc},
        upsert=True
    )

    return profile

@course_content_router.get("/courses/{course_id}/adaptive/recommendations")
async def get_adaptive_recommendations(course_id: str, user=Depends(_current_user)):
    db = get_database()

    # Get user's adaptive profile
    profile = await db.adaptive_learning_profiles.find_one({
        "user_id": user["id"],
        "course_id": course_id
    })

    # Get user's progress
    progress = await db.student_course_progress.find_one({
        "user_id": user["id"],
        "course_id": course_id
    })

    # Generate recommendations based on profile and progress
    recommendations = {
        "content_adjustments": [],
        "pace_recommendations": [],
        "difficulty_suggestions": [],
        "learning_path": []
    }

    if profile:
        if profile["learning_style"] == "visual":
            recommendations["content_adjustments"].append("Increase use of diagrams and visual aids")
        elif profile["learning_style"] == "auditory":
            recommendations["content_adjustments"].append("Add more audio explanations and discussions")

        if profile["preferred_pace"] == "slow":
            recommendations["pace_recommendations"].append("Extend deadlines and add more practice time")
        elif profile["preferred_pace"] == "fast":
            recommendations["pace_recommendations"].append("Provide accelerated learning options")

    if progress and progress["overall_progress"] < 50:
        recommendations["difficulty_suggestions"].append("Consider reviewing foundational concepts")
    elif progress and progress["overall_progress"] > 80:
        recommendations["difficulty_suggestions"].append("Ready for advanced challenges")

    return recommendations

# Certificate Generation
@course_content_router.post("/courses/{course_id}/certificate")
async def generate_certificate(course_id: str, user=Depends(_current_user)):
    db = get_database()

    # Check if course is completed
    progress = await db.student_course_progress.find_one({
        "user_id": user["id"],
        "course_id": course_id
    })

    if not progress or not progress.get("completed"):
        raise HTTPException(400, "Course not completed")

    if progress.get("certificate_issued"):
        raise HTTPException(400, "Certificate already issued")

    # Get course content for certificate data
    course = await _find_one("courses", {"_id": course_id})
    content = await db.course_content.find_one({"course_id": course_id})

    certificate_data = {
        "student_name": user["name"],
        "course_title": course["title"],
        "completion_date": progress["completed_at"].isoformat(),
        "certificate_id": f"CERT-{course_id}-{user['id'][:8]}",
        "issuer": content.get("certification", {}).get("issuer", "AI Education Consortium"),
        "skills_demonstrated": content.get("modules", [{}])[0].get("objectives", [])
    }

    # Update progress
    await db.student_course_progress.update_one(
        {"user_id": user["id"], "course_id": course_id},
        {"$set": {"certificate_issued": True}}
    )

    return certificate_data