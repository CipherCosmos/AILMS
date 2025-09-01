"""
Course management routes for Course Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

from shared.common.auth import get_current_user, require_admin
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

from services.course_service import course_service
from models import Course, CourseCreate, CourseUpdate, CourseStats, EnrollmentResponse

logger = get_logger("course-service")
router = APIRouter()

@router.post("/", response_model=Course)
async def create_course(body: CourseCreate, user: dict = Depends(get_current_user)):
    """
    Create a new course.

    - **title**: Course title
    - **audience**: Target audience
    - **difficulty**: Difficulty level
    """
    try:
        # Check permissions (would be handled in service layer)
        if user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only instructors and admins can create courses")

        # Create course using service layer
        course = await course_service.create_course(body, user["id"])
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
    user: dict = Depends(get_current_user)
):
    """
    List courses with visibility filtering.

    - **limit**: Maximum number of courses to return
    - **offset**: Number of courses to skip
    - **published_only**: Return only published courses
    """
    try:
        # Build query based on user permissions
        query = {}
        if published_only:
            query["published"] = True

        # List courses using service layer
        courses = await course_service.list_courses(
            query=query,
            user_id=user["id"],
            limit=limit,
            offset=offset
        )

        return courses

    except Exception as e:
        logger.error("Failed to list courses", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve courses")

@router.get("/{course_id}", response_model=Course)
async def get_course(course_id: str, user: dict = Depends(get_current_user)):
    """
    Get a specific course.

    - **course_id**: Course identifier
    """
    try:
        # Get course using service layer
        course = await course_service.get_course(course_id, user["id"])
        if not course:
            raise NotFoundError("Course", course_id)

        return course

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get course", extra={
            "course_id": course_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve course")

@router.put("/{course_id}", response_model=Course)
async def update_course(course_id: str, body: CourseUpdate, user: dict = Depends(get_current_user)):
    """
    Update a course.

    - **course_id**: Course identifier
    - **body**: Update data
    """
    try:
        # Update course using service layer
        updated_course = await course_service.update_course(course_id, body, user["id"])
        return updated_course

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to update course", extra={
            "course_id": course_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to update course")

@router.post("/{course_id}/enroll", response_model=EnrollmentResponse)
async def enroll_course(course_id: str, user: dict = Depends(get_current_user)):
    """
    Enroll user in a course.

    - **course_id**: Course identifier
    """
    try:
        # Enroll user using service layer
        result = await course_service.enroll_user(course_id, user["id"])
        return result

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to enroll in course", extra={
            "course_id": course_id,
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to enroll in course")

@router.delete("/{course_id}/enroll", response_model=EnrollmentResponse)
async def unenroll_course(course_id: str, user: dict = Depends(get_current_user)):
    """
    Unenroll user from a course.

    - **course_id**: Course identifier
    """
    try:
        # Unenroll user using service layer
        result = await course_service.unenroll_user(course_id, user["id"])
        return result

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to unenroll from course", extra={
            "course_id": course_id,
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to unenroll from course")

@router.get("/stats/summary", response_model=CourseStats)
async def get_course_stats(user: dict = Depends(get_current_user)):
    """
    Get course statistics summary.
    """
    try:
        # Check permissions
        if user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only instructors can access course statistics")

        # Get course stats using service layer
        stats = await course_service.get_course_stats(user["id"])
        return stats

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get course stats", extra={"error": str(e)})
        raise HTTPException(500, "Failed to retrieve course statistics")