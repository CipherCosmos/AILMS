"""
Performance analysis routes for AI Service
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

@router.post("/analyze-performance")
async def analyze_performance(request: dict, user=Depends(_current_user)):
    """
    Analyze student performance using AI.

    - **user_id**: Student user ID to analyze
    - **course_id**: Specific course to analyze (optional)
    - **timeframe**: Analysis timeframe (optional)
    """
    try:
        # Check permissions (admin, instructor, or analyzing own performance)
        user_id = request.get("user_id")
        if user["id"] != user_id and user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to analyze this user's performance")

        course_id = request.get("course_id")
        timeframe = request.get("timeframe", "all")

        logger.info("Starting performance analysis", extra={
            "target_user_id": user_id,
            "course_id": course_id,
            "timeframe": timeframe,
            "requested_by": user["id"]
        })

        # Get performance data from database
        progress_db = DatabaseOperations("course_progress")
        progress_data = await progress_db.find_many({"user_id": user_id}, limit=20)

        submissions_db = DatabaseOperations("submissions")
        submissions = await submissions_db.find_many({"user_id": user_id}, limit=50)

        # Calculate metrics
        completed_courses = len([p for p in progress_data if p.get("completed")])
        avg_progress = sum([p.get("overall_progress", 0) for p in progress_data]) / len(progress_data) if progress_data else 0
        total_submissions = len(submissions)

        # Calculate average grade from submissions
        avg_grade = 0
        if submissions:
            grades = [s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")]
            if grades:
                avg_grade = sum(grades) / len(grades)

        # Generate AI analysis
        prompt = f"""
        Analyze this student's performance:

        Performance Summary:
        - Courses Enrolled: {len(progress_data)}
        - Courses Completed: {completed_courses}
        - Average Progress: {avg_progress:.1f}%
        - Total Submissions: {total_submissions}
        - Average Grade: {avg_grade:.1f}%

        Provide:
        1. Performance assessment (excellent/good/developing)
        2. Strengths and areas for improvement
        3. Learning pattern analysis
        4. Personalized recommendations
        5. Predicted completion trajectory
        6. Study habit suggestions
        """

        model = _get_ai()
        response = model.generate_content(prompt)

        result = {
            "analysis": response.text,
            "metrics": {
                "completed_courses": completed_courses,
                "average_progress": round(avg_progress, 1),
                "total_submissions": total_submissions,
                "average_grade": round(avg_grade, 1),
                "enrolled_courses": len(progress_data)
            },
            "performance_level": "Excellent" if avg_progress > 85 else "Good" if avg_progress > 70 else "Developing",
            "recommendations": [
                "Focus on consistent daily study sessions",
                "Practice more hands-on exercises",
                "Review fundamental concepts regularly"
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "analyzed_by": user["id"],
            "target_user": user_id
        }

        logger.info("Performance analysis completed", extra={
            "target_user_id": user_id,
            "performance_level": result["performance_level"],
            "average_progress": round(avg_progress, 1),
            "requested_by": user["id"]
        })

        return result

    except (AuthorizationError):
        raise
    except Exception as e:
        logger.error("Performance analysis failed", extra={
            "target_user_id": user_id,
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, f"Performance analysis failed: {str(e)}")

@router.post("/analyze-course-performance")
async def analyze_course_performance(request: dict, user=Depends(_current_user)):
    """
    Analyze performance for a specific course using AI.

    - **course_id**: Course to analyze
    - **include_individual_students**: Whether to include individual student analysis
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "instructor"])

        course_id = request.get("course_id")
        include_individual_students = request.get("include_individual_students", False)

        if not course_id:
            raise ValidationError("Course ID is required", "course_id")

        logger.info("Starting course performance analysis", extra={
            "course_id": course_id,
            "include_individual_students": include_individual_students,
            "requested_by": user["id"]
        })

        # Get course data
        courses_db = DatabaseOperations("courses")
        course = await courses_db.find_one({"_id": course_id})
        if not course:
            raise ValidationError("Course not found", "course_id")

        # Get all progress data for this course
        progress_db = DatabaseOperations("course_progress")
        all_progress = await progress_db.find_many({"course_id": course_id}, limit=1000)

        # Calculate course-level metrics
        total_enrolled = len(course.get("enrolled_user_ids", []))
        total_with_progress = len(all_progress)
        completed_count = len([p for p in all_progress if p.get("completed")])
        completion_rate = (completed_count / max(total_with_progress, 1)) * 100

        avg_progress = sum([p.get("overall_progress", 0) for p in all_progress]) / max(len(all_progress), 1)

        # Generate AI analysis for course
        prompt = f"""
        Analyze this course's performance:

        Course: {course.get('title', 'Unknown')}
        Total Enrolled: {total_enrolled}
        Active Students: {total_with_progress}
        Completion Rate: {completion_rate:.1f}%
        Average Progress: {avg_progress:.1f}%

        Provide:
        1. Overall course effectiveness assessment
        2. Student engagement analysis
        3. Content difficulty assessment
        4. Recommendations for improvement
        5. Success factors and challenges
        """

        model = _get_ai()
        response = model.generate_content(prompt)

        result = {
            "course_analysis": response.text,
            "course_metrics": {
                "course_id": course_id,
                "course_title": course.get("title", "Unknown"),
                "total_enrolled": total_enrolled,
                "active_students": total_with_progress,
                "completion_rate": round(completion_rate, 1),
                "average_progress": round(avg_progress, 1),
                "completed_students": completed_count
            },
            "engagement_indicators": {
                "enrollment_rate": round((total_with_progress / max(total_enrolled, 1)) * 100, 1),
                "completion_rate": round(completion_rate, 1),
                "average_progress": round(avg_progress, 1)
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "analyzed_by": user["id"]
        }

        # Include individual student analysis if requested
        if include_individual_students and all_progress:
            student_analyses = []
            for progress in all_progress[:10]:  # Limit to first 10 for performance
                student_prompt = f"""
                Analyze individual student performance:
                Student Progress: {progress.get('overall_progress', 0)}%
                Completed: {progress.get('completed', False)}
                Lessons completed: {len([l for l in progress.get('lessons_progress', []) if l.get('completed')])}

                Provide brief assessment and recommendations.
                """

                try:
                    student_response = model.generate_content(student_prompt)
                    student_analyses.append({
                        "user_id": progress["user_id"],
                        "progress": progress.get("overall_progress", 0),
                        "completed": progress.get("completed", False),
                        "analysis": student_response.text
                    })
                except Exception:
                    continue

            result["individual_analyses"] = student_analyses

        logger.info("Course performance analysis completed", extra={
            "course_id": course_id,
            "completion_rate": round(completion_rate, 1),
            "average_progress": round(avg_progress, 1),
            "requested_by": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Course performance analysis failed", extra={
            "course_id": course_id,
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Course performance analysis failed")

@router.post("/predict-performance")
async def predict_performance(request: dict, user=Depends(_current_user)):
    """
    Predict student performance using AI.

    - **user_id**: Student to predict performance for
    - **course_id**: Course to predict performance in
    """
    try:
        # Check permissions
        user_id = request.get("user_id")
        if user["id"] != user_id and user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to predict this user's performance")

        course_id = request.get("course_id")

        if not user_id or not course_id:
            raise ValidationError("User ID and Course ID are required", "prediction_data")

        logger.info("Starting performance prediction", extra={
            "target_user_id": user_id,
            "course_id": course_id,
            "requested_by": user["id"]
        })

        # Get historical data
        progress_db = DatabaseOperations("course_progress")
        user_progress = await progress_db.find_many({"user_id": user_id}, limit=20)

        submissions_db = DatabaseOperations("submissions")
        user_submissions = await submissions_db.find_many({"user_id": user_id}, limit=50)

        # Calculate current performance metrics
        completed_courses = len([p for p in user_progress if p.get("completed")])
        avg_progress = sum([p.get("overall_progress", 0) for p in user_progress]) / max(len(user_progress), 1)

        avg_grade = 0
        if user_submissions:
            grades = [s.get("ai_grade", {}).get("score", 0) for s in user_submissions if s.get("ai_grade")]
            if grades:
                avg_grade = sum(grades) / len(grades)

        # Generate AI prediction
        prompt = f"""
        Predict student performance for course:

        Current Performance:
        - Completed Courses: {completed_courses}
        - Average Progress: {avg_progress:.1f}%
        - Average Grade: {avg_grade:.1f}%
        - Total Submissions: {len(user_submissions)}

        Provide:
        1. Predicted final grade (A/B/C/D/F)
        2. Predicted completion probability (%)
        3. Expected completion timeline
        4. Risk factors and challenges
        5. Recommendations to improve predicted outcomes
        """

        model = _get_ai()
        response = model.generate_content(prompt)

        result = {
            "prediction": response.text,
            "current_metrics": {
                "completed_courses": completed_courses,
                "average_progress": round(avg_progress, 1),
                "average_grade": round(avg_grade, 1),
                "total_submissions": len(user_submissions)
            },
            "prediction_factors": {
                "historical_performance": "Strong" if avg_progress > 75 else "Moderate" if avg_progress > 50 else "Developing",
                "consistency": "High" if len(user_submissions) > 10 else "Medium" if len(user_submissions) > 5 else "Low",
                "engagement": "High" if completed_courses > 2 else "Medium" if completed_courses > 0 else "Low"
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "predicted_for": user_id,
            "course_id": course_id,
            "predicted_by": user["id"]
        }

        logger.info("Performance prediction completed", extra={
            "target_user_id": user_id,
            "course_id": course_id,
            "average_progress": round(avg_progress, 1),
            "requested_by": user["id"]
        })

        return result

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Performance prediction failed", extra={
            "target_user_id": user_id,
            "course_id": course_id,
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Performance prediction failed")