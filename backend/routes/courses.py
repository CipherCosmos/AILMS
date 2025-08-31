from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional
import json
import re
import math
from database import get_database, _insert_one, _update_one, _find_one, _require
from auth import _current_user, _require_role
from models import (
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
from config import settings
import uuid
from datetime import datetime, timezone
from utils import serialize_mongo_doc
from bson import ObjectId
from pydantic import BaseModel

# AI integrations
try:
    import google.generativeai as genai
except Exception:
    genai = None


def _get_ai():
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


courses_router = APIRouter()


@courses_router.post("", response_model=Course)
async def create_course(body: CourseCreate, user=Depends(_current_user)):
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


@courses_router.get("", response_model=List[Course])
async def list_courses(user=Depends(_current_user)):
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


@courses_router.get("/{cid}", response_model=Course)
async def get_course(cid: str, user=Depends(_current_user)):
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


@courses_router.put("/{cid}", response_model=Course)
async def update_course(cid: str, body: CourseUpdate, user=Depends(_current_user)):
    doc = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] in ["admin", "instructor"] or doc.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    changes = {k: v for k, v in body.dict().items() if v is not None}
    await _update_one("courses", {"_id": cid}, changes)
    doc.update(changes)
    return Course(**doc)


@courses_router.post("/{cid}/enroll")
async def enroll_course(cid: str, user=Depends(_current_user)):
    await _require("courses", {"_id": cid}, "Course not found")
    db = get_database()
    await db.courses.update_one(
        {"_id": cid}, {"$addToSet": {"enrolled_user_ids": user["id"]}}
    )
    return {"status": "enrolled"}


@courses_router.post("/{cid}/lessons", response_model=Course)
async def add_lesson(cid: str, body: LessonCreate, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    lesson = CourseLesson(title=body.title, content=body.content)
    db = get_database()
    await db.courses.update_one({"_id": cid}, {"$push": {"lessons": lesson.dict()}})
    course["lessons"].append(lesson.dict())
    return Course(**course)


@courses_router.post("/ai/generate_course", response_model=Course)
async def generate_course(req: GenerateCourseRequest, user=Depends(_current_user)):
    _require_role(user, ["admin", "instructor"])  # only creators
    system_message = "You are an expert instructional designer. Output strict JSON."
    prompt = f"""
Create a complete course on the topic: {req.topic}
Audience: {req.audience}
Difficulty: {req.difficulty}
Number of lessons: {req.lessons_count}

Return ONLY JSON with this schema:
{{
  "title": string,
  "audience": string,
  "difficulty": string,
  "lessons": [
    {{"title": string, "content": string}} (exactly {req.lessons_count} items)
  ],
  "quiz": [
    {{
      "question": string,
      "options": [
        {{"text": string, "is_correct": boolean}},
        {{"text": string, "is_correct": boolean}},
        {{"text": string, "is_correct": boolean}},
        {{"text": string, "is_correct": boolean}}
      ],
      "explanation": string
    }}
  ]
}}
Ensure exactly one option is correct per question.
"""
    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        data = _safe_json_extract(response.text)
    except Exception as e:
        raise HTTPException(500, f"AI generation failed: {e}")

    # build model
    lessons = [
        CourseLesson(title=l.get("title", "Untitled"), content=l.get("content", ""))
        for l in data.get("lessons", [])
    ][: req.lessons_count]
    quiz: List[QuizQuestion] = []
    for q in data.get("quiz", [])[: max(3, req.lessons_count)]:
        options = [
            QuizOption(
                text=o.get("text", ""), is_correct=bool(o.get("is_correct", False))
            )
            for o in q.get("options", [])[:4]
        ]
        if sum(1 for o in options if o.is_correct) != 1 and options:
            for i, o in enumerate(options):
                o.is_correct = i == 0
        quiz.append(
            QuizQuestion(
                question=q.get("question", ""),
                options=options,
                explanation=q.get("explanation") or "",
            )
        )
    course = Course(
        owner_id=user["id"],
        title=data.get("title", req.topic),
        audience=data.get("audience", req.audience),
        difficulty=data.get("difficulty", req.difficulty),
        lessons=lessons,
        quiz=quiz,
    )
    doc = course.dict()
    doc["_id"] = course.id
    db = get_database()
    await db.courses.insert_one(doc)
    return course


@courses_router.post("/lessons/{lesson_id}/quiz/generate", response_model=QuizQuestion)
async def generate_quiz_for_lesson(lesson_id: str, user=Depends(_current_user)):
    db = get_database()
    course = await db.courses.find_one({"lessons.id": lesson_id})
    if not course:
        raise HTTPException(404, "Lesson not found")
    if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    lesson = next(
        (l for l in course.get("lessons", []) if l.get("id") == lesson_id), None
    )
    system_message = (
        "Generate a single high quality MCQ based on lesson content in strict JSON."
    )
    schema = (
        "{"
        + '"question": string, "options": [{"text": string, "is_correct": boolean} x4], "explanation": string'
        + "}"
    )
    prompt = f"Create 1 MCQ for lesson titled '{lesson.get('title')}'. Content: {lesson.get('content')}. Return ONLY JSON with schema {schema}."
    model = _get_ai()
    response = model.generate_content(prompt)
    data = _safe_json_extract(response.text)
    options = [
        QuizOption(text=o.get("text", ""), is_correct=bool(o.get("is_correct", False)))
        for o in data.get("options", [])[:4]
    ]
    if sum(1 for o in options if o.is_correct) != 1 and options:
        options[0].is_correct = True
        for i in range(1, len(options)):
            options[i].is_correct = False
    q = QuizQuestion(
        question=data.get("question", ""),
        options=options,
        explanation=data.get("explanation") or "",
    )
    await db.courses.update_one(
        {"_id": course["_id"], "lessons.id": lesson_id}, {"$push": {"quiz": q.dict()}}
    )
    return q


@courses_router.post("/quizzes/{course_id}/submit")
async def submit_quiz(
    course_id: str, body: QuizSubmitRequest, user=Depends(_current_user)
):
    course = await _require("courses", {"_id": course_id}, "Course not found")
    q = next(
        (qq for qq in course.get("quiz", []) if qq.get("id") == body.question_id), None
    )
    if not q:
        raise HTTPException(404, "Question not found")
    correct = False
    try:
        correct = bool(q.get("options", [])[body.selected_index].get("is_correct"))
    except Exception:
        correct = False
    return {"correct": correct, "explanation": q.get("explanation", "")}


@courses_router.post("/lessons/{lesson_id}/transcript")
async def upload_transcript(
    lesson_id: str, body: TranscriptBody, user=Depends(_current_user)
):
    db = get_database()
    course = await db.courses.find_one({"lessons.id": lesson_id})
    if not course:
        raise HTTPException(404, "Lesson not found")
    if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    await db.courses.update_one(
        {"_id": course["_id"], "lessons.id": lesson_id},
        {"$set": {"lessons.$.transcript_text": body.text}},
    )
    return {"status": "uploaded"}


@courses_router.post("/lessons/{lesson_id}/summary")
async def summarize_lesson(lesson_id: str, user=Depends(_current_user)):
    db = get_database()
    course = await db.courses.find_one({"lessons.id": lesson_id})
    if not course:
        raise HTTPException(404, "Lesson not found")
    lesson = next(
        (l for l in course.get("lessons", []) if l.get("id") == lesson_id), None
    )
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    if (user["role"] == "instructor" and course.get("owner_id") != user["id"]) or user["role"] not in ["admin", "instructor", "auditor", "student"]:
        raise HTTPException(403, "Not authorized")
    transcript = lesson.get("transcript_text") or lesson.get("content")
    model = _get_ai()
    prompt = f"Summarize this lesson transcript/content into JSON: {{'summary': string, 'highlights': [string]}}. Text: {transcript}"
    try:
        response = model.generate_content(prompt)
        data = _safe_json_extract(response.text.replace("'", '"'))
    except Exception:
        data = {"summary": "Summary unavailable", "highlights": []}
    await db.courses.update_one(
        {"_id": course["_id"], "lessons.id": lesson_id},
        {"$set": {"lessons.$.summary": data.get("summary")}},
    )
    return data


# Progress tracking
class ProgressUpdate(BaseModel):
    lesson_id: str
    completed: bool
    quiz_score: Optional[int] = None

@courses_router.post("/{cid}/progress")
async def update_progress(cid: str, progress_data: dict, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if user["id"] not in course.get("enrolled_user_ids", []):
        raise HTTPException(403, "Not enrolled in course")

    db = get_database()
    progress_doc = await db.course_progress.find_one({"course_id": cid, "user_id": user["id"]})
    if not progress_doc:
        progress_doc = {"course_id": cid, "user_id": user["id"], "lessons_progress": [], "overall_progress": 0, "completed": False}
    else:
        # Ensure existing documents have required fields
        progress_doc.setdefault("overall_progress", 0)
        progress_doc.setdefault("completed", False)
        progress_doc.setdefault("lessons_progress", [])

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

    # Handle quiz score
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


@courses_router.get("/{cid}/progress")
async def get_progress(cid: str, user=Depends(_current_user)):
    await _require("courses", {"_id": cid}, "Course not found")
    db = get_database()
    progress = await db.course_progress.find_one({"course_id": cid, "user_id": user["id"]})
    return progress or {"course_id": cid, "user_id": user["id"], "lessons_progress": [], "overall_progress": 0.0, "completed": False}


# Certificate generation
@courses_router.post("/{cid}/certificate")
async def generate_certificate(cid: str, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    db = get_database()
    progress = await db.course_progress.find_one({"course_id": cid, "user_id": user["id"]})
    if not progress or not progress.get("completed"):
        raise HTTPException(400, "Course not completed")

    if progress.get("certificate_issued"):
        raise HTTPException(400, "Certificate already issued")

    # Generate certificate data (simplified)
    certificate_data = {
        "student_name": user["name"],
        "course_title": course["title"],
        "completion_date": progress["completed_at"].isoformat(),
        "certificate_id": str(uuid.uuid4())
    }

    certificate = {
        "user_id": user["id"],
        "course_id": cid,
        "certificate_data": certificate_data
    }
    await db.certificates.insert_one(certificate)

    await db.course_progress.update_one(
        {"course_id": cid, "user_id": user["id"]},
        {"$set": {"certificate_issued": True}}
    )

    return certificate_data


# AI-Powered Recommendations
@courses_router.get("/basic_recommendations")
async def get_basic_recommendations(user=Depends(_current_user)):
    """Get personalized course recommendations for the user"""
    db = get_database()

    # Get user's current courses and progress
    user_courses = await db.courses.find({"enrolled_user_ids": user["id"]}).to_list(10)
    user_progress = await db.course_progress.find({"user_id": user["id"]}).to_list(10)

    # Get user's profile and preferences
    profile = await db.user_profiles.find_one({"user_id": user["id"]})
    preferences = await db.user_preferences.find_one({"user_id": user["id"]})

    # Simple recommendation logic based on completed courses and interests
    completed_course_ids = [p["course_id"] for p in user_progress if p.get("completed")]
    enrolled_course_ids = [str(c["_id"]) for c in user_courses]

    # Find courses user hasn't enrolled in
    all_courses = await db.courses.find({
        "_id": {"$nin": [ObjectId(cid) for cid in enrolled_course_ids if cid]},
        "published": True
    }).to_list(20)

    # Simple scoring based on difficulty and interests
    user_interests = (profile.get("interests", []) if profile else []) + (preferences.get("interests", []) if preferences else [])
    recommendations = []

    for course in all_courses[:10]:
        score = 0
        # Score based on interests match
        course_title_lower = course.get("title", "").lower()
        course_audience = course.get("audience", "").lower()

        for interest in user_interests:
            if interest.lower() in course_title_lower or interest.lower() in course_audience:
                score += 10

        # Score based on difficulty progression
        if completed_course_ids:
            # Prefer slightly harder courses than what they've completed
            completed_difficulties = []
            for cid in completed_course_ids:
                completed_course = await db.courses.find_one({"_id": ObjectId(cid)})
                if completed_course:
                    completed_difficulties.append(completed_course.get("difficulty", "beginner"))

            current_difficulty = course.get("difficulty", "beginner")
            if "advanced" in completed_difficulties and current_difficulty == "advanced":
                score += 15
            elif "intermediate" in completed_difficulties and current_difficulty in ["intermediate", "advanced"]:
                score += 10

        recommendations.append({
            "course": serialize_mongo_doc(course),
            "score": score,
            "reason": f"Based on your {'interests in ' + ', '.join(user_interests[:2]) if user_interests else 'course history'}"
        })

    # Sort by score
    recommendations.sort(key=lambda x: x["score"], reverse=True)

    return {"recommendations": recommendations}


# Learning Path Generation
@courses_router.get("/learning_path")
async def get_learning_path(user=Depends(_current_user)):
    """Generate a personalized learning path for the user"""
    db = get_database()

    # Get user's current state
    user_courses = await db.courses.find({"enrolled_user_ids": user["id"]}).to_list(20)
    user_progress = await db.course_progress.find({"user_id": user["id"]}).to_list(20)

    # Get user's profile and preferences
    profile = await db.user_profiles.find_one({"user_id": user["id"]})
    preferences = await db.user_preferences.find_one({"user_id": user["id"]})

    # Analyze current progress
    completed_courses = [p for p in user_progress if p.get("completed")]
    in_progress_courses = [p for p in user_progress if not p.get("completed") and p.get("overall_progress", 0) > 0]
    not_started_courses = [p for p in user_progress if not p.get("completed") and p.get("overall_progress", 0) == 0]

    # Generate learning path
    learning_path = {
        "current_focus": [],
        "upcoming_courses": [],
        "recommended_next": [],
        "completed_milestones": len(completed_courses),
        "total_enrolled": len(user_courses)
    }

    # Current focus: courses with progress but not completed
    for progress in in_progress_courses[:3]:
        course = await db.courses.find_one({"_id": ObjectId(progress["course_id"])})
        if course:
            learning_path["current_focus"].append({
                "course": serialize_mongo_doc(course),
                "progress": progress.get("overall_progress", 0),
                "next_steps": ["Complete remaining lessons", "Take final quiz"]
            })

    # Upcoming courses: enrolled but not started
    for progress in not_started_courses[:5]:
        course = await db.courses.find_one({"_id": ObjectId(progress["course_id"])})
        if course:
            learning_path["upcoming_courses"].append({
                "course": serialize_mongo_doc(course),
                "estimated_time": "2-4 hours",
                "prerequisites": []
            })

    # Recommended next courses
    all_courses = await db.courses.find({
        "_id": {"$nin": [ObjectId(str(c["_id"])) for c in user_courses]},
        "published": True
    }).to_list(10)

    for course in all_courses:
        learning_path["recommended_next"].append({
            "course": serialize_mongo_doc(course),
            "reason": "Complementary to your current learning path",
            "difficulty": course.get("difficulty", "beginner")
        })

    return learning_path


# Recommendations
@courses_router.get("/course_recommendations")
async def get_course_recommendations(user=Depends(_current_user)):
    # Get user's enrolled courses and progress
    enrolled_courses = await db.courses.find({"enrolled_user_ids": user["id"]}).to_list(100)
    enrolled_ids = [c["_id"] for c in enrolled_courses]

    # Get user's progress data
    progress_data = await db.course_progress.find({"user_id": user["id"]}).to_list(100)

    # Get all available courses
    all_courses = await db.courses.find({"published": True}).to_list(200)

    # Filter out already enrolled courses
    available_courses = [c for c in all_courses if c["_id"] not in enrolled_ids]

    # Simple recommendation logic based on difficulty and progress
    recommendations = []
    for course in available_courses[:10]:  # Limit to 10 recommendations
        # Calculate match score based on user's current progress
        match_score = 70  # Base score

        # Adjust based on difficulty progression
        if progress_data:
            avg_progress = sum(p.get("overall_progress", 0) for p in progress_data) / len(progress_data)
            if course.get("difficulty") == "beginner" and avg_progress > 80:
                match_score += 10  # Advanced user might want to review basics
            elif course.get("difficulty") == "intermediate" and avg_progress < 50:
                match_score -= 20  # Too advanced for beginner
            elif course.get("difficulty") == "advanced" and avg_progress > 70:
                match_score += 15  # Good match for advanced learner

        recommendations.append({
            "course_id": course["_id"],
            "title": course.get("title", ""),
            "difficulty": course.get("difficulty", "beginner"),
            "audience": course.get("audience", "General"),
            "score": min(100, match_score),
            "reasons": ["Based on your learning progress", "Matches your skill level"]
        })

    return recommendations


# My submissions
@courses_router.get("/my_submissions")
async def get_my_submissions(user=Depends(_current_user)):
    # Get all submissions by the user
    submissions = await db.submissions.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)

    # Enrich with assignment and course data
    enriched_submissions = []
    for sub in submissions:
        # Get assignment details
        assignment = await db.assignments.find_one({"_id": sub["assignment_id"]})
        if assignment:
            # Get course details
            course = await db.courses.find_one({"_id": assignment["course_id"]})
            if course:
                enriched_submissions.append({
                    "id": sub["_id"],
                    "assignment_title": assignment.get("title", "Unknown Assignment"),
                    "course_title": course.get("title", "Unknown Course"),
                    "created_at": sub.get("created_at"),
                    "ai_grade": sub.get("ai_grade"),
                    "status": "graded" if sub.get("ai_grade") else "pending"
                })

    return enriched_submissions




# Advanced AI-Powered Features
@courses_router.get("/ai/learning_path/{user_id}")
async def get_personalized_learning_path(user_id: str, user=Depends(_current_user)):
    """Generate AI-powered personalized learning path"""
    if user["id"] != user_id and user["role"] not in ["admin", "instructor"]:
        raise HTTPException(403, "Not authorized")

    db = get_database()

    # Get user's course history and performance
    user_courses = await db.courses.find({"enrolled_user_ids": user_id}).to_list(50)
    user_progress = await db.course_progress.find({"user_id": user_id}).to_list(50)
    user_submissions = await db.submissions.find({"user_id": user_id}).to_list(100)

    # Analyze performance patterns
    performance_data = {
        "completed_courses": len([p for p in user_progress if p.get("completed")]),
        "average_progress": sum([p.get("overall_progress", 0) for p in user_progress]) / len(user_progress) if user_progress else 0,
        "total_submissions": len(user_submissions),
        "average_grade": sum([s.get("ai_grade", {}).get("score", 0) for s in user_submissions if s.get("ai_grade")]) / len([s for s in user_submissions if s.get("ai_grade")]) if user_submissions else 0
    }

    # Get all available courses for recommendations
    all_courses = await db.courses.find({"published": True}).to_list(100)

    # AI-powered recommendation algorithm
    recommendations = []
    for course in all_courses:
        if course["_id"] in [c["_id"] for c in user_courses]:
            continue  # Skip already enrolled courses

        # Calculate recommendation score based on multiple factors
        score = 0
        reasons = []

        # Difficulty matching
        if performance_data["average_grade"] > 85 and course.get("difficulty") == "advanced":
            score += 30
            reasons.append("High performer - ready for advanced content")
        elif performance_data["average_grade"] < 70 and course.get("difficulty") == "beginner":
            score += 25
            reasons.append("Needs foundational knowledge")

        # Subject area preferences (based on enrolled courses)
        enrolled_subjects = set()
        for ec in user_courses:
            # Extract keywords from course titles
            words = ec.get("title", "").lower().split()
            enrolled_subjects.update(words)

        course_words = set(course.get("title", "").lower().split())
        subject_overlap = len(enrolled_subjects & course_words)
        if subject_overlap > 0:
            score += subject_overlap * 10
            reasons.append(f"Related to your interests in {list(enrolled_subjects & course_words)[:2]}")

        # Progress-based recommendations
        if performance_data["completed_courses"] > 3:
            score += 15
            reasons.append("Experienced learner - ready for complex topics")

        # Time-based recommendations (recent activity)
        recent_activity = len([s for s in user_submissions if (datetime.now(timezone.utc) - s.get("created_at", datetime.now(timezone.utc))).days < 7])
        if recent_activity > 5:
            score += 20
            reasons.append("Active learner - recommended continuation")

        if score > 20:  # Only include reasonably good matches
            recommendations.append({
                "course_id": str(course["_id"]),
                "title": course.get("title"),
                "difficulty": course.get("difficulty"),
                "audience": course.get("audience"),
                "score": min(score, 100),  # Cap at 100
                "reasons": reasons[:3]  # Top 3 reasons
            })

    # Sort by recommendation score
    recommendations.sort(key=lambda x: x["score"], reverse=True)

    return {
        "current_performance": performance_data,
        "recommendations": recommendations[:10],  # Top 10 recommendations
        "learning_insights": [
            f"You've completed {performance_data['completed_courses']} courses",
            f"Your average grade is {performance_data['average_grade']:.1f}%",
            f"You're an {'active' if recent_activity > 3 else 'moderate'} learner",
            f"Recommended difficulty level: {'Advanced' if performance_data['average_grade'] > 80 else 'Intermediate' if performance_data['average_grade'] > 60 else 'Beginner'}"
        ]
    }


@courses_router.get("/ai/course_insights/{course_id}")
async def get_course_ai_insights(course_id: str, user=Depends(_current_user)):
    """Generate AI-powered course insights for instructors"""
    course = await _require("courses", {"_id": course_id}, "Course not found")
    if course.get("owner_id") != user["id"] and user["role"] not in ["admin"]:
        raise HTTPException(403, "Not authorized")

    db = get_database()

    # Get comprehensive course analytics
    enrollments = len(course.get("enrolled_user_ids", []))
    progress_data = await db.course_progress.find({"course_id": course_id}).to_list(200)
    submissions = await db.submissions.find({"assignment_id": {"$in": [a["_id"] for a in await db.assignments.find({"course_id": course_id}).to_list(50)]}}).to_list(500)

    # Calculate engagement metrics
    completion_rate = len([p for p in progress_data if p.get("completed")]) / enrollments * 100 if enrollments > 0 else 0
    avg_progress = sum([p.get("overall_progress", 0) for p in progress_data]) / len(progress_data) if progress_data else 0
    avg_grade = sum([s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")]) / len([s for s in submissions if s.get("ai_grade")]) if submissions else 0

    # Generate AI insights
    insights = []

    if completion_rate > 80:
        insights.append("🎉 Excellent completion rate! Course content is highly engaging.")
    elif completion_rate < 50:
        insights.append("⚠️ Low completion rate. Consider reviewing course difficulty or structure.")

    if avg_progress > 75:
        insights.append("📈 Students are progressing well through the material.")
    elif avg_progress < 40:
        insights.append("📉 Students may be struggling. Consider additional support resources.")

    if avg_grade > 85:
        insights.append("🏆 High average grades indicate strong student understanding.")
    elif avg_grade < 70:
        insights.append("📚 Average grades suggest need for additional explanations or resources.")

    # Lesson-specific insights
    lesson_completion = {}
    for progress in progress_data:
        for lp in progress.get("lessons_progress", []):
            lesson_id = lp.get("lesson_id")
            if lesson_id not in lesson_completion:
                lesson_completion[lesson_id] = {"completed": 0, "total": 0}
            lesson_completion[lesson_id]["total"] += 1
            if lp.get("completed"):
                lesson_completion[lesson_id]["completed"] += 1

    difficult_lessons = []
    for lesson_id, stats in lesson_completion.items():
        completion_pct = stats["completed"] / stats["total"] * 100
        if completion_pct < 60:  # Less than 60% completion
            difficult_lessons.append({
                "lesson_id": lesson_id,
                "completion_rate": completion_pct,
                "suggestion": "Consider adding more examples or breaking down complex concepts"
            })

    return {
        "overview": {
            "enrollments": enrollments,
            "completion_rate": round(completion_rate, 1),
            "average_progress": round(avg_progress, 1),
            "average_grade": round(avg_grade, 1),
            "total_submissions": len(submissions)
        },
        "insights": insights,
        "difficult_lessons": difficult_lessons[:5],  # Top 5 most difficult lessons
        "recommendations": [
            "Consider adding more interactive elements to boost engagement",
            "Review difficult lessons and provide additional resources",
            "Send personalized encouragement to struggling students",
            "Create study groups for peer learning support"
        ] if len(difficult_lessons) > 0 else ["Course is performing well! Consider adding advanced modules."]
    }


@courses_router.post("/ai/generate_course_content")
async def generate_course_content(request: dict, user=Depends(_current_user)):
    """Generate comprehensive course content using AI"""
    _require_role(user, ["admin", "instructor"])

    topic = request.get("topic", "")
    audience = request.get("audience", "general")
    difficulty = request.get("difficulty", "intermediate")
    lesson_count = request.get("lesson_count", 5)

    # Enhanced AI prompt for course generation
    system_prompt = """You are an expert curriculum designer and subject matter expert. Create comprehensive, engaging course content that follows best practices in educational design.

Course Design Principles:
1. Clear learning objectives for each lesson
2. Progressive difficulty building
3. Real-world applications and examples
4. Assessment opportunities throughout
5. Inclusive and accessible content
6. Engaging multimedia suggestions
7. Practical exercises and projects

Structure each lesson with:
- Learning objectives
- Key concepts and explanations
- Examples and case studies
- Practice activities
- Assessment questions
- Resources and references"""

    course_prompt = f"""Create a complete course on: {topic}

Target Audience: {audience}
Difficulty Level: {difficulty}
Number of Lessons: {lesson_count}

Provide:
1. Course overview and objectives
2. Detailed lesson plans with content, activities, and assessments
3. Quiz questions for each lesson
4. Final project or assessment
5. Recommended resources and materials

Make the content engaging, practical, and educationally sound."""

    try:
        model = _get_ai()
        response = model.generate_content(course_prompt)
        generated_content = response.text

        return {
            "generated_content": generated_content,
            "topic": topic,
            "audience": audience,
            "difficulty": difficulty,
            "lesson_count": lesson_count,
            "generation_timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"AI content generation failed: {str(e)}")


@courses_router.post("/ai/analyze_student_performance/{user_id}")
async def analyze_student_performance(user_id: str, user=Depends(_current_user)):
    """Comprehensive AI analysis of student performance"""
    if user["id"] != user_id and user["role"] not in ["admin", "instructor"]:
        raise HTTPException(403, "Not authorized")

    db = get_database()

    # Gather comprehensive student data
    courses = await db.courses.find({"enrolled_user_ids": user_id}).to_list(20)
    progress = await db.course_progress.find({"user_id": user_id}).to_list(20)
    submissions = await db.submissions.find({"user_id": user_id}).to_list(100)
    chats = await db.chats.find({"session_id": {"$regex": user_id}}).sort("created_at", -1).limit(50).to_list(50)

    # Performance analysis
    analysis = {
        "overall_performance": {
            "courses_enrolled": len(courses),
            "courses_completed": len([p for p in progress if p.get("completed")]),
            "average_progress": sum([p.get("overall_progress", 0) for p in progress]) / len(progress) if progress else 0,
            "total_submissions": len(submissions),
            "average_grade": sum([s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")]) / len([s for s in submissions if s.get("ai_grade")]) if submissions else 0
        },
        "learning_patterns": {
            "most_active_day": "Analysis pending",
            "preferred_learning_time": "Analysis pending",
            "average_session_length": "Analysis pending",
            "consistency_score": "Analysis pending"
        },
        "strengths_weaknesses": {
            "strong_subjects": [],
            "areas_for_improvement": [],
            "learning_style": "Adaptive learner",
            "recommended_study_methods": []
        },
        "predictions": {
            "completion_probability": 0,
            "recommended_next_course": "",
            "estimated_completion_time": "",
            "skill_development_trajectory": ""
        },
        "personalized_recommendations": [
            "Focus on consistent daily study sessions",
            "Practice more hands-on exercises",
            "Join study groups for peer learning",
            "Review fundamental concepts regularly",
            "Set specific learning goals for each session"
        ]
    }

    return analysis


# Get enrolled students for a course
@courses_router.get("/{cid}/students")
async def get_enrolled_students(cid: str, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    db = get_database()
    enrolled_ids = course.get("enrolled_user_ids", [])
    if enrolled_ids:
        users = await db.users.find({"_id": {"$in": enrolled_ids}}).to_list(100)
        return [{"id": u["_id"], "name": u["name"], "email": u["email"]} for u in users]
    return []


# Delete course
@courses_router.delete("/{cid}")
async def delete_course(cid: str, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    db = get_database()
    await db.courses.delete_one({"_id": cid})
    # Also delete related data
    await db.assignments.delete_many({"course_id": cid})
    await db.submissions.delete_many({"assignment_id": {"$in": await db.assignments.find({"course_id": cid}).distinct("_id")}})
    await db.course_progress.delete_many({"course_id": cid})
    await db.certificates.delete_many({"course_id": cid})
    return {"status": "deleted"}


# AI-Powered Personalized Learning Paths
@courses_router.get("/ai/learning_path/{user_id}")
async def get_ai_learning_path(user_id: str, user=Depends(_current_user)):
    from database import get_database
    db = get_database()

    # Check permissions
    if not (user["role"] == "admin" or user["id"] == user_id):
        raise HTTPException(403, "Not authorized")

    # Get user's progress and history
    progress_data = await db.course_progress.find({"user_id": user_id}).to_list(100)
    completed_courses = [p["course_id"] for p in progress_data if p.get("completed")]

    # Get user's submissions and grades
    submissions = await db.submissions.find({"user_id": user_id}).to_list(100)
    avg_grade = sum(s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")) / len([s for s in submissions if s.get("ai_grade")]) if submissions else 0

    # Get all available courses
    all_courses = await db.courses.find({"published": True}).to_list(200)

    # AI Recommendation Algorithm
    recommendations = []

    for course in all_courses:
        if course["_id"] in completed_courses:
            continue

        score = 0
        reasons = []

        # Progress-based scoring
        user_progress = next((p for p in progress_data if p["course_id"] == course["_id"]), None)
        if user_progress:
            if user_progress.get("overall_progress", 0) > 50:
                score += 30
                reasons.append("Good progress in similar content")
        else:
            # New course - check prerequisites
            if len(completed_courses) > 2:
                score += 20
                reasons.append("Ready for advanced content")

        # Difficulty matching
        if avg_grade > 80 and course.get("difficulty") == "advanced":
            score += 25
            reasons.append("High performer - suitable for advanced level")
        elif avg_grade < 60 and course.get("difficulty") == "beginner":
            score += 25
            reasons.append("Needs foundational content")

        # Interest matching (simplified)
        if len(completed_courses) > 0:
            score += 15
            reasons.append("Based on learning history")

        if score > 20:
            recommendations.append({
                "course_id": course["_id"],
                "title": course["title"],
                "difficulty": course.get("difficulty"),
                "score": score,
                "reasons": reasons[:2]  # Top 2 reasons
            })

    # Sort by score
    recommendations.sort(key=lambda x: x["score"], reverse=True)

    return {
        "user_id": user_id,
        "current_performance": {
            "completed_courses": len(completed_courses),
            "average_grade": round(avg_grade, 1),
            "active_courses": len(progress_data)
        },
        "recommendations": recommendations[:5]  # Top 5 recommendations
    }




# Instructor: View student progress
@courses_router.get("/{cid}/students/{sid}/progress")
async def get_student_progress(cid: str, sid: str, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    db = get_database()
    progress = await db.course_progress.find_one({"course_id": cid, "user_id": sid})
    return progress or {"course_id": cid, "user_id": sid, "lessons_progress": [], "overall_progress": 0.0, "completed": False}


# Instructor: Update student progress
@courses_router.put("/{cid}/students/{sid}/progress")
async def update_student_progress(cid: str, sid: str, progress_data: dict, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    db = get_database()
    await db.course_progress.update_one(
        {"course_id": cid, "user_id": sid},
        {"$set": progress_data},
        upsert=True
    )
    return {"status": "updated"}


# Instructor: Remove student from course
@courses_router.delete("/{cid}/students/{sid}")
async def remove_student(cid: str, sid: str, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] in ["admin", "instructor"] or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    db = get_database()
    await db.courses.update_one({"_id": cid}, {"$pull": {"enrolled_user_ids": sid}})
    await db.course_progress.delete_one({"course_id": cid, "user_id": sid})
    return {"status": "removed"}


# AI Tools for Instructors
@courses_router.post("/ai/lesson_plan")
async def generate_lesson_plan(request: dict, user=Depends(_current_user)):
    """Generate a detailed lesson plan using AI"""
    _require_role(user, ["admin", "instructor"])

    topic = request.get("topic", "")
    grade_level = request.get("grade_level", "general")
    duration = request.get("duration", 60)
    objectives = request.get("objectives", [])

    prompt = f"""
    Create a comprehensive lesson plan for: {topic}

    Target Audience: {grade_level}
    Duration: {duration} minutes
    Learning Objectives: {', '.join(objectives) if objectives else 'General understanding'}

    Please provide:
    1. Lesson Title
    2. Learning Objectives
    3. Materials Needed
    4. Lesson Procedure (step-by-step)
    5. Assessment Methods
    6. Differentiation Strategies
    7. Extension Activities

    Make it detailed, practical, and educationally sound.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return {
            "lesson_plan": response.text,
            "topic": topic,
            "grade_level": grade_level,
            "duration": duration,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"AI lesson plan generation failed: {str(e)}")


@courses_router.post("/ai/quiz_generator")
async def generate_quiz(request: dict, user=Depends(_current_user)):
    """Generate quiz questions using AI"""
    _require_role(user, ["admin", "instructor"])

    topic = request.get("topic", "")
    difficulty = request.get("difficulty", "intermediate")
    question_count = request.get("question_count", 5)
    question_types = request.get("question_types", ["multiple_choice"])

    prompt = f"""
    Generate {question_count} quiz questions on: {topic}

    Difficulty Level: {difficulty}
    Question Types: {', '.join(question_types)}

    For each question, provide:
    1. Question text
    2. Answer options (if multiple choice)
    3. Correct answer
    4. Explanation
    5. Difficulty level

    Make questions challenging but fair, with clear explanations.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return {
            "quiz_questions": response.text,
            "topic": topic,
            "difficulty": difficulty,
            "question_count": question_count,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"AI quiz generation failed: {str(e)}")


@courses_router.post("/ai/assignment_ideas")
async def generate_assignment_ideas(request: dict, user=Depends(_current_user)):
    """Generate assignment ideas using AI"""
    _require_role(user, ["admin", "instructor"])

    topic = request.get("topic", "")
    skill_level = request.get("skill_level", "intermediate")
    assignment_types = request.get("assignment_types", ["project", "essay"])

    prompt = f"""
    Generate creative assignment ideas for: {topic}

    Skill Level: {skill_level}
    Assignment Types: {', '.join(assignment_types)}

    For each assignment idea, provide:
    1. Assignment Title
    2. Description and objectives
    3. Required materials/resources
    4. Step-by-step instructions
    5. Assessment rubric criteria
    6. Estimated completion time
    7. Differentiation options

    Make assignments engaging, practical, and aligned with learning objectives.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return {
            "assignment_ideas": response.text,
            "topic": topic,
            "skill_level": skill_level,
            "assignment_types": assignment_types,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"AI assignment generation failed: {str(e)}")


@courses_router.post("/ai/course_feedback")
async def analyze_course_feedback(request: dict, user=Depends(_current_user)):
    """Analyze course feedback using AI"""
    _require_role(user, ["admin", "instructor"])

    course_id = request.get("course_id")
    feedback_data = request.get("feedback_data", [])

    # Get course data
    course = await _require("courses", {"_id": course_id}, "Course not found")
    if course.get("owner_id") != user["id"] and user["role"] not in ["admin", "instructor"]:
        raise HTTPException(403, "Not authorized")

    feedback_text = "\n".join([f.get("comment", "") for f in feedback_data if f.get("comment")])

    prompt = f"""
    Analyze the following student feedback for the course "{course.get('title', '')}":

    {feedback_text}

    Please provide:
    1. Overall sentiment analysis
    2. Common themes and patterns
    3. Strengths mentioned
    4. Areas for improvement
    5. Specific actionable recommendations
    6. Student engagement indicators

    Be constructive and provide specific suggestions for improvement.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return {
            "analysis": response.text,
            "course_id": course_id,
            "feedback_count": len(feedback_data),
            "analyzed_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"AI feedback analysis failed: {str(e)}")


# AI Tools for Students
@courses_router.post("/ai/study_guide")
async def generate_study_guide(request: dict, user=Depends(_current_user)):
    """Generate personalized study guide using AI"""
    course_id = request.get("course_id")
    lesson_ids = request.get("lesson_ids", [])

    # Verify enrollment
    course = await _require("courses", {"_id": course_id}, "Course not found")
    if user["id"] not in course.get("enrolled_user_ids", []):
        raise HTTPException(403, "Not enrolled in this course")

    # Get lesson content
    lessons_content = []
    for lesson_id in lesson_ids:
        lesson = next((l for l in course.get("lessons", []) if l.get("id") == lesson_id), None)
        if lesson:
            lessons_content.append(f"Lesson: {lesson.get('title', '')}\nContent: {lesson.get('content', '')}")

    content_text = "\n\n".join(lessons_content)

    prompt = f"""
    Create a comprehensive study guide based on the following lesson content:

    {content_text}

    Please provide:
    1. Key concepts and definitions
    2. Important formulas/theorems (if applicable)
    3. Step-by-step problem-solving approaches
    4. Common mistakes to avoid
    5. Practice questions with answers
    6. Memory aids and mnemonics
    7. Real-world applications

    Make it concise yet comprehensive, perfect for exam preparation.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return {
            "study_guide": response.text,
            "course_id": course_id,
            "lesson_count": len(lesson_ids),
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"AI study guide generation failed: {str(e)}")


@courses_router.post("/ai/explain_concept")
async def explain_concept(request: dict, user=Depends(_current_user)):
    """Explain difficult concepts using AI"""
    concept = request.get("concept", "")
    context = request.get("context", "")
    explanation_level = request.get("level", "intermediate")

    prompt = f"""
    Explain the concept "{concept}" in simple, clear terms.

    Context: {context}
    Explanation Level: {explanation_level}

    Please provide:
    1. Simple definition
    2. Analogy or real-world example
    3. Step-by-step breakdown
    4. Common misconceptions
    5. Why it matters
    6. Related concepts to explore

    Use everyday language and make it engaging and easy to understand.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return {
            "explanation": response.text,
            "concept": concept,
            "level": explanation_level,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"AI concept explanation failed: {str(e)}")


@courses_router.post("/ai/practice_questions")
async def generate_practice_questions(request: dict, user=Depends(_current_user)):
    """Generate practice questions using AI"""
    topic = request.get("topic", "")
    difficulty = request.get("difficulty", "intermediate")
    question_count = request.get("question_count", 10)
    question_type = request.get("question_type", "mixed")

    prompt = f"""
    Generate {question_count} practice questions on: {topic}

    Difficulty: {difficulty}
    Question Type: {question_type}

    Include a mix of:
    1. Multiple choice questions
    2. Short answer questions
    3. True/False questions
    4. Application-based questions

    Provide answers and explanations for all questions.
    Make them progressively more challenging.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return {
            "practice_questions": response.text,
            "topic": topic,
            "difficulty": difficulty,
            "question_count": question_count,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"AI practice questions generation failed: {str(e)}")


@courses_router.post("/ai/learning_tips")
async def get_learning_tips(request: dict, user=Depends(_current_user)):
    """Get personalized learning tips using AI"""
    learning_goal = request.get("learning_goal", "")
    current_level = request.get("current_level", "beginner")
    preferred_style = request.get("preferred_style", "visual")

    prompt = f"""
    Provide personalized learning tips for someone who wants to: {learning_goal}

    Current Level: {current_level}
    Preferred Learning Style: {preferred_style}

    Please provide:
    1. Study techniques that work best for their style
    2. Time management strategies
    3. Resource recommendations
    4. Motivation and mindset tips
    5. Common pitfalls to avoid
    6. Progress tracking methods
    7. When to seek help

    Make the advice practical, actionable, and encouraging.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return {
            "learning_tips": response.text,
            "learning_goal": learning_goal,
            "current_level": current_level,
            "preferred_style": preferred_style,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"AI learning tips generation failed: {str(e)}")


