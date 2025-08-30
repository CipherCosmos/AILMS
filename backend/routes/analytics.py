from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from database import get_database
from auth import _current_user, _require_role
from models import CourseAnalytics, StudentAnalytics
from datetime import datetime
import uuid

analytics_router = APIRouter()


@analytics_router.get("/ai/course/{course_id}")
async def get_course_analytics(course_id: str, user=Depends(_current_user)):
    """Get comprehensive analytics for a course"""
    db = get_database()

    # Check if user has access to this course
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(404, "Course not found")

    if user["role"] not in ["admin", "instructor"] and course.get("owner_id") != user["id"]:
        raise HTTPException(403, "Not authorized to view analytics")

    # Get enrollment data
    enrollments = len(course.get("enrolled_user_ids", []))

    # Get progress data
    progress_data = await db.course_progress.find({"course_id": course_id}).to_list(1000)

    # Calculate completion rate
    completed_count = len([p for p in progress_data if p.get("completed")])
    completion_rate = (completed_count / max(enrollments, 1)) * 100

    # Calculate average progress
    if progress_data:
        avg_progress = sum([p.get("overall_progress", 0) for p in progress_data]) / len(progress_data)
    else:
        avg_progress = 0

    # Get review data
    reviews = await db.course_reviews.find({"course_id": course_id}).to_list(100)
    avg_rating = 0
    if reviews:
        avg_rating = sum([r.get("rating", 0) for r in reviews]) / len(reviews)

    # Get discussion data
    discussions = await db.course_discussions.find({"course_id": course_id}).to_list(100)

    # Mock some additional analytics data
    analytics = {
        "enrollment_trends": enrollments,
        "completion_rate": round(completion_rate, 1),
        "average_progress": round(avg_progress, 1),
        "average_rating": round(avg_rating, 1),
        "total_reviews": len(reviews),
        "discussion_count": len(discussions),
        "performance_insights": [
            "Your course completion rate is above average",
            "Students are engaging well with the content",
            "Consider adding more interactive elements"
        ],
        "popular_lessons": [
            {"lesson_id": "lesson1", "title": "Introduction", "views": 150},
            {"lesson_id": "lesson2", "title": "Core Concepts", "views": 120}
        ],
        "student_demographics": {
            "total_students": enrollments,
            "active_students": max(1, int(enrollments * 0.8)),
            "completion_distribution": {
                "0-25%": int(enrollments * 0.1),
                "25-50%": int(enrollments * 0.2),
                "50-75%": int(enrollments * 0.3),
                "75-100%": int(enrollments * 0.4)
            }
        },
        "engagement_metrics": {
            "average_session_time": 24,
            "total_sessions": enrollments * 5,
            "return_visitors": int(enrollments * 0.7)
        }
    }

    return analytics


@analytics_router.get("/ai/student/{user_id}")
async def get_student_analytics(user_id: str, course_id: Optional[str] = None, user=Depends(_current_user)):
    """Get detailed analytics for a specific student"""
    db = get_database()

    # Check permissions
    if user["id"] != user_id and user["role"] not in ["admin", "instructor"]:
        raise HTTPException(403, "Not authorized to view student analytics")

    # Get student's courses and progress
    courses = await db.courses.find({"enrolled_user_ids": user_id}).to_list(20)
    progress_data = await db.course_progress.find({"user_id": user_id}).to_list(20)

    # Calculate metrics
    lessons_completed = sum([p.get("lessons_progress", []) for p in progress_data], [])
    lessons_completed = sum(1 for lesson in lessons_completed if lesson.get("completed"))

    total_time_spent = sum([p.get("time_spent", 0) for p in progress_data])

    if progress_data:
        progress_percentage = sum([p.get("overall_progress", 0) for p in progress_data]) / len(progress_data)
    else:
        progress_percentage = 0

    # Get quiz scores
    quiz_scores = []
    for progress in progress_data:
        for lesson in progress.get("lessons_progress", []):
            if lesson.get("quiz_score") is not None:
                quiz_scores.append({
                    "lesson_id": lesson["lesson_id"],
                    "score": lesson["quiz_score"],
                    "completed_at": lesson.get("quiz_completed_at")
                })

    # Mock learning pattern analysis
    learning_pattern = "consistent" if progress_percentage > 50 else "needs_improvement"

    analytics = {
        "lessons_completed": lessons_completed,
        "total_time_spent": total_time_spent,
        "progress_percentage": round(progress_percentage, 1),
        "quiz_scores": quiz_scores,
        "discussion_participation": 5,  # Mock data
        "last_activity": datetime.utcnow().isoformat(),
        "learning_pattern": learning_pattern,
        "strengths": ["Good understanding of core concepts", "Consistent progress"],
        "areas_for_improvement": ["Could improve quiz performance", "More practice needed"],
        "personalized_recommendations": [
            "Focus on completing remaining lessons",
            "Review quiz questions that were missed",
            "Join study groups for peer learning"
        ]
    }

    return analytics


@analytics_router.get("/course/{course_id}/students")
async def get_course_students(course_id: str, user=Depends(_current_user)):
    """Get list of students enrolled in a course with their progress"""
    db = get_database()

    # Check permissions
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(404, "Course not found")

    if user["role"] not in ["admin", "instructor"] and course.get("owner_id") != user["id"]:
        raise HTTPException(403, "Not authorized")

    enrolled_user_ids = course.get("enrolled_user_ids", [])

    students = []
    for user_id in enrolled_user_ids:
        user_data = await db.users.find_one({"_id": user_id})
        if user_data:
            # Get progress data
            progress = await db.course_progress.find_one({"course_id": course_id, "user_id": user_id})

            student_info = {
                "id": user_data["_id"],
                "name": user_data.get("name", "Unknown"),
                "email": user_data.get("email", ""),
                "enrolled_at": course.get("created_at"),  # Mock enrollment date
                "progress": progress.get("overall_progress", 0) if progress else 0,
                "completed": progress.get("completed", False) if progress else False,
                "last_activity": progress.get("last_accessed") if progress else None
            }
            students.append(student_info)

    return students


@analytics_router.get("/instructor/{instructor_id}/overview")
async def get_instructor_overview(instructor_id: str, user=Depends(_current_user)):
    """Get overview analytics for an instructor"""
    if user["id"] != instructor_id and user["role"] != "admin":
        raise HTTPException(403, "Not authorized")

    db = get_database()

    # Get instructor's courses
    courses = await db.courses.find({"owner_id": instructor_id}).to_list(100)

    total_students = 0
    total_revenue = 0
    course_performance = []

    for course in courses:
        enrolled_count = len(course.get("enrolled_user_ids", []))
        total_students += enrolled_count

        # Get course analytics
        progress_data = await db.course_progress.find({"course_id": course["_id"]}).to_list(100)
        completion_rate = 0
        if progress_data:
            completed = len([p for p in progress_data if p.get("completed")])
            completion_rate = (completed / len(progress_data)) * 100

        course_performance.append({
            "course_id": course["_id"],
            "title": course.get("title", ""),
            "enrollments": enrolled_count,
            "completion_rate": round(completion_rate, 1),
            "average_rating": 4.5  # Mock data
        })

    return {
        "total_courses": len(courses),
        "total_students": total_students,
        "total_revenue": total_revenue,
        "average_rating": 4.3,
        "course_performance": course_performance,
        "recent_activity": [
            "New student enrolled in Advanced Python",
            "Course review received for Machine Learning Basics",
            "Quiz completed by 15 students"
        ]
    }
