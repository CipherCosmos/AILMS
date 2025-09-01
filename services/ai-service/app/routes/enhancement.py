"""
Content enhancement routes for AI Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends

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

@router.post("/enhance-content")
async def enhance_content(request: dict, user=Depends(_current_user)):
    """
    Enhance existing lesson content using AI.

    - **content**: Original content to enhance
    - **enhancement_type**: Type of enhancement (comprehensive, examples, practical)
    - **target_audience**: Target audience for the content
    - **difficulty_level**: Difficulty level of the content
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

        logger.info("Starting content enhancement", extra={
            "enhancement_type": enhancement_type,
            "content_length": len(content),
            "target_audience": target_audience,
            "difficulty_level": difficulty_level,
            "user_id": user["id"]
        })

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

        result = {
            "enhanced_content": response.text,
            "original_content": content,
            "enhancement_type": enhancement_type,
            "target_audience": target_audience,
            "difficulty_level": difficulty_level,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": user["id"],
            "content_improvement": {
                "original_length": len(content),
                "enhanced_length": len(response.text),
                "improvement_ratio": round(len(response.text) / max(len(content), 1), 2)
            }
        }

        logger.info("Content enhancement completed", extra={
            "enhancement_type": enhancement_type,
            "original_length": len(content),
            "enhanced_length": len(response.text),
            "user_id": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Content enhancement failed", extra={
            "enhancement_type": enhancement_type,
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Content enhancement failed")

@router.post("/enhance-lesson")
async def enhance_lesson(request: dict, user=Depends(_current_user)):
    """
    Enhance a complete lesson using AI.

    - **lesson_title**: Title of the lesson
    - **lesson_content**: Current lesson content
    - **learning_objectives**: Learning objectives
    - **target_audience**: Target audience
    - **difficulty_level**: Difficulty level
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "instructor"])

        lesson_title = request.get("lesson_title", "")
        lesson_content = request.get("lesson_content", "")
        learning_objectives = request.get("learning_objectives", [])
        target_audience = request.get("target_audience", "general")
        difficulty_level = request.get("difficulty_level", "intermediate")

        if not lesson_title or not lesson_content:
            raise ValidationError("Lesson title and content are required", "lesson_data")

        logger.info("Starting lesson enhancement", extra={
            "lesson_title": lesson_title,
            "content_length": len(lesson_content),
            "target_audience": target_audience,
            "difficulty_level": difficulty_level,
            "user_id": user["id"]
        })

        prompt = f"""
        Enhance this complete lesson:

        Lesson Title: {lesson_title}
        Current Content: {lesson_content}
        Learning Objectives: {', '.join(learning_objectives) if learning_objectives else 'General learning'}
        Target Audience: {target_audience}
        Difficulty Level: {difficulty_level}

        Provide a comprehensive enhancement that includes:
        1. Improved structure and flow
        2. Additional real-world examples
        3. Interactive elements and exercises
        4. Assessment questions
        5. Visual learning aids descriptions
        6. Common mistakes and solutions
        7. Further reading and resources
        8. Summary and key takeaways

        Make the lesson more engaging, comprehensive, and effective for learning.
        """

        model = _get_ai()
        response = model.generate_content(prompt)

        result = {
            "enhanced_lesson": {
                "title": lesson_title,
                "content": response.text,
                "learning_objectives": learning_objectives,
                "target_audience": target_audience,
                "difficulty_level": difficulty_level
            },
            "original_content": lesson_content,
            "enhancement_summary": {
                "original_length": len(lesson_content),
                "enhanced_length": len(response.text),
                "improvement_ratio": round(len(response.text) / max(len(lesson_content), 1), 2)
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": user["id"]
        }

        logger.info("Lesson enhancement completed", extra={
            "lesson_title": lesson_title,
            "original_length": len(lesson_content),
            "enhanced_length": len(response.text),
            "user_id": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Lesson enhancement failed", extra={
            "lesson_title": lesson_title,
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Lesson enhancement failed")

@router.post("/generate-exercises")
async def generate_exercises(request: dict, user=Depends(_current_user)):
    """
    Generate practice exercises for a topic using AI.

    - **topic**: Topic for exercises
    - **difficulty**: Difficulty level
    - **exercise_count**: Number of exercises to generate
    - **exercise_type**: Type of exercises (coding, conceptual, practical)
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "instructor"])

        topic = request.get("topic", "")
        difficulty = request.get("difficulty", "intermediate")
        exercise_count = min(int(request.get("exercise_count", 5)), 10)
        exercise_type = request.get("exercise_type", "mixed")

        if not topic:
            raise ValidationError("Topic is required", "topic")

        logger.info("Generating exercises", extra={
            "topic": topic,
            "difficulty": difficulty,
            "exercise_count": exercise_count,
            "exercise_type": exercise_type,
            "user_id": user["id"]
        })

        prompt = f"""
        Generate {exercise_count} practice exercises for: {topic}
        Difficulty: {difficulty}
        Exercise Type: {exercise_type}

        Create a variety of exercises including:
        - Conceptual understanding questions
        - Problem-solving exercises
        - Practical application scenarios
        - Code implementation tasks (if applicable)
        - Critical thinking challenges

        For each exercise, provide:
        1. Clear instructions
        2. Expected outcomes
        3. Hints or guidance
        4. Solution approach (for instructors)
        """

        model = _get_ai()
        response = model.generate_content(prompt)

        result = {
            "exercises": response.text,
            "topic": topic,
            "difficulty": difficulty,
            "exercise_count": exercise_count,
            "exercise_type": exercise_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": user["id"]
        }

        logger.info("Exercises generated", extra={
            "topic": topic,
            "exercise_count": exercise_count,
            "user_id": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Exercise generation failed", extra={
            "topic": topic,
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Exercise generation failed")

@router.post("/improve-assessment")
async def improve_assessment(request: dict, user=Depends(_current_user)):
    """
    Improve assessment questions using AI.

    - **assessment_content**: Current assessment content
    - **assessment_type**: Type of assessment (quiz, exam, assignment)
    - **target_difficulty**: Target difficulty level
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "instructor"])

        assessment_content = request.get("assessment_content", "")
        assessment_type = request.get("assessment_type", "quiz")
        target_difficulty = request.get("target_difficulty", "intermediate")

        if not assessment_content:
            raise ValidationError("Assessment content is required", "assessment_content")

        logger.info("Improving assessment", extra={
            "assessment_type": assessment_type,
            "target_difficulty": target_difficulty,
            "content_length": len(assessment_content),
            "user_id": user["id"]
        })

        prompt = f"""
        Improve this assessment content:

        Current Assessment: {assessment_content}
        Assessment Type: {assessment_type}
        Target Difficulty: {target_difficulty}

        Provide improvements including:
        1. Better question clarity and precision
        2. More comprehensive answer options
        3. Improved difficulty calibration
        4. Enhanced learning outcome alignment
        5. Better discrimination between knowledge levels
        6. Clearer grading rubrics
        7. Additional question variations
        """

        model = _get_ai()
        response = model.generate_content(prompt)

        result = {
            "improved_assessment": response.text,
            "original_assessment": assessment_content,
            "assessment_type": assessment_type,
            "target_difficulty": target_difficulty,
            "improvement_summary": {
                "original_length": len(assessment_content),
                "improved_length": len(response.text)
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": user["id"]
        }

        logger.info("Assessment improvement completed", extra={
            "assessment_type": assessment_type,
            "original_length": len(assessment_content),
            "improved_length": len(response.text),
            "user_id": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Assessment improvement failed", extra={
            "assessment_type": assessment_type,
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Assessment improvement failed")