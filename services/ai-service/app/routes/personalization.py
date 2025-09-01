"""
Learning personalization routes for AI Service
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

@router.post("/personalize-learning")
async def personalize_learning(request: dict, user=Depends(_current_user)):
    """
    Generate personalized learning recommendations using AI.

    - **user_id**: User to personalize for
    - **learning_goals**: User's learning objectives
    - **current_level**: Current skill level
    - **preferred_style**: Preferred learning style
    - **time_available**: Time available per week
    """
    try:
        # Check permissions (can personalize own learning or admin/instructor can personalize for others)
        target_user_id = request.get("user_id")
        if user["id"] != target_user_id and user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to personalize learning for this user")

        learning_goals = request.get("learning_goals", [])
        current_level = request.get("current_level", "beginner")
        preferred_style = request.get("preferred_style", "visual")
        time_available = request.get("time_available", "moderate")

        if not target_user_id:
            raise ValidationError("User ID is required", "user_id")

        logger.info("Starting learning personalization", extra={
            "target_user_id": target_user_id,
            "learning_goals_count": len(learning_goals),
            "current_level": current_level,
            "preferred_style": preferred_style,
            "requested_by": user["id"]
        })

        # Get user's learning history
        progress_db = DatabaseOperations("course_progress")
        user_progress = await progress_db.find_many({"user_id": target_user_id}, limit=20)

        submissions_db = DatabaseOperations("submissions")
        user_submissions = await submissions_db.find_many({"user_id": target_user_id}, limit=50)

        # Calculate learning metrics
        completed_courses = len([p for p in user_progress if p.get("completed")])
        avg_progress = sum([p.get("overall_progress", 0) for p in user_progress]) / max(len(user_progress), 1)

        avg_grade = 0
        if user_submissions:
            grades = [s.get("ai_grade", {}).get("score", 0) for s in user_submissions if s.get("ai_grade")]
            if grades:
                avg_grade = sum(grades) / len(grades)

        prompt = f"""
        Create a personalized learning plan for:

        Learning Goals: {', '.join(learning_goals) if learning_goals else 'General skill development'}
        Current Level: {current_level}
        Preferred Learning Style: {preferred_style}
        Time Available: {time_available}

        Current Performance:
        - Completed Courses: {completed_courses}
        - Average Progress: {avg_progress:.1f}%
        - Average Grade: {avg_grade:.1f}%

        Provide:
        1. Customized study schedule
        2. Recommended learning resources
        3. Practice exercises and projects
        4. Assessment strategies
        5. Motivation and progress tracking tips
        6. Timeline and milestones
        7. Learning style adaptations
        """

        model = _get_ai()
        response = model.generate_content(prompt)

        result = {
            "personalized_plan": response.text,
            "learning_goals": learning_goals,
            "current_level": current_level,
            "preferred_style": preferred_style,
            "time_available": time_available,
            "current_performance": {
                "completed_courses": completed_courses,
                "average_progress": round(avg_progress, 1),
                "average_grade": round(avg_grade, 1)
            },
            "adaptations": {
                "learning_style": preferred_style,
                "pace": "Accelerated" if avg_progress > 80 else "Standard" if avg_progress > 60 else "Supportive",
                "focus_areas": "Advanced topics" if avg_grade > 85 else "Core concepts" if avg_grade > 70 else "Foundations"
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_for": target_user_id,
            "generated_by": user["id"]
        }

        logger.info("Learning personalization completed", extra={
            "target_user_id": target_user_id,
            "learning_goals_count": len(learning_goals),
            "preferred_style": preferred_style,
            "requested_by": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Learning personalization failed", extra={
            "target_user_id": target_user_id,
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Learning personalization failed")

@router.post("/adapt-content")
async def adapt_content(request: dict, user=Depends(_current_user)):
    """
    Adapt content based on user's learning profile.

    - **content**: Original content to adapt
    - **user_id**: User to adapt content for
    - **difficulty_preference**: Preferred difficulty level
    - **learning_style**: User's learning style
    """
    try:
        # Check permissions
        target_user_id = request.get("user_id")
        if user["id"] != target_user_id and user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to adapt content for this user")

        content = request.get("content", "")
        difficulty_preference = request.get("difficulty_preference", "adaptive")
        learning_style = request.get("learning_style", "visual")

        if not content:
            raise ValidationError("Content is required", "content")
        if not target_user_id:
            raise ValidationError("User ID is required", "user_id")

        logger.info("Starting content adaptation", extra={
            "target_user_id": target_user_id,
            "content_length": len(content),
            "difficulty_preference": difficulty_preference,
            "learning_style": learning_style,
            "requested_by": user["id"]
        })

        # Get user's learning profile
        profiles_db = DatabaseOperations("user_profiles")
        user_profile = await profiles_db.find_one({"user_id": target_user_id})

        preferred_style = user_profile.get("preferred_learning_style", learning_style) if user_profile else learning_style

        prompt = f"""
        Adapt this content for a learner:

        Original Content: {content}

        Learner Profile:
        - Preferred Learning Style: {preferred_style}
        - Difficulty Preference: {difficulty_preference}
        - Learning Goals: Adapt based on individual needs

        Provide adaptations including:
        1. Content restructuring for learning style
        2. Difficulty level adjustments
        3. Additional examples or simplifications
        4. Visual/auditory/kinesthetic elements
        5. Pacing recommendations
        6. Supplementary resources
        """

        model = _get_ai()
        response = model.generate_content(prompt)

        result = {
            "adapted_content": response.text,
            "original_content": content,
            "adaptation_details": {
                "learning_style": preferred_style,
                "difficulty_preference": difficulty_preference,
                "adaptations_made": [
                    "Content restructured for learning style",
                    "Difficulty adjusted",
                    "Examples added",
                    "Pacing recommendations included"
                ]
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "adapted_for": target_user_id,
            "adapted_by": user["id"]
        }

        logger.info("Content adaptation completed", extra={
            "target_user_id": target_user_id,
            "learning_style": preferred_style,
            "requested_by": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Content adaptation failed", extra={
            "target_user_id": target_user_id,
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Content adaptation failed")

@router.post("/recommend-courses")
async def recommend_courses(request: dict, user=Depends(_current_user)):
    """
    Recommend courses based on user's profile and goals.

    - **user_id**: User to recommend courses for
    - **goals**: Learning goals
    - **current_level**: Current skill level
    - **preferred_topics**: Preferred subject areas
    """
    try:
        # Check permissions
        target_user_id = request.get("user_id")
        if user["id"] != target_user_id and user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to recommend courses for this user")

        goals = request.get("goals", [])
        current_level = request.get("current_level", "beginner")
        preferred_topics = request.get("preferred_topics", [])

        if not target_user_id:
            raise ValidationError("User ID is required", "user_id")

        logger.info("Starting course recommendations", extra={
            "target_user_id": target_user_id,
            "goals_count": len(goals),
            "current_level": current_level,
            "preferred_topics_count": len(preferred_topics),
            "requested_by": user["id"]
        })

        # Get user's learning history
        progress_db = DatabaseOperations("course_progress")
        user_progress = await progress_db.find_many({"user_id": target_user_id}, limit=20)

        # Get available courses
        courses_db = DatabaseOperations("courses")
        available_courses = await courses_db.find_many({"published": True}, limit=50)

        # Calculate user preferences and performance
        completed_course_ids = [p["course_id"] for p in user_progress if p.get("completed")]
        avg_progress = sum([p.get("overall_progress", 0) for p in user_progress]) / max(len(user_progress), 1)

        prompt = f"""
        Recommend courses for this learner:

        Learner Profile:
        - Current Level: {current_level}
        - Learning Goals: {', '.join(goals) if goals else 'General skill development'}
        - Preferred Topics: {', '.join(preferred_topics) if preferred_topics else 'Open to suggestions'}
        - Completed Courses: {len(completed_course_ids)}
        - Average Progress: {avg_progress:.1f}%

        Available Courses: {len(available_courses)} courses

        Provide:
        1. Top 5 course recommendations with reasons
        2. Learning path suggestions
        3. Prerequisites and preparation needed
        4. Expected time commitment
        5. Skill development trajectory
        """

        model = _get_ai()
        response = model.generate_content(prompt)

        result = {
            "recommendations": response.text,
            "learner_profile": {
                "current_level": current_level,
                "goals": goals,
                "preferred_topics": preferred_topics,
                "completed_courses": len(completed_course_ids),
                "average_progress": round(avg_progress, 1)
            },
            "recommendation_criteria": {
                "skill_alignment": "High priority",
                "difficulty_appropriateness": "Medium priority",
                "interest_alignment": "High priority",
                "career_relevance": "Medium priority"
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "recommended_for": target_user_id,
            "recommended_by": user["id"]
        }

        logger.info("Course recommendations completed", extra={
            "target_user_id": target_user_id,
            "recommendations_count": 5,  # Assuming 5 recommendations
            "requested_by": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Course recommendation failed", extra={
            "target_user_id": target_user_id,
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Course recommendation failed")

@router.post("/generate-study-plan")
async def generate_study_plan(request: dict, user=Depends(_current_user)):
    """
    Generate a detailed study plan based on user's goals and schedule.

    - **user_id**: User to generate plan for
    - **goals**: Learning objectives
    - **timeframe**: Study timeframe (weeks)
    - **daily_hours**: Hours available per day
    - **preferred_times**: Preferred study times
    """
    try:
        # Check permissions
        target_user_id = request.get("user_id")
        if user["id"] != target_user_id and user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to generate study plan for this user")

        goals = request.get("goals", [])
        timeframe = int(request.get("timeframe", 4))
        daily_hours = float(request.get("daily_hours", 2))
        preferred_times = request.get("preferred_times", ["evening"])

        if not target_user_id:
            raise ValidationError("User ID is required", "user_id")

        logger.info("Generating study plan", extra={
            "target_user_id": target_user_id,
            "goals_count": len(goals),
            "timeframe": timeframe,
            "daily_hours": daily_hours,
            "requested_by": user["id"]
        })

        # Get user's current progress
        progress_db = DatabaseOperations("course_progress")
        user_progress = await progress_db.find_many({"user_id": target_user_id}, limit=20)

        avg_progress = sum([p.get("overall_progress", 0) for p in user_progress]) / max(len(user_progress), 1)

        prompt = f"""
        Create a detailed study plan:

        Goals: {', '.join(goals) if goals else 'General skill development'}
        Timeframe: {timeframe} weeks
        Daily Hours Available: {daily_hours}
        Preferred Study Times: {', '.join(preferred_times)}
        Current Progress: {avg_progress:.1f}%

        Provide:
        1. Weekly study schedule
        2. Daily study routines
        3. Topic progression plan
        4. Milestone checkpoints
        5. Progress tracking methods
        6. Adjustment strategies
        7. Motivation techniques
        """

        model = _get_ai()
        response = model.generate_content(prompt)

        result = {
            "study_plan": response.text,
            "plan_details": {
                "goals": goals,
                "timeframe_weeks": timeframe,
                "daily_hours": daily_hours,
                "preferred_times": preferred_times,
                "total_hours": timeframe * 7 * daily_hours
            },
            "current_status": {
                "average_progress": round(avg_progress, 1),
                "active_courses": len(user_progress)
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_for": target_user_id,
            "generated_by": user["id"]
        }

        logger.info("Study plan generated", extra={
            "target_user_id": target_user_id,
            "timeframe": timeframe,
            "daily_hours": daily_hours,
            "requested_by": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Study plan generation failed", extra={
            "target_user_id": target_user_id,
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Study plan generation failed")