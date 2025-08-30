from fastapi import APIRouter, Depends
from database import get_database
from auth import _current_user, _require_role

analytics_router = APIRouter()


@analytics_router.get("/instructor")
async def instructor_analytics(user=Depends(_current_user)):
    _require_role(user, ["admin", "instructor"])
    q = {"owner_id": user["id"]} if user["role"] == "instructor" else {}
    db = get_database()
    courses = await db.courses.find(q).to_list(1000)
    total_students = sum(len(c.get("enrolled_user_ids", [])) for c in courses)
    return {"courses": len(courses), "students": total_students}


@analytics_router.get("/admin")
async def admin_analytics(user=Depends(_current_user)):
    _require_role(user, ["admin"])
    db = get_database()
    users = await db.users.count_documents({})
    courses = await db.courses.count_documents({})
    submissions = await db.submissions.count_documents({})
    return {"users": users, "courses": courses, "submissions": submissions}


@analytics_router.get("/student")
async def student_analytics(user=Depends(_current_user)):
    _require_role(user, ["student"])  # auditor sees via course list
    db = get_database()
    my_courses = await db.courses.count_documents({"enrolled_user_ids": user["id"]})
    my_subs = await db.submissions.count_documents({"user_id": user["id"]})
    return {"enrolled_courses": my_courses, "submissions": my_subs}


# Advanced AI Analytics
@analytics_router.get("/ai/course/{cid}")
async def ai_course_analytics(cid: str, user=Depends(_current_user)):
    from database import get_database
    db = get_database()

    # Get course data
    course = await db.courses.find_one({"_id": cid})
    if not course:
        raise HTTPException(404, "Course not found")

    # Check permissions
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")

    # Get all students in course
    enrolled_students = course.get("enrolled_user_ids", [])

    # Get progress data
    progress_data = await db.course_progress.find({"course_id": cid}).to_list(1000)

    # Get assignment data
    assignments = await db.assignments.find({"course_id": cid}).to_list(100)
    assignment_ids = [a["_id"] for a in assignments]

    # Get submissions
    submissions = await db.submissions.find({"assignment_id": {"$in": assignment_ids}}).to_list(1000)

    # AI Analysis
    analysis = {
        "enrollment_trends": len(enrolled_students),
        "completion_rate": len([p for p in progress_data if p.get("completed")]) / len(enrolled_students) * 100 if enrolled_students else 0,
        "average_progress": sum(p.get("overall_progress", 0) for p in progress_data) / len(progress_data) if progress_data else 0,
        "submission_rate": len(submissions) / (len(assignments) * len(enrolled_students)) * 100 if assignments and enrolled_students else 0,
        "at_risk_students": [],
        "performance_insights": []
    }

    # Identify at-risk students
    for progress in progress_data:
        if progress.get("overall_progress", 0) < 30:
            student_id = progress["user_id"]
            analysis["at_risk_students"].append({
                "student_id": student_id,
                "progress": progress.get("overall_progress", 0),
                "recommendations": ["Review foundational concepts", "Schedule office hours"]
            })

    # Performance insights
    if analysis["completion_rate"] < 50:
        analysis["performance_insights"].append("Low completion rate - consider revising course difficulty")
    if analysis["submission_rate"] < 60:
        analysis["performance_insights"].append("Low submission rate - check assignment clarity")

    return analysis


@analytics_router.get("/ai/student/{sid}")
async def ai_student_analytics(sid: str, user=Depends(_current_user)):
    from database import get_database
    db = get_database()

    # Check permissions
    if not (user["role"] == "admin" or user["id"] == sid):
        raise HTTPException(403, "Not authorized")

    # Get student's courses
    enrolled_courses = await db.courses.find({"enrolled_user_ids": sid}).to_list(100)

    # Get progress data
    progress_data = await db.course_progress.find({"user_id": sid}).to_list(100)

    # Get submissions
    submissions = await db.submissions.find({"user_id": sid}).to_list(100)

    # AI Analysis
    analysis = {
        "total_courses": len(enrolled_courses),
        "completed_courses": len([p for p in progress_data if p.get("completed")]),
        "average_progress": sum(p.get("overall_progress", 0) for p in progress_data) / len(progress_data) if progress_data else 0,
        "total_submissions": len(submissions),
        "learning_pattern": "consistent" if len(submissions) > 5 else "needs_improvement",
        "recommendations": []
    }

    # Generate recommendations
    if analysis["average_progress"] < 50:
        analysis["recommendations"].append("Focus on completing current courses before new enrollments")
    if analysis["total_submissions"] < 3:
        analysis["recommendations"].append("Increase assignment submission frequency")

    # Learning style analysis (simplified)
    if len(enrolled_courses) > 3:
        analysis["recommendations"].append("Consider specializing in fewer subjects for better mastery")

    return analysis
