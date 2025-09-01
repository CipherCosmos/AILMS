"""
AI-powered content generation routes for AI Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
import json
import re

from shared.config.config import settings
from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations
from shared.common.errors import ValidationError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("ai-service")
router = APIRouter()

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

async def _current_user(token: str = None):
    """Get current authenticated user"""
    if not token:
        raise HTTPException(401, "No authentication token provided")

    try:
        import jwt
        from shared.config.config import settings

        # Decode and validate JWT token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        # Verify token hasn't expired
        if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(401, "Token has expired")

        # Get user from database
        users_db = DatabaseOperations("users")
        user = await users_db.find_one({"_id": payload.get("sub")})
        if not user:
            raise HTTPException(401, "User not found")

        return {
            "id": user["_id"],
            "role": user.get("role", "student"),
            "email": user.get("email", ""),
            "name": user.get("name", "")
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    except Exception as e:
        raise HTTPException(401, f"Authentication failed: {str(e)}")

def _require_role(user, allowed: list[str]):
    """Check if user has required role"""
    if user.get("role") not in allowed:
        raise HTTPException(403, "Insufficient permissions")

@router.post("/generate-course")
async def generate_course(request: dict, user=Depends(_current_user)):
    """
    Generate a complete course using AI.

    - **topic**: Course topic
    - **audience**: Target audience
    - **difficulty**: Difficulty level
    - **lessons_count**: Number of lessons to generate
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "instructor"])

        topic = request.get("topic", "")
        audience = request.get("audience", "general")
        difficulty = request.get("difficulty", "intermediate")
        lesson_count = min(int(request.get("lesson_count", 10)), 25)

        if not topic:
            raise ValidationError("Topic is required", "topic")

        logger.info("Starting AI course generation", extra={
            "topic": topic,
            "audience": audience,
            "difficulty": difficulty,
            "lessons_count": lesson_count,
            "user_id": user["id"]
        })

        # Generate course structure
        course_data = await _generate_course_structure(topic, audience, difficulty, lesson_count)

        # Generate detailed content for each lesson
        detailed_lessons = []
        for i, lesson_outline in enumerate(course_data.get("lessons", [])):
            lesson_content = await _generate_detailed_lesson(
                lesson_outline, topic, audience, difficulty, i + 1
            )
            detailed_lessons.append(lesson_content)

        # Generate quizzes
        quizzes = await _generate_course_quizzes(detailed_lessons, topic, difficulty)

        result = {
            "title": course_data.get("title", f"AI Generated: {topic}"),
            "description": course_data.get("description", ""),
            "audience": audience,
            "difficulty": difficulty,
            "lessons": detailed_lessons,
            "quiz": quizzes,
            "learning_objectives": course_data.get("learning_objectives", []),
            "prerequisites": course_data.get("prerequisites", []),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "lesson_count": len(detailed_lessons),
            "generated_by": user["id"]
        }

        logger.info("AI course generation completed", extra={
            "course_title": result["title"],
            "lessons_generated": len(detailed_lessons),
            "quizzes_generated": len(quizzes),
            "user_id": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("AI course generation failed", extra={
            "topic": topic,
            "user_id": user["id"],
            "error": str(e)
        })
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
        "description": "Detailed course description (200-300 words)",
        "learning_objectives": ["objective1", "objective2"],
        "prerequisites": ["prereq1", "prereq2"],
        "lessons": [
            {{
                "id": "lesson_1",
                "title": "Lesson Title",
                "overview": "Brief overview of what will be covered",
                "duration_minutes": 90,
                "key_concepts": ["concept1", "concept2"],
                "learning_outcomes": ["outcome1", "outcome2"]
            }}
        ]
    }}

    Make the course structure comprehensive and well-organized.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return _safe_json_extract(response.text)
    except Exception as e:
        logger.error("Course structure generation failed", extra={"error": str(e)})
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
    - Real-world examples and case studies
    - Practical exercises and implementations
    - Code examples (if applicable)
    - Common mistakes and solutions
    - Further reading resources

    Make the content engaging, practical, and comprehensive (600-1000 words).
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
            "order_index": lesson_number - 1,
            "ai_generated": True,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error("Detailed lesson generation failed", extra={"error": str(e)})
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
                {"text": opt.get("text", ""), "is_correct": bool(opt.get("is_correct", False))}
                for opt in q.get("options", [])[:4]
            ]
            if options:
                quiz_question = {
                    "id": f"quiz_{len(quizzes) + 1}",
                    "question": q.get("question", ""),
                    "options": options,
                    "explanation": q.get("explanation", ""),
                    "ai_generated": True,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
                quizzes.append(quiz_question)

        return quizzes
    except Exception:
        logger.warning("Quiz generation failed, returning empty list", extra={"topic": topic})
        return []

@router.post("/generate-quiz")
async def generate_quiz(request: dict, user=Depends(_current_user)):
    """
    Generate quiz questions using AI.

    - **topic**: Quiz topic
    - **difficulty**: Difficulty level
    - **question_count**: Number of questions to generate
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "instructor"])

        topic = request.get("topic", "")
        difficulty = request.get("difficulty", "intermediate")
        question_count = min(int(request.get("question_count", 10)), 20)

        if not topic:
            raise ValidationError("Topic is required", "topic")

        prompt = f"""
        Generate {question_count} quiz questions on: {topic}
        Difficulty: {difficulty}

        Include a mix of:
        - Multiple choice questions (70%)
        - True/False questions (20%)
        - Short answer questions (10%)

        For multiple choice questions, provide 4 options with exactly one correct answer.
        Include explanations for all correct answers.
        """

        model = _get_ai()
        response = model.generate_content(prompt)

        logger.info("AI quiz generation completed", extra={
            "topic": topic,
            "difficulty": difficulty,
            "question_count": question_count,
            "user_id": user["id"]
        })

        return {
            "quiz_questions": response.text,
            "topic": topic,
            "difficulty": difficulty,
            "question_count": question_count,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": user["id"]
        }

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("AI quiz generation failed", extra={
            "topic": topic,
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, f"AI quiz generation failed: {str(e)}")

@router.get("/models")
async def get_available_models(user=Depends(_current_user)):
    """
    Get available AI models for content generation.
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "instructor"])

        # Return available models (simplified for now)
        return {
            "available_models": [
                {
                    "name": "gemini-1.5-flash",
                    "description": "Fast and efficient model for content generation",
                    "max_tokens": 8192,
                    "status": "available" if settings.gemini_api_key else "unavailable"
                },
                {
                    "name": "gemini-1.5-pro",
                    "description": "Advanced model with higher quality output",
                    "max_tokens": 16384,
                    "status": "available" if settings.gemini_api_key else "unavailable"
                }
            ],
            "current_model": settings.default_llm_model,
            "api_key_configured": bool(settings.gemini_api_key)
        }

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get AI models", extra={"error": str(e)})
        raise HTTPException(500, "Failed to retrieve AI models")