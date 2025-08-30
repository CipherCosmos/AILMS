from fastapi import APIRouter, HTTPException, Depends
from typing import List
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
from datetime import datetime

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
    if not (user["role"] == "admin" or doc.get("owner_id") == user["id"]):
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
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
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
    if not (user["role"] in ["admin"] or course.get("owner_id") == user["id"]):
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
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
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
@courses_router.post("/{cid}/progress")
async def update_progress(cid: str, lesson_id: str, completed: bool, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if user["id"] not in course.get("enrolled_user_ids", []):
        raise HTTPException(403, "Not enrolled in course")

    db = get_database()
    progress_doc = await db.course_progress.find_one({"course_id": cid, "user_id": user["id"]})
    if not progress_doc:
        progress_doc = {"course_id": cid, "user_id": user["id"], "lessons_progress": []}

    lesson_progress = next((lp for lp in progress_doc["lessons_progress"] if lp["lesson_id"] == lesson_id), None)
    if not lesson_progress:
        lesson_progress = {"lesson_id": lesson_id, "completed": False}
        progress_doc["lessons_progress"].append(lesson_progress)

    if completed and not lesson_progress["completed"]:
        lesson_progress["completed"] = True
        lesson_progress["completed_at"] = datetime.utcnow()

    # Calculate overall progress
    total_lessons = len(course.get("lessons", []))
    completed_lessons = sum(1 for lp in progress_doc["lessons_progress"] if lp["completed"])
    progress_doc["overall_progress"] = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

    if progress_doc["overall_progress"] >= 100 and not progress_doc.get("completed"):
        progress_doc["completed"] = True
        progress_doc["completed_at"] = datetime.utcnow()

    await db.course_progress.update_one(
        {"course_id": cid, "user_id": user["id"]},
        {"$set": progress_doc},
        upsert=True
    )
    return {"progress": progress_doc["overall_progress"], "completed": progress_doc["completed"]}


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


# Recommendations
@courses_router.get("/recommendations")
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


# Learning path
@courses_router.get("/learning_path")
async def get_learning_path(user=Depends(_current_user)):
    # Get user's enrolled courses and progress
    enrolled_courses = await db.courses.find({"enrolled_user_ids": user["id"]}).to_list(100)
    progress_data = await db.course_progress.find({"user_id": user["id"]}).to_list(100)

    # Calculate performance metrics
    total_courses = len(enrolled_courses)
    completed_courses = sum(1 for p in progress_data if p.get("completed"))
    total_progress = sum(p.get("overall_progress", 0) for p in progress_data)
    average_progress = total_progress / len(progress_data) if progress_data else 0

    # Get assignment grades
    submissions = await db.submissions.find({"user_id": user["id"]}).to_list(100)
    grades = [s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")]
    average_grade = sum(grades) / len(grades) if grades else 0

    # Generate learning path recommendations
    recommendations = []
    if average_progress < 70:
        recommendations.append({
            "type": "focus",
            "message": "Focus on completing current courses to build a strong foundation"
        })
    elif completed_courses >= 3:
        recommendations.append({
            "type": "advance",
            "message": "Consider taking advanced courses in your areas of interest"
        })

    return {
        "current_performance": {
            "completed_courses": completed_courses,
            "total_courses": total_courses,
            "average_progress": round(average_progress, 1),
            "average_grade": round(average_grade, 1),
            "active_courses": total_courses - completed_courses
        },
        "recommendations": recommendations,
        "learning_goals": [
            "Complete 2 more courses this month",
            "Maintain average grade above 85%",
            "Explore advanced topics in your field"
        ]
    }


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
        recent_activity = len([s for s in user_submissions if (datetime.utcnow() - s.get("created_at", datetime.utcnow())).days < 7])
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
            "generation_timestamp": datetime.utcnow().isoformat()
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
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
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
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
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
async def get_learning_path(user_id: str, user=Depends(_current_user)):
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


# General course recommendations for students
@courses_router.get("/recommendations")
async def get_course_recommendations(user=Depends(_current_user)):
    from database import get_database
    db = get_database()

    # Get all published courses
    all_courses = await db.courses.find({"published": True}).to_list(50)

    # Get user's enrolled courses
    enrolled_course_ids = []
    if hasattr(user, 'id'):
        enrolled = await db.courses.find({"enrolled_user_ids": user["id"]}).to_list(100)
        enrolled_course_ids = [c["_id"] for c in enrolled]

    # Filter out already enrolled courses
    available_courses = [c for c in all_courses if c["_id"] not in enrolled_course_ids]

    # Simple recommendation logic (can be enhanced with AI)
    recommendations = []
    for course in available_courses[:10]:  # Limit to 10 recommendations
        recommendations.append({
            "id": str(course["_id"]),
            "title": course["title"],
            "audience": course.get("audience", "General"),
            "difficulty": course.get("difficulty", "beginner"),
            "lessons_count": len(course.get("lessons", []))
        })

    return recommendations


# Instructor: View student progress
@courses_router.get("/{cid}/students/{sid}/progress")
async def get_student_progress(cid: str, sid: str, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    db = get_database()
    progress = await db.course_progress.find_one({"course_id": cid, "user_id": sid})
    return progress or {"course_id": cid, "user_id": sid, "lessons_progress": [], "overall_progress": 0.0, "completed": False}


# Instructor: Update student progress
@courses_router.put("/{cid}/students/{sid}/progress")
async def update_student_progress(cid: str, sid: str, progress_data: dict, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
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
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    db = get_database()
    await db.courses.update_one({"_id": cid}, {"$pull": {"enrolled_user_ids": sid}})
    await db.course_progress.delete_one({"course_id": cid, "user_id": sid})
    return {"status": "removed"}


# AI recommendations
@courses_router.get("/recommendations")
async def get_recommendations(user=Depends(_current_user)):
    db = get_database()
    # Get user's enrolled courses and completed ones
    enrolled = await db.courses.find({"enrolled_user_ids": user["id"]}).to_list(100)
    completed_course_ids = []
    for c in enrolled:
        progress = await db.course_progress.find_one({"course_id": c["_id"], "user_id": user["id"]})
        if progress and progress.get("completed"):
            completed_course_ids.append(c["_id"])

    # Simple recommendation: suggest courses not enrolled in, similar audience
    if enrolled:
        audience = enrolled[0].get("audience", "General")
        recommended = await db.courses.find({
            "audience": audience,
            "published": True,
            "_id": {"$nin": [c["_id"] for c in enrolled]}
        }).sort("created_at", -1).to_list(5)
        return [Course(**c) for c in recommended]
    else:
        # New user: suggest popular courses
        all_courses = await db.courses.find({"published": True}).sort("created_at", -1).to_list(5)
        return [Course(**c) for c in all_courses]
