"""
Course Service Business Logic Layer
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import json

from shared.common.logging import get_logger
from shared.common.errors import NotFoundError, ValidationError, DatabaseError, AuthorizationError

from database.database import course_db
from models import (
    Course, CourseCreate, CourseUpdate,
    Lesson, LessonCreate, LessonUpdate,
    CourseProgress, CourseProgressCreate, CourseProgressUpdate,
    CourseStats, EnrollmentResponse
)
from config.config import course_service_settings

logger = get_logger("course-service")

class CourseService:
    """Course service business logic"""

    def __init__(self):
        self.db = course_db

    # Course operations
    async def create_course(self, course_data: CourseCreate, owner_id: str) -> Course:
        """Create new course"""
        try:
            # Validate course data
            if len(course_data.title) > course_service_settings.max_course_title_length:
                raise ValidationError("Course title too long", "title")

            if course_data.description and len(course_data.description) > course_service_settings.max_course_description_length:
                raise ValidationError("Course description too long", "description")

            # Create course document
            course_dict = course_data.dict()
            course_dict["owner_id"] = owner_id
            course_dict["enrolled_user_ids"] = []

            course_id = await self.db.create_course(course_dict)

            # Get created course
            created_course = await self.get_course(course_id)
            if not created_course:
                raise DatabaseError("create_course", "Failed to retrieve created course")

            logger.info("Course created", extra={
                "course_id": course_id,
                "title": course_data.title,
                "owner_id": owner_id
            })

            return created_course

        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to create course", extra={
                "title": course_data.title,
                "owner_id": owner_id,
                "error": str(e)
            })
            raise DatabaseError("create_course", f"Course creation failed: {str(e)}")

    async def get_course(self, course_id: str, user_id: Optional[str] = None) -> Optional[Course]:
        """Get course with access control"""
        try:
            course_data = await self.db.get_course(course_id)
            if not course_data:
                return None

            # Check access permissions
            if user_id and not self._can_access_course(course_data, user_id):
                raise AuthorizationError("Not authorized to access this course")

            return Course(**course_data)

        except AuthorizationError:
            raise
        except Exception as e:
            logger.error("Failed to get course", extra={
                "course_id": course_id,
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_course", f"Course retrieval failed: {str(e)}")

    async def update_course(self, course_id: str, updates: CourseUpdate, user_id: str) -> Course:
        """Update course"""
        try:
            # Get existing course
            existing_course = await self.get_course(course_id, user_id)
            if not existing_course:
                raise NotFoundError("Course", course_id)

            # Check permissions
            if not self._can_modify_course(existing_course, user_id):
                raise AuthorizationError("Not authorized to modify this course")

            # Validate updates
            if updates.title and len(updates.title) > course_service_settings.max_course_title_length:
                raise ValidationError("Course title too long", "title")

            if updates.description and len(updates.description) > course_service_settings.max_course_description_length:
                raise ValidationError("Course description too long", "description")

            # Apply updates
            update_dict = updates.dict(exclude_unset=True)
            success = await self.db.update_course(course_id, update_dict)

            if not success:
                raise DatabaseError("update_course", "Failed to update course")

            # Get updated course
            updated_course = await self.get_course(course_id, user_id)
            if not updated_course:
                raise DatabaseError("update_course", "Failed to retrieve updated course")

            logger.info("Course updated", extra={
                "course_id": course_id,
                "updated_by": user_id,
                "updated_fields": list(update_dict.keys())
            })

            return updated_course

        except (NotFoundError, ValidationError, AuthorizationError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to update course", extra={
                "course_id": course_id,
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("update_course", f"Course update failed: {str(e)}")

    async def list_courses(self, query: Dict[str, Any], user_id: Optional[str] = None,
                          limit: int = 50, offset: int = 0) -> List[Course]:
        """List courses with filtering and access control"""
        try:
            # Build access control query
            if user_id:
                access_query = self._build_access_query(user_id)
                if query:
                    access_query.update(query)
                else:
                    query = access_query
            elif not query:
                query = {"published": True}  # Default to published only for anonymous users

            courses_data = await self.db.list_courses(query, limit, offset)

            # Convert to Course objects with legacy data handling
            courses = []
            for course_data in courses_data:
                try:
                    # Handle legacy data
                    if "_id" in course_data and "id" not in course_data:
                        course_data["id"] = course_data["_id"]

                    # Handle legacy courses that have 'topic' instead of 'title'
                    if not course_data.get("title") and course_data.get("topic"):
                        course_data["title"] = course_data["topic"]

                    # Ensure required fields have defaults
                    course_data.setdefault("audience", "General")
                    course_data.setdefault("difficulty", "beginner")
                    course_data.setdefault("lessons", [])
                    course_data.setdefault("quiz", [])
                    course_data.setdefault("published", False)
                    course_data.setdefault("enrolled_user_ids", [])

                    courses.append(Course(**course_data))

                except Exception as e:
                    logger.warning("Skipping invalid course", extra={
                        "course_id": course_data.get("id", "unknown"),
                        "error": str(e)
                    })
                    continue

            return courses

        except Exception as e:
            logger.error("Failed to list courses", extra={
                "user_id": user_id,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("list_courses", f"Course listing failed: {str(e)}")

    async def enroll_user(self, course_id: str, user_id: str) -> EnrollmentResponse:
        """Enroll user in course"""
        try:
            # Verify course exists and is accessible
            course = await self.get_course(course_id, user_id)
            if not course:
                raise NotFoundError("Course", course_id)

            # Check if already enrolled
            if user_id in course.enrolled_user_ids:
                return EnrollmentResponse(
                    status="already_enrolled",
                    message="User is already enrolled in this course"
                )

            # Enroll user
            success = await self.db.enroll_user(course_id, user_id)
            if not success:
                raise DatabaseError("enroll_user", "Failed to enroll user")

            logger.info("User enrolled in course", extra={
                "course_id": course_id,
                "user_id": user_id
            })

            return EnrollmentResponse(
                status="enrolled",
                message="Successfully enrolled in course"
            )

        except (NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to enroll user", extra={
                "course_id": course_id,
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("enroll_user", f"User enrollment failed: {str(e)}")

    async def unenroll_user(self, course_id: str, user_id: str) -> EnrollmentResponse:
        """Unenroll user from course"""
        try:
            # Verify course exists
            course = await self.get_course(course_id, user_id)
            if not course:
                raise NotFoundError("Course", course_id)

            # Check if enrolled
            if user_id not in course.enrolled_user_ids:
                return EnrollmentResponse(
                    status="not_enrolled",
                    message="User is not enrolled in this course"
                )

            # Unenroll user
            success = await self.db.unenroll_user(course_id, user_id)
            if not success:
                raise DatabaseError("unenroll_user", "Failed to unenroll user")

            logger.info("User unenrolled from course", extra={
                "course_id": course_id,
                "user_id": user_id
            })

            return EnrollmentResponse(
                status="unenrolled",
                message="Successfully unenrolled from course"
            )

        except (NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to unenroll user", extra={
                "course_id": course_id,
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("unenroll_user", f"User unenrollment failed: {str(e)}")

    async def get_course_stats(self, user_id: str) -> CourseStats:
        """Get course statistics"""
        try:
            # Check permissions
            # For now, allow instructors and admins to see stats
            # In production, this would check user roles

            stats_data = await self.db.get_course_stats()
            return CourseStats(**stats_data)

        except Exception as e:
            logger.error("Failed to get course stats", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_course_stats", f"Course stats retrieval failed: {str(e)}")

    # Helper methods
    def _can_access_course(self, course_data: Dict[str, Any], user_id: str) -> bool:
        """Check if user can access course"""
        # Public access if published
        if course_data.get("published"):
            return True

        # Owner access
        if course_data.get("owner_id") == user_id:
            return True

        # Enrolled user access
        if user_id in course_data.get("enrolled_user_ids", []):
            return True

        # Admin access (would check roles in production)
        # For now, deny access to unpublished courses for non-owners/non-enrolled
        return False

    def _can_modify_course(self, course: Course, user_id: str) -> bool:
        """Check if user can modify course"""
        # Owner can modify
        if course.owner_id == user_id:
            return True

        # Admin can modify (would check roles in production)
        # For now, only owner can modify
        return False

    def _build_access_query(self, user_id: str) -> Dict[str, Any]:
        """Build MongoDB query for course access control"""
        return {
            "$or": [
                {"published": True},
                {"owner_id": user_id},
                {"enrolled_user_ids": user_id}
            ]
        }

# Global service instance
course_service = CourseService()