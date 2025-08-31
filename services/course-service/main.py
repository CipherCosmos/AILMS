"""
Course Service - Handles course management, lessons, and content
"""
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Body
from typing import List, Optional
import json
import re
import math
from datetime import datetime, timezone
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.config.config import settings
from shared.database.database import get_database, _insert_one, _update_one, _find_one, _require
from shared.models.models import (
    Course,
    CourseCreate,
    CourseUpdate,
    GenerateCourseRequest,
    CourseLesson,
    LessonCreate,
    QuizQuestion,
    QuizOption,
    QuizSubmitRequest,
    TranscriptBody,
    CourseProgress,
    Certificate,
)

app = FastAPI(title='Course Service', version='1.0.0')

# AI integrations
try:
    import google.generativeai as genai
except Exception:
    genai = None

def _get_ai():
    """Get AI model instance"""
    if genai is None:
        raise HTTPException(
            status_code=500,
            detail="AI dependency not installed. Please install google-generativeai.",
        )
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=500,
            detail="No AI key configured. Set GEMINI_API_KEY in backend/.env",
        )
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(settings.default_llm_model)

def _safe_json_extract(text: str) -> dict:
    """Extract JSON from AI response safely"""
    if not isinstance(text, str):
        text = str(text)
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    raise ValueError("Could not parse JSON from AI response")

# Import auth functions (simplified for service communication)
async def _current_user(token: Optional[str] = None):
    """Mock user authentication for service-to-service calls"""
    # In production, this would validate JWT tokens from API Gateway
    return {"id": "user_123", "role": "instructor", "email": "user@example.com", "name": "Test User"}

def _require_role(user, allowed: list[str]):
    """Check if user has required role"""
    if user.get("role") not in allowed:
        raise HTTPException(403, "Insufficient permissions")

@app.post("/courses", response_model=Course)
async def create_course(body: CourseCreate, user=Depends(_current_user)):
    """Create a new course"""
    _require_role(user, ["admin", "instructor"])
    course = Course(
        owner_id=user["id"],
        title=body.title,
        audience=body.audience,
        difficulty=body.difficulty,
    )
    doc = course.dict()
    doc["_id"] = course.id
    db = get_database()
    await db.courses.insert_one(doc)
    return course

@app.get("/courses", response_model=List[Course])
async def list_courses(user=Depends(_current_user)):
    """List courses with visibility filtering"""
    q = (
        {}
        if user["role"] in ["admin", "auditor"]
        else {
            "$or": [
                {"published": True},
                {"owner_id": user["id"]},
                {"enrolled_user_ids": user["id"]},
            ]
        }
    )
    db = get_database()
    docs = await db.courses.find(q).sort("created_at", -1).to_list(200)

    # Convert _id to id and handle legacy data
    valid_courses = []
    for doc in docs:
        if "_id" in doc and "id" not in doc:
            doc["id"] = doc["_id"]

        # Skip courses missing required fields (legacy data)
        if not doc.get("title") and not doc.get("topic"):
            continue
        if not doc.get("owner_id"):
            continue

        # Handle legacy courses that have 'topic' instead of 'title'
        if not doc.get("title") and doc.get("topic"):
            doc["title"] = doc["topic"]

        # Ensure all required fields have defaults
        doc.setdefault("audience", "General")
        doc.setdefault("difficulty", "beginner")
        doc.setdefault("lessons", [])
        doc.setdefault("quiz", [])
        doc.setdefault("published", False)
        doc.setdefault("enrolled_user_ids", [])

        try:
            valid_courses.append(Course(**doc))
        except Exception as e:
            print(f"Skipping invalid course {doc.get('id', 'unknown')}: {e}")
            continue

    return valid_courses

@app.get("/courses/{cid}", response_model=Course)
async def get_course(cid: str, user=Depends(_current_user)):
    """Get a specific course"""
    doc = await _require("courses", {"_id": cid}, "Course not found")
    # visibility
    if not (
        doc.get("published")
        or doc.get("owner_id") == user["id"]
        or user["role"] in ["admin", "auditor"]
        or user["id"] in doc.get("enrolled_user_ids", [])
    ):
        raise HTTPException(403, "Not authorized to view course")
    return Course(**doc)

@app.put("/courses/{cid}", response_model=Course)
async def update_course(cid: str, body: CourseUpdate, user=Depends(_current_user)):
    """Update a course"""
    doc = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] in ["admin", "instructor"] or doc.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    changes = {k: v for k, v in body.dict().items() if v is not None}
    await _update_one("courses", {"_id": cid}, changes)
    doc.update(changes)
    return Course(**doc)

@app.post("/courses/{cid}/enroll")
async def enroll_course(cid: str, user=Depends(_current_user)):
    """Enroll user in course"""
    await _require("courses", {"_id": cid}, "Course not found")
    db = get_database()
    await db.courses.update_one(
        {"_id": cid}, {"$addToSet": {"enrolled_user_ids": user["id"]}}
    )
    return {"status": "enrolled"}

@app.post("/courses/ai/generate_course", response_model=Course)
async def generate_course(req: GenerateCourseRequest, user=Depends(_current_user)):
    """Generate course using AI"""
    _require_role(user, ["admin", "instructor"])

    try:
        # Generate course structure
        course_data = await _generate_course_structure(
            req.topic, req.audience, req.difficulty, req.lessons_count
        )

        # Generate detailed content for each lesson
        detailed_lessons = []
        for i, lesson_outline in enumerate(course_data.get("lessons", [])):
            lesson_content = await _generate_detailed_lesson(
                lesson_outline, req.topic, req.audience, req.difficulty, i + 1
            )
            detailed_lessons.append(lesson_content)

        # Generate quizzes
        quizzes = await _generate_course_quizzes(
            detailed_lessons, req.topic, req.difficulty
        )

        # Create course
        course = Course(
            owner_id=user["id"],
            title=course_data.get("title", f"AI Generated: {req.topic}"),
            audience=course_data.get("audience", req.audience),
            difficulty=course_data.get("difficulty", req.difficulty),
            lessons=detailed_lessons,
            quiz=quizzes,
        )

        doc = course.dict()
        doc["_id"] = course.id
        doc["generated_content"] = course_data

        db = get_database()
        await db.courses.insert_one(doc)
        return course

    except Exception as e:
        raise HTTPException(500, f"AI course generation failed: {str(e)}")

async def _generate_course_structure(topic: str, audience: str, difficulty: str, lesson_count: int) -> dict:
    """Generate course structure using AI"""
    prompt = f"""
    Create a detailed course structure for: {topic}
    Target Audience: {audience}
    Difficulty Level: {difficulty}
    Number of Lessons: {lesson_count}

    Return JSON with:
    {{
        "title": "Course title",
        "description": "Course description",
        "learning_objectives": ["objective1", "objective2"],
        "prerequisites": ["prereq1", "prereq2"],
        "lessons": [
            {{
                "id": "lesson_1",
                "title": "Lesson Title",
                "overview": "Brief overview",
                "duration_minutes": 90,
                "key_concepts": ["concept1", "concept2"],
                "learning_outcomes": ["outcome1", "outcome2"]
            }}
        ]
    }}
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return _safe_json_extract(response.text)
    except Exception as e:
        raise HTTPException(500, f"Course structure generation failed: {e}")

async def _generate_detailed_lesson(lesson_outline: dict, topic: str, audience: str, difficulty: str, lesson_number: int) -> dict:
    """Generate detailed lesson content"""
    lesson_title = lesson_outline.get("title", "")
    key_concepts = lesson_outline.get("key_concepts", [])

    prompt = f"""
    Create comprehensive content for Lesson {lesson_number}: {lesson_title}
    Course Topic: {topic}
    Target Audience: {audience}
    Difficulty Level: {difficulty}

    Key Concepts: {', '.join(key_concepts)}

    Provide detailed lesson content including:
    - Step-by-step explanations
    - Real-world examples
    - Practical exercises
    - Code examples (if applicable)
    - Common mistakes and solutions
    - Further reading resources

    Make the content engaging and comprehensive (600-1000 words).
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)

        return {
            "id": lesson_outline.get("id", f"lesson_{lesson_number}"),
            "title": lesson_title,
            "content": response.text,
            "duration_minutes": lesson_outline.get("duration_minutes", 90),
            "key_concepts": key_concepts,
            "learning_outcomes": lesson_outline.get("learning_outcomes", []),
            "order_index": lesson_number - 1
        }
    except Exception as e:
        raise HTTPException(500, f"Detailed lesson generation failed: {e}")

async def _generate_course_quizzes(lessons: list, topic: str, difficulty: str) -> list:
    """Generate quizzes for the course"""
    prompt = f"""
    Create a comprehensive quiz for the course: {topic}
    Difficulty: {difficulty}
    Course has {len(lessons)} lessons

    Generate 20 multiple choice questions covering all major concepts.
    Each question should have 4 options with exactly one correct answer.

    Return format:
    [
        {{
            "question": "Question text",
            "options": [
                {{"text": "Option 1", "is_correct": false}},
                {{"text": "Option 2", "is_correct": true}},
                ...
            ],
            "explanation": "Explanation of correct answer"
        }}
    ]
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        quiz_data = _safe_json_extract(response.text)

        quizzes = []
        for q in quiz_data[:20]:  # Limit to 20 questions
            options = [
                QuizOption(text=opt.get("text", ""), is_correct=bool(opt.get("is_correct", False)))
                for opt in q.get("options", [])[:4]
            ]
            if options:
                quiz_question = QuizQuestion(
                    question=q.get("question", ""),
                    options=options,
                    explanation=q.get("explanation", "")
                )
                quizzes.append(quiz_question)

        return quizzes
    except Exception:
        return []

@app.post("/courses/{cid}/lessons", response_model=Course)
async def add_lesson(cid: str, body: LessonCreate, user=Depends(_current_user)):
    """Add lesson to course"""
    course = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    lesson = CourseLesson(title=body.title, content=body.content)
    db = get_database()
    await db.courses.update_one({"_id": cid}, {"$push": {"lessons": lesson.dict()}})
    course["lessons"].append(lesson.dict())
    return Course(**course)

@app.post("/courses/{cid}/progress")
async def update_progress(cid: str, progress_data: dict, user=Depends(_current_user)):
    """Update course progress"""
    course = await _require("courses", {"_id": cid}, "Course not found")
    if user["id"] not in course.get("enrolled_user_ids", []):
        raise HTTPException(403, "Not enrolled in course")

    db = get_database()
    progress_doc = await db.course_progress.find_one({"course_id": cid, "user_id": user["id"]})
    if not progress_doc:
        progress_doc = {"course_id": cid, "user_id": user["id"], "lessons_progress": [], "overall_progress": 0, "completed": False}

    lesson_id = progress_data.get("lesson_id")
    completed = progress_data.get("completed", False)
    quiz_score = progress_data.get("quiz_score")

    lesson_progress = next((lp for lp in progress_doc["lessons_progress"] if lp["lesson_id"] == lesson_id), None)
    if not lesson_progress:
        lesson_progress = {"lesson_id": lesson_id, "completed": False}
        progress_doc["lessons_progress"].append(lesson_progress)

    if completed and not lesson_progress["completed"]:
        lesson_progress["completed"] = True
        lesson_progress["completed_at"] = datetime.now(timezone.utc)

    if quiz_score is not None:
        lesson_progress["quiz_score"] = quiz_score
        lesson_progress["quiz_completed"] = True
        lesson_progress["quiz_completed_at"] = datetime.now(timezone.utc)

    # Calculate overall progress
    total_lessons = len(course.get("lessons", []))
    completed_lessons = sum(1 for lp in progress_doc["lessons_progress"] if lp["completed"])
    progress_doc["overall_progress"] = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

    if progress_doc["overall_progress"] >= 100 and not progress_doc.get("completed", False):
        progress_doc["completed"] = True
        progress_doc["completed_at"] = datetime.now(timezone.utc)

    await db.course_progress.update_one(
        {"course_id": cid, "user_id": user["id"]},
        {"$set": progress_doc},
        upsert=True
    )
    return {"progress": progress_doc.get("overall_progress", 0), "completed": progress_doc.get("completed", False)}

@app.get("/courses/{cid}/progress")
async def get_progress(cid: str, user=Depends(_current_user)):
    """Get course progress"""
    await _require("courses", {"_id": cid}, "Course not found")
    db = get_database()
    progress = await db.course_progress.find_one({"course_id": cid, "user_id": user["id"]})
    return progress or {"course_id": cid, "user_id": user["id"], "lessons_progress": [], "overall_progress": 0.0, "completed": False}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "course"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Course Service", "status": "running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=settings.environment == 'development')