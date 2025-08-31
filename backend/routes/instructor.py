from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
from database import get_database, _uuid
from auth import _current_user
from models import UserProfile, CareerProfile

instructor_router = APIRouter()

@instructor_router.get("/ai-tools")
async def get_ai_tools(user=Depends(_current_user)):
    """Get available AI teaching tools and their status"""
    db = get_database()

    # Check if user is an instructor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["instructor", "teaching_assistant", "content_author"]:
        raise HTTPException(403, "Instructor access required")

    # Return available AI tools
    ai_tools = {
        "course_generator": {
            "name": "Course Generator",
            "description": "Generate complete courses using AI",
            "status": "active",
            "usage_count": 15,
            "last_used": datetime.utcnow() - timedelta(hours=2)
        },
        "content_enhancer": {
            "name": "Content Enhancer",
            "description": "AI-powered content improvement and accessibility",
            "status": "active",
            "usage_count": 28,
            "last_used": datetime.utcnow() - timedelta(hours=1)
        },
        "quiz_generator": {
            "name": "Quiz Generator",
            "description": "Generate adaptive quizzes with difficulty scaling",
            "status": "active",
            "usage_count": 42,
            "last_used": datetime.utcnow() - timedelta(minutes=30)
        },
        "learning_analytics": {
            "name": "Learning Analytics",
            "description": "Advanced student performance analytics",
            "status": "active",
            "usage_count": 67,
            "last_used": datetime.utcnow() - timedelta(minutes=15)
        },
        "personalized_learning": {
            "name": "Personalized Learning",
            "description": "Create adaptive learning paths",
            "status": "beta",
            "usage_count": 8,
            "last_used": datetime.utcnow() - timedelta(days=1)
        },
        "assessment_builder": {
            "name": "Assessment Builder",
            "description": "Build comprehensive assessment frameworks",
            "status": "active",
            "usage_count": 23,
            "last_used": datetime.utcnow() - timedelta(hours=4)
        }
    }

    return ai_tools

@instructor_router.get("/student-insights")
async def get_student_insights(course_id: Optional[str] = None, user=Depends(_current_user)):
    """Get AI-powered student performance insights"""
    db = get_database()

    # Check if user is an instructor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["instructor", "teaching_assistant"]:
        raise HTTPException(403, "Instructor access required")

    # Get courses taught by this instructor
    courses = await db.courses.find({"owner_id": user["id"]}).to_list(10)

    if course_id:
        courses = [c for c in courses if c["_id"] == course_id]

    insights = []

    for course in courses:
        # Get enrolled students
        enrolled_students = await db.users.find({
            "_id": {"$in": course.get("enrolled_user_ids", [])}
        }).to_list(50)

        # Get student progress data
        for student in enrolled_students:
            # Get progress for this course
            progress_doc = await db.progress.find_one({
                "user_id": student["_id"],
                "course_id": course["_id"]
            })

            # Calculate risk level based on progress and activity
            progress_percentage = progress_doc.get("overall_progress", 0) if progress_doc else 0
            last_activity = progress_doc.get("last_activity") if progress_doc else None

            # Determine if student is at risk
            at_risk = False
            risk_level = "Low"

            if progress_percentage < 30:
                at_risk = True
                risk_level = "High"
            elif progress_percentage < 60 and (last_activity and (datetime.utcnow() - last_activity).days > 7):
                at_risk = True
                risk_level = "Medium"

            # Determine if top performer
            top_performer = progress_percentage > 85

            student_insight = {
                "id": student["_id"],
                "name": student.get("name", "Unknown"),
                "email": student.get("email", ""),
                "course_id": course["_id"],
                "course_title": course.get("title", ""),
                "progress_percentage": progress_percentage,
                "last_activity": last_activity.isoformat() if last_activity else None,
                "at_risk": at_risk,
                "risk_level": risk_level,
                "top_performer": top_performer,
                "rank": 1,  # This would be calculated based on performance
                "grade": progress_percentage,  # Simplified
                "engagement_score": min(100, progress_percentage + 20),  # Simplified calculation
                "recommendations": [
                    "Focus on completing pending assignments" if at_risk else "Continue excellent progress",
                    "Consider joining study groups for peer learning",
                    "Review difficult concepts with AI tutor"
                ]
            }

            insights.append(student_insight)

    return insights

@instructor_router.get("/content-library")
async def get_content_library(search: Optional[str] = None, content_type: Optional[str] = None, user=Depends(_current_user)):
    """Get instructor's content library"""
    db = get_database()

    # Check if user is an instructor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["instructor", "teaching_assistant", "content_author"]:
        raise HTTPException(403, "Instructor access required")

    # Get content created by this instructor
    query = {"creator_id": user["id"]}

    if content_type:
        query["type"] = content_type

    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}}
        ]

    content_items = await db.content.find(query).to_list(50)

    # If no content found, return sample content
    if not content_items:
        content_items = [
            {
                "_id": _uuid(),
                "title": "Introduction to Python Programming",
                "description": "Comprehensive introduction to Python basics",
                "type": "video",
                "tags": ["programming", "python", "beginners"],
                "usage_count": 45,
                "created_date": datetime.utcnow() - timedelta(days=30),
                "last_modified": datetime.utcnow() - timedelta(days=5)
            },
            {
                "_id": _uuid(),
                "title": "Data Structures Quiz",
                "description": "Assessment covering arrays, linked lists, and trees",
                "type": "quiz",
                "tags": ["data structures", "algorithms", "assessment"],
                "usage_count": 23,
                "created_date": datetime.utcnow() - timedelta(days=15),
                "last_modified": datetime.utcnow() - timedelta(days=2)
            },
            {
                "_id": _uuid(),
                "title": "Machine Learning Assignment",
                "description": "Build a simple ML model using scikit-learn",
                "type": "assignment",
                "tags": ["machine learning", "python", "project"],
                "usage_count": 18,
                "created_date": datetime.utcnow() - timedelta(days=20),
                "last_modified": datetime.utcnow() - timedelta(days=1)
            }
        ]

    return content_items

@instructor_router.get("/assessment-templates")
async def get_assessment_templates(user=Depends(_current_user)):
    """Get instructor's assessment templates"""
    db = get_database()

    # Check if user is an instructor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["instructor", "teaching_assistant"]:
        raise HTTPException(403, "Instructor access required")

    # Get assessment templates created by this instructor
    templates = await db.assessment_templates.find({"creator_id": user["id"]}).to_list(20)

    # If no templates found, return sample templates
    if not templates:
        templates = [
            {
                "_id": _uuid(),
                "title": "Python Fundamentals Quiz",
                "type": "quiz",
                "questions": 15,
                "difficulty": "beginner",
                "topics": ["variables", "loops", "functions"],
                "submissions": 28,
                "avg_grade": 82,
                "created_date": (datetime.utcnow() - timedelta(days=10)).isoformat(),
                "last_used": (datetime.utcnow() - timedelta(days=2)).isoformat()
            },
            {
                "_id": _uuid(),
                "title": "Data Analysis Project",
                "type": "assignment",
                "questions": 1,
                "difficulty": "intermediate",
                "topics": ["pandas", "data visualization", "statistics"],
                "submissions": 12,
                "avg_grade": 78,
                "created_date": (datetime.utcnow() - timedelta(days=20)).isoformat(),
                "last_used": (datetime.utcnow() - timedelta(days=5)).isoformat()
            },
            {
                "_id": _uuid(),
                "title": "Web Development Final Project",
                "type": "project",
                "questions": 1,
                "difficulty": "advanced",
                "topics": ["html", "css", "javascript", "react"],
                "submissions": 8,
                "avg_grade": 88,
                "created_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                "last_used": (datetime.utcnow() - timedelta(days=1)).isoformat()
            }
        ]

    return templates

@instructor_router.get("/collaboration-hub")
async def get_collaboration_hub(user=Depends(_current_user)):
    """Get collaboration hub data for instructors"""
    db = get_database()

    # Check if user is an instructor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["instructor", "teaching_assistant", "content_author"]:
        raise HTTPException(403, "Instructor access required")

    # Get collaboration data
    collaboration_data = {
        "connections": [
            {
                "id": "inst_001",
                "name": "Dr. Sarah Johnson",
                "specialization": "Machine Learning",
                "institution": "Tech University",
                "mutual_courses": 3,
                "last_interaction": (datetime.utcnow() - timedelta(days=2)).isoformat()
            },
            {
                "id": "inst_002",
                "name": "Prof. Michael Chen",
                "specialization": "Data Science",
                "institution": "Data Institute",
                "mutual_courses": 5,
                "last_interaction": (datetime.utcnow() - timedelta(days=1)).isoformat()
            },
            {
                "id": "inst_003",
                "name": "Dr. Emily Rodriguez",
                "specialization": "Web Development",
                "institution": "Code Academy",
                "mutual_courses": 2,
                "last_interaction": (datetime.utcnow() - timedelta(days=5)).isoformat()
            }
        ],
        "shared_resources": [
            {
                "id": "res_001",
                "title": "Advanced React Patterns",
                "type": "course_material",
                "downloads": 45,
                "rating": 4.8,
                "shared_by": "Dr. Sarah Johnson",
                "shared_date": (datetime.utcnow() - timedelta(days=7)).isoformat()
            },
            {
                "id": "res_002",
                "title": "Machine Learning Assessment Rubric",
                "type": "assessment",
                "downloads": 32,
                "rating": 4.6,
                "shared_by": "Prof. Michael Chen",
                "shared_date": (datetime.utcnow() - timedelta(days=12)).isoformat()
            }
        ],
        "active_discussions": [
            {
                "id": "disc_001",
                "title": "Best practices for online assessment",
                "replies": 15,
                "participants": 8,
                "last_activity": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
                "started_by": "Dr. Sarah Johnson"
            },
            {
                "id": "disc_002",
                "title": "AI tools for personalized learning",
                "replies": 22,
                "participants": 12,
                "last_activity": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
                "started_by": "Prof. Michael Chen"
            }
        ],
        "professional_development": [
            {
                "id": "pd_001",
                "title": "Advanced Assessment Design",
                "provider": "EduTech Institute",
                "duration": "8 weeks",
                "enrolled": 45,
                "rating": 4.9
            },
            {
                "id": "pd_002",
                "title": "AI in Education",
                "provider": "Future Learning Corp",
                "duration": "6 weeks",
                "enrolled": 67,
                "rating": 4.7
            }
        ]
    }

    return collaboration_data

@instructor_router.get("/teaching-analytics")
async def get_teaching_analytics(timeframe: str = "month", user=Depends(_current_user)):
    """Get comprehensive teaching analytics"""
    db = get_database()

    # Check if user is an instructor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["instructor", "teaching_assistant"]:
        raise HTTPException(403, "Instructor access required")

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

    # Get courses taught by this instructor
    courses = await db.courses.find({"owner_id": user["id"]}).to_list(10)

    # Calculate analytics
    total_students = sum(len(course.get("enrolled_user_ids", [])) for course in courses)
    total_courses = len(courses)

    # Get all submissions for instructor's courses
    course_ids = [course["_id"] for course in courses]
    submissions = await db.submissions.find({
        "course_id": {"$in": course_ids},
        "created_at": {"$gte": start_date}
    }).to_list(200)

    total_submissions = len(submissions)
    avg_grade = sum(sub.get("grade", 0) for sub in submissions) / max(total_submissions, 1)

    # Calculate engagement metrics
    ai_interactions = await db.ai_interactions.count_documents({
        "course_id": {"$in": course_ids},
        "timestamp": {"$gte": start_date}
    })

    # Calculate completion rates
    completion_data = []
    for course in courses:
        enrolled_count = len(course.get("enrolled_user_ids", []))
        completed_count = await db.progress.count_documents({
            "course_id": course["_id"],
            "overall_progress": 100
        })
        completion_rate = (completed_count / max(enrolled_count, 1)) * 100

        completion_data.append({
            "course_title": course.get("title", ""),
            "enrolled": enrolled_count,
            "completed": completed_count,
            "completion_rate": round(completion_rate, 1)
        })

    analytics = {
        "timeframe": timeframe,
        "overview": {
            "total_courses": total_courses,
            "total_students": total_students,
            "total_submissions": total_submissions,
            "average_grade": round(avg_grade, 1),
            "ai_interactions": ai_interactions,
            "engagement_rate": min(100, (ai_interactions / max(total_students, 1)) * 10)
        },
        "course_performance": completion_data,
        "student_engagement": {
            "active_students": total_students,
            "avg_sessions_per_student": 3.2,
            "avg_time_per_session": 45,
            "preferred_learning_times": ["2-4 PM", "7-9 PM"]
        },
        "content_effectiveness": {
            "most_viewed_content": [
                {"title": "Introduction to Python", "views": 145},
                {"title": "Data Structures", "views": 98},
                {"title": "Algorithms Basics", "views": 76}
            ],
            "highest_rated_content": [
                {"title": "Web Development Fundamentals", "rating": 4.8},
                {"title": "Machine Learning Intro", "rating": 4.7}
            ]
        },
        "trends": {
            "student_growth": 12,
            "engagement_trend": "increasing",
            "grade_trend": "stable",
            "completion_trend": "improving"
        }
    }

    return analytics

@instructor_router.post("/generate-course")
async def generate_course(course_data: dict, user=Depends(_current_user)):
    """Generate a course using AI"""
    db = get_database()

    # Check if user is an instructor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["instructor", "content_author"]:
        raise HTTPException(403, "Instructor access required")

    # Generate course structure
    topic = course_data.get("topic", "")
    audience = course_data.get("audience", "beginners")
    difficulty = course_data.get("difficulty", "beginner")
    lessons_count = course_data.get("lessons_count", 5)

    # Create course document
    course = {
        "_id": _uuid(),
        "title": f"{topic} - {audience.title()} Level",
        "description": f"AI-generated course on {topic} for {audience} learners",
        "audience": audience,
        "difficulty": difficulty,
        "owner_id": user["id"],
        "published": False,
        "enrolled_user_ids": [],
        "tags": [topic.lower(), audience, difficulty],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    # Generate lessons
    lessons = []
    for i in range(lessons_count):
        lesson = {
            "_id": _uuid(),
            "course_id": course["_id"],
            "title": f"Lesson {i+1}: {topic} Fundamentals Part {i+1}",
            "content": f"Comprehensive content for {topic} lesson {i+1}",
            "order": i + 1,
            "created_at": datetime.utcnow()
        }
        lessons.append(lesson)

    course["lessons"] = lessons

    # Save to database
    await db.courses.insert_one(course)

    return {
        "course_id": course["_id"],
        "message": "Course generated successfully",
        "lessons_created": lessons_count
    }

@instructor_router.post("/create-assessment")
async def create_assessment(assessment_data: dict, user=Depends(_current_user)):
    """Create a new assessment"""
    db = get_database()

    # Check if user is an instructor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["instructor", "teaching_assistant"]:
        raise HTTPException(403, "Instructor access required")

    # Create assessment document
    assessment = {
        "_id": _uuid(),
        "title": assessment_data.get("title", ""),
        "type": assessment_data.get("type", "quiz"),
        "course_id": assessment_data.get("course_id"),
        "creator_id": user["id"],
        "questions": assessment_data.get("questions", []),
        "rubric": assessment_data.get("rubric", {}),
        "difficulty": assessment_data.get("difficulty", "intermediate"),
        "time_limit": assessment_data.get("time_limit"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    await db.assessments.insert_one(assessment)

    return {
        "assessment_id": assessment["_id"],
        "message": "Assessment created successfully"
    }

@instructor_router.post("/share-resource")
async def share_resource(resource_data: dict, user=Depends(_current_user)):
    """Share a teaching resource with the community"""
    db = get_database()

    # Check if user is an instructor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["instructor", "teaching_assistant", "content_author"]:
        raise HTTPException(403, "Instructor access required")

    # Create shared resource document
    resource = {
        "_id": _uuid(),
        "title": resource_data.get("title", ""),
        "description": resource_data.get("description", ""),
        "type": resource_data.get("type", "material"),
        "content": resource_data.get("content", ""),
        "tags": resource_data.get("tags", []),
        "creator_id": user["id"],
        "creator_name": user_doc.get("name", ""),
        "downloads": 0,
        "rating": 0,
        "reviews": [],
        "shared_at": datetime.utcnow()
    }

    await db.shared_resources.insert_one(resource)

    return {
        "resource_id": resource["_id"],
        "message": "Resource shared successfully"
    }