"""
Course management routes for Course Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations, _require
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger
from shared.models.models import Course, CourseCreate, CourseUpdate

logger = get_logger("course-service")
router = APIRouter()
courses_db = DatabaseOperations("courses")

async def _current_user(token: Optional[str] = None):
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

@router.post("/", response_model=Course)
async def create_course(body: CourseCreate, user=Depends(_current_user)):
    """
    Create a new course.

    - **title**: Course title
    - **audience**: Target audience
    - **difficulty**: Difficulty level
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "instructor"])

        # Create course
        course = Course(
            owner_id=user["id"],
            title=body.title,
            audience=body.audience,
            difficulty=body.difficulty,
        )

        doc = course.dict()
        doc["_id"] = course.id
        doc["created_at"] = datetime.now(timezone.utc)

        await courses_db.insert_one(doc)

        logger.info("Course created", extra={
            "course_id": course.id,
            "title": course.title,
            "owner_id": user["id"]
        })

        return course

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to create course", extra={
            "title": body.title,
            "owner_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to create course")

@router.get("/", response_model=List[Course])
async def list_courses(
    limit: int = 50,
    offset: int = 0,
    published_only: bool = False,
    user=Depends(_current_user)
):
    """
    List courses with visibility filtering.

    - **limit**: Maximum number of courses to return
    - **offset**: Number of courses to skip
    - **published_only**: Return only published courses
    """
    try:
        # Build query based on user permissions
        if user["role"] in ["admin", "auditor"]:
            query = {}
            if published_only:
                query["published"] = True
        else:
            query = {
                "$or": [
                    {"published": True},
                    {"owner_id": user["id"]},
                    {"enrolled_user_ids": user["id"]},
                ]
            }

        # Get courses
        courses = await courses_db.find_many(
            query,
            sort=[("created_at", -1)],
            limit=limit,
            skip=offset
        )

        # Convert to Course models with legacy data handling
        valid_courses = []
        for doc in courses:
            # Handle legacy data
            if "_id" in doc and "id" not in doc:
                doc["id"] = doc["_id"]

            # Skip courses missing required fields
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
                logger.warning("Skipping invalid course", extra={
                    "course_id": doc.get("id", "unknown"),
                    "error": str(e)
                })
                continue

        return valid_courses

    except Exception as e:
        logger.error("Failed to list courses", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve courses")

@router.get("/{course_id}", response_model=Course)
async def get_course(course_id: str, user=Depends(_current_user)):
    """
    Get a specific course.

    - **course_id**: Course identifier
    """
    try:
        # Get course document
        doc = await courses_db.find_one({"_id": course_id})
        if not doc:
            raise NotFoundError("Course not found")

        # Check visibility permissions
        if not (
            doc.get("published")
            or doc.get("owner_id") == user["id"]
            or user["role"] in ["admin", "auditor"]
            or user["id"] in doc.get("enrolled_user_ids", [])
        ):
            raise AuthorizationError("Not authorized to view this course")

        return Course(**doc)

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get course", extra={
            "course_id": course_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve course")

@router.put("/{course_id}", response_model=Course)
async def update_course(course_id: str, body: CourseUpdate, user=Depends(_current_user)):
    """
    Update a course.

    - **course_id**: Course identifier
    - **body**: Update data
    """
    try:
        # Get existing course
        doc = await courses_db.find_one({"_id": course_id})
        if not doc:
            raise NotFoundError("Course not found")

        # Check permissions
        if not (user["role"] in ["admin", "instructor"] or doc.get("owner_id") == user["id"]):
            raise AuthorizationError("Not authorized to update this course")

        # Prepare updates
        changes = {k: v for k, v in body.dict().items() if v is not None}
        if changes:
            changes["updated_at"] = datetime.now(timezone.utc)
            await courses_db.update_one({"_id": course_id}, changes)
            doc.update(changes)

            logger.info("Course updated", extra={
                "course_id": course_id,
                "updated_by": user["id"],
                "updated_fields": list(changes.keys())
            })

        return Course(**doc)

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to update course", extra={
            "course_id": course_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to update course")

@router.post("/{course_id}/enroll")
async def enroll_course(course_id: str, user=Depends(_current_user)):
    """
    Enroll user in a course.

    - **course_id**: Course identifier
    """
    try:
        # Verify course exists
        course = await courses_db.find_one({"_id": course_id})
        if not course:
            raise NotFoundError("Course not found")

        # Add user to enrolled list
        await courses_db.update_one(
            {"_id": course_id},
            {"$addToSet": {"enrolled_user_ids": user["id"]}}
        )

        logger.info("User enrolled in course", extra={
            "course_id": course_id,
            "user_id": user["id"]
        })

        return {"status": "enrolled", "message": "Successfully enrolled in course"}

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to enroll in course", extra={
            "course_id": course_id,
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to enroll in course")

@router.delete("/{course_id}/enroll")
async def unenroll_course(course_id: str, user=Depends(_current_user)):
    """
    Unenroll user from a course.

    - **course_id**: Course identifier
    """
    try:
        # Verify course exists
        course = await courses_db.find_one({"_id": course_id})
        if not course:
            raise NotFoundError("Course not found")

        # Remove user from enrolled list
        await courses_db.update_one(
            {"_id": course_id},
            {"$pull": {"enrolled_user_ids": user["id"]}}
        )

        logger.info("User unenrolled from course", extra={
            "course_id": course_id,
            "user_id": user["id"]
        })

        return {"status": "unenrolled", "message": "Successfully unenrolled from course"}

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to unenroll from course", extra={
            "course_id": course_id,
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to unenroll from course")

@router.get("/stats/summary")
async def get_course_stats(user=Depends(_current_user)):
    """
    Get course statistics summary.
    """
    try:
        # Check permissions
        if user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only instructors can access course statistics")

        # Get course counts
        total_courses = await courses_db.count_documents({})
        published_courses = await courses_db.count_documents({"published": True})

        # Get enrollment statistics
        courses = await courses_db.find_many({})
        total_enrollments = sum(len(course.get("enrolled_user_ids", [])) for course in courses)

        return {
            "total_courses": total_courses,
            "published_courses": published_courses,
            "draft_courses": total_courses - published_courses,
            "total_enrollments": total_enrollments,
            "average_enrollment_per_course": round(total_enrollments / max(total_courses, 1), 1)
        }

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get course stats", extra={"error": str(e)})
        raise HTTPException(500, "Failed to retrieve course statistics")