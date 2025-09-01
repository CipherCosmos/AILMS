"""
AI-powered course generation routes for Course Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
import json
import re

from shared.config.config import settings
from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger
from shared.models.models import (
    Course,
    CourseLesson,
    QuizQuestion,
    QuizOption,
    GenerateCourseRequest
)

logger = get_logger("course-service")
router = APIRouter()
courses_db = DatabaseOperations("courses")

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
        db = await DatabaseOperations("users").get_database()
        user = await db.users.find_one({"_id": payload.get("sub")})
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

@router.post("/generate_course", response_model=Course)
async def generate_course(req: GenerateCourseRequest, user=Depends(_current_user)):
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

        logger.info("Starting AI course generation", extra={
            "topic": req.topic,
            "audience": req.audience,
            "difficulty": req.difficulty,
            "lessons_count": req.lessons_count,
            "user_id": user["id"]
        })

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
        doc["ai_generated"] = True
        doc["generation_params"] = req.dict()
        doc["created_at"] = datetime.now(timezone.utc)

        await courses_db.insert_one(doc)

        logger.info("AI course generation completed", extra={
            "course_id": course.id,
            "title": course.title,
            "lessons_generated": len(detailed_lessons),
            "quizzes_generated": len(quizzes)
        })

        return course

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("AI course generation failed", extra={
            "topic": req.topic,
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
            "ai_generated": True
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
        logger.warning("Quiz generation failed, returning empty list", extra={"topic": topic})
        return []

@router.post("/enhance_content")
async def enhance_content(request: dict, user=Depends(_current_user)):
    """
    Enhance existing lesson content using AI.

    - **content**: Original content to enhance
    - **enhancement_type**: Type of enhancement (comprehensive, examples, practical)
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "instructor"])

        content = request.get("content", "")
        enhancement_type = request.get("enhancement_type", "comprehensive")
        target_audience = request.get("target_audience", "general")
        difficulty_level = request.get("difficulty_level", "intermediate")

        if not content:
            raise ValidationError("Content is required", "content")

        prompts = {
            "comprehensive": f"""
            Enhance this lesson content comprehensively:

            Original Content: {content}
            Target Audience: {target_audience}
            Difficulty Level: {difficulty_level}

            Add:
            1. Real-world examples and case studies
            2. Step-by-step explanations
            3. Visual descriptions and analogies
            4. Common misconceptions and clarifications
            5. Practical applications
            6. Assessment questions with answers

            Make the content 2-3 times more detailed while maintaining clarity.
            """,

            "examples": f"""
            Add comprehensive real-world examples to this content:

            Original Content: {content}
            Target Audience: {target_audience}

            Add 4-6 detailed examples including:
            - Industry case studies
            - Historical examples
            - Personal success stories
            - Common problem-solving scenarios
            """,

            "practical": f"""
            Add practical exercises and implementations to this lesson:

            Original Content: {content}
            Difficulty Level: {difficulty_level}

            Add:
            1. Hands-on exercises
            2. Code examples (if applicable)
            3. Step-by-step tutorials
            4. Practice problems with solutions
            5. Project ideas
            6. Implementation checklists
            """
        }

        prompt = prompts.get(enhancement_type, prompts["comprehensive"])

        model = _get_ai()
        response = model.generate_content(prompt)

        logger.info("Content enhanced using AI", extra={
            "enhancement_type": enhancement_type,
            "content_length": len(content),
            "enhanced_length": len(response.text),
            "user_id": user["id"]
        })

        return {
            "enhanced_content": response.text,
            "original_content": content,
            "enhancement_type": enhancement_type,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Content enhancement failed", extra={"error": str(e)})
        raise HTTPException(500, "Content enhancement failed")

@router.get("/models")
async def get_available_models(user=Depends(_current_user)):
    """
    Get available AI models for course generation.
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "instructor"])

        # Return available models (simplified for now)
        return {
            "available_models": [
                {
                    "name": "gemini-1.5-flash",
                    "description": "Fast and efficient model for course generation",
                    "max_tokens": 8192,
                    "supports_images": False
                },
                {
                    "name": "gemini-1.5-pro",
                    "description": "Advanced model with higher quality output",
                    "max_tokens": 16384,
                    "supports_images": True
                }
            ],
            "current_model": settings.default_llm_model
        }

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get AI models", extra={"error": str(e)})
        raise HTTPException(500, "Failed to retrieve AI models")