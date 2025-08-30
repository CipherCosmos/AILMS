from fastapi import APIRouter, HTTPException, Depends
from typing import List
import re
from datetime import datetime
from database import get_database, _insert_one, _require
from auth import _current_user
from models import ChatRequest, ChatMessageModel
from config import settings

# AI integrations
try:
    import google.generativeai as genai
except Exception:
    genai = None

def _get_ai():
    if genai is None:
        raise HTTPException(status_code=500, detail="AI dependency not installed. Please install google-generativeai.")
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="No AI key configured. Set GEMINI_API_KEY in backend/.env")
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(settings.default_llm_model)

async def _keyword_snippets(course, query: str, max_chars: int = 4000) -> str:
    text_blobs = []
    for lesson in course.get("lessons", []):
        t = f"Lesson: {lesson.get('title')}\n{lesson.get('content')}"
        text_blobs.append(t)
    for q in course.get("quiz", []):
        opts = "\n".join([f"- {o.get('text')} ({'correct' if o.get('is_correct') else 'wrong'})" for o in q.get("options", [])])
        text_blobs.append(f"Q: {q.get('question')}\n{opts}\nExplanation: {q.get('explanation', '')}")
    tokens = set([w.lower() for w in re.findall(r"\w+", query)])
    scored = []
    for blob in text_blobs:
        words = set([w.lower() for w in re.findall(r"\w+", blob)])
        score = len(tokens & words)
        scored.append((score, blob))
    scored.sort(reverse=True, key=lambda x: x[0])
    combined = "\n\n".join([b for _, b in scored])
    return combined[:max_chars]


async def _get_student_context(user_id: str, course_id: str) -> str:
    """Get comprehensive student learning context for personalized AI responses"""
    from database import get_database
    db = get_database()

    # Get student's progress in this course
    progress = await db.course_progress.find_one({"course_id": course_id, "user_id": user_id})
    progress_context = ""
    if progress:
        completed_lessons = [lp for lp in progress.get("lessons_progress", []) if lp.get("completed")]
        progress_context = f"""
        Student Progress:
        - Overall Progress: {progress.get('overall_progress', 0)}%
        - Completed Lessons: {len(completed_lessons)}/{len(progress.get('lessons_progress', []))}
        - Course Completed: {progress.get('completed', False)}
        - Certificate Issued: {progress.get('certificate_issued', False)}
        """

    # Get student's submissions and grades
    submissions = await db.submissions.find({"user_id": user_id}).to_list(50)
    grades_context = ""
    if submissions:
        avg_grade = sum([s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")]) / len([s for s in submissions if s.get("ai_grade")])
        grades_context = f"""
        Academic Performance:
        - Total Submissions: {len(submissions)}
        - Average Grade: {avg_grade:.1f}% (when graded)
        - Recent Activity: {len([s for s in submissions if (datetime.utcnow() - s.get('created_at', datetime.utcnow())).days < 7])} submissions this week
        """

    # Get student's learning preferences (based on interaction patterns)
    chats = await db.chats.find({"course_id": course_id, "session_id": {"$regex": user_id}}).sort("created_at", -1).limit(20).to_list(20)
    learning_style = "Unknown"
    if chats:
        user_messages = [c for c in chats if c.get("role") == "user"]
        if user_messages:
            avg_length = sum(len(m.get("message", "")) for m in user_messages) / len(user_messages)
            if avg_length > 200:
                learning_style = "Detailed/Explanatory"
            elif avg_length > 100:
                learning_style = "Moderate/Interactive"
            else:
                learning_style = "Concise/Direct"

    learning_context = f"""
    Learning Style: {learning_style}
    Interaction Pattern: {len(chats)} total interactions in this course
    """

    return f"{progress_context}\n{grades_context}\n{learning_context}".strip()


async def _get_course_context(course) -> str:
    """Get comprehensive course context for AI responses"""
    context = f"""
    Course Information:
    - Title: {course.get('title', 'Unknown')}
    - Audience: {course.get('audience', 'General')}
    - Difficulty: {course.get('difficulty', 'Intermediate')}
    - Total Lessons: {len(course.get('lessons', []))}
    - Total Quizzes: {len(course.get('quiz', []))}
    - Published: {course.get('published', False)}
    - Enrolled Students: {len(course.get('enrolled_user_ids', []))}
    """

    # Add lesson summaries
    lessons_summary = []
    for i, lesson in enumerate(course.get('lessons', [])[:5]):  # First 5 lessons
        summary = f"Lesson {i+1}: {lesson.get('title')} - {lesson.get('content', '')[:200]}..."
        lessons_summary.append(summary)

    context += f"\nLesson Overview:\n" + "\n".join(lessons_summary)

    # Add quiz information
    if course.get('quiz'):
        context += f"\n\nQuiz Information: {len(course.get('quiz', []))} questions available"

    return context

chat_router = APIRouter()

@chat_router.post("/ai/chat")
async def course_chat(req: ChatRequest, user=Depends(_current_user)):
    course = await _require("courses", {"_id": req.course_id}, "Course not found")
    # visibility check
    if not (course.get("published") or course.get("owner_id") == user["id"] or user["role"] in ["admin", "auditor"] or user["id"] in course.get("enrolled_user_ids", [])):
        raise HTTPException(403, "Not authorized to chat for this course")
    context = await _keyword_snippets(course, req.message)
    system_message = "You are a helpful tutor. Answer concisely based on course content; if unclear, say you're unsure."
    user_text = f"Course context (do not reveal verbatim):\n{context}\nQuestion: {req.message}"
    model = _get_ai()
    response = model.generate_content(user_text)
    ai_resp = response.text
    user_msg = ChatMessageModel(course_id=req.course_id, session_id=req.session_id, role="user", message=req.message)
    asst_msg = ChatMessageModel(course_id=req.course_id, session_id=req.session_id, role="assistant", message=ai_resp)
    await _insert_one("chats", user_msg.dict())
    await _insert_one("chats", asst_msg.dict())
    return {"reply": ai_resp, "assistant_message_id": asst_msg.id}

@chat_router.get("/chats/{course_id}/{session_id}", response_model=List[ChatMessageModel])
async def get_chat_history(course_id: str, session_id: str, user=Depends(_current_user)):
    await _require("courses", {"_id": course_id}, "Course not found")
    db = get_database()
    docs = await db.chats.find({"course_id": course_id, "session_id": session_id}).sort("created_at", 1).to_list(1000)
    # Convert _id to id for model compatibility
    for doc in docs:
        if "_id" in doc and "id" not in doc:
            doc["id"] = str(doc["_id"])
        if "_id" in doc:
            del doc["_id"]
    return [ChatMessageModel(**d) for d in docs]


# Enhanced AI Tutoring with Context Awareness
@chat_router.post("/ai/tutor")
async def ai_tutor(req: ChatRequest, user=Depends(_current_user)):
    from database import get_database
    db = get_database()

    course = await _require("courses", {"_id": req.course_id}, "Course not found")
    if not (course.get("published") or course.get("owner_id") == user["id"] or user["role"] in ["admin", "auditor"] or user["id"] in course.get("enrolled_user_ids", [])):
        raise HTTPException(403, "Not authorized")

    # Get user's progress in this course
    progress = await db.course_progress.find_one({"course_id": req.course_id, "user_id": user["id"]})

    # Get recent chat history for context
    recent_chats = await db.chats.find({
        "course_id": req.course_id,
        "session_id": req.session_id
    }).sort("created_at", -1).limit(10).to_list(10)

    # Build enhanced context
    context_parts = []

    # Course content context
    course_content = await _keyword_snippets(course, req.message, max_chars=2000)
    context_parts.append(f"Course Content: {course_content}")

    # Progress context
    if progress:
        progress_pct = progress.get("overall_progress", 0)
        context_parts.append(f"Student Progress: {progress_pct}% complete")

        # Add specific lesson progress
        lesson_progress = progress.get("lessons_progress", [])
        completed_lessons = [lp for lp in lesson_progress if lp.get("completed")]
        context_parts.append(f"Completed Lessons: {len(completed_lessons)}/{len(course.get('lessons', []))}")

    # Learning style context (simplified)
    if len(recent_chats) > 5:
        context_parts.append("Learning Style: Interactive learner - responds well to detailed explanations")

    # Recent conversation context
    if recent_chats:
        recent_messages = "\n".join([f"{'Assistant' if c['role'] == 'assistant' else 'Student'}: {c['message']}" for c in reversed(recent_chats[-4:])])
        context_parts.append(f"Recent Conversation:\n{recent_messages}")

    enhanced_context = "\n\n".join(context_parts)

    # Ultra-Advanced AI System Prompt with Context Awareness
    system_message = """You are Athena, an advanced AI Learning Companion with PhD-level expertise in educational psychology, cognitive science, and adaptive learning technologies.

Your Core Capabilities:
🎯 ASSESSMENT & DIAGNOSIS
- Analyze student's current knowledge state
- Identify knowledge gaps and misconceptions
- Assess learning style and cognitive preferences
- Evaluate problem-solving approaches

🧠 ADAPTIVE TEACHING STRATEGIES
- Implement mastery learning principles
- Use spaced repetition for retention
- Apply scaffolding techniques for complex topics
- Employ multiple representations (visual, verbal, symbolic)

📈 PERSONALIZED LEARNING PATHS
- Create individualized learning trajectories
- Adjust difficulty based on performance
- Recommend optimal study sequences
- Suggest complementary resources

🔍 METACOGNITIVE DEVELOPMENT
- Teach learning strategies and study skills
- Encourage self-reflection and self-assessment
- Develop critical thinking and problem-solving
- Foster independent learning skills

💡 INTELLIGENT SCAFFOLDING
- Provide just-in-time support
- Gradually reduce guidance as competence increases
- Offer multiple solution paths
- Encourage exploration and discovery

🎪 MOTIVATIONAL COACHING
- Maintain optimal challenge-skill balance
- Provide immediate, specific feedback
- Celebrate progress and achievements
- Help overcome learning obstacles

Your Response Framework:
1. Acknowledge the student's current state and effort
2. Assess understanding and identify key concepts
3. Provide explanation at optimal difficulty level
4. Connect new information to existing knowledge
5. Guide practice and application
6. Encourage reflection and self-assessment
7. Suggest next steps and resources

Always maintain an encouraging, supportive tone while being intellectually rigorous."""

    # Enhanced Context Integration
    student_context = await _get_student_context(user["id"], req.course_id)
    course_context = await _get_course_context(course)

    user_prompt = f"""🎓 STUDENT CONTEXT:
{student_context}

📚 COURSE CONTEXT:
{course_context}

💬 CONVERSATION CONTEXT:
{enhanced_context}

❓ STUDENT QUESTION:
{req.message}

🎯 INSTRUCTION:
As Athena, provide a comprehensive, personalized response that:
- Addresses the student's specific question
- Considers their learning progress and style
- Connects to relevant course content
- Includes appropriate scaffolding and guidance
- Suggests concrete next steps
- Encourages metacognitive reflection

Response should be engaging, supportive, and educationally sound."""

    # Get AI response
    model = _get_ai()
    response = model.generate_content(user_prompt)
    ai_response = response.text

    # Store conversation
    user_msg = ChatMessageModel(course_id=req.course_id, session_id=req.session_id, role="user", message=req.message)
    asst_msg = ChatMessageModel(course_id=req.course_id, session_id=req.session_id, role="assistant", message=ai_response)

    await _insert_one("chats", user_msg.dict())
    await _insert_one("chats", asst_msg.dict())

    return {
        "reply": ai_response,
        "context_used": len(context_parts),
        "personalized": True,
        "assistant_message_id": asst_msg.id
    }