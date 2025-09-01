"""
Assessment Service Business Logic Layer
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from shared.common.logging import get_logger
from shared.common.errors import ValidationError, DatabaseError, NotFoundError

from database.database import assessment_db
from models import (
    Assignment, AssignmentCreate, AssignmentUpdate,
    Submission, SubmissionCreate, SubmissionUpdate,
    Grade, GradeCreate, GradeUpdate,
    Rubric, RubricCreate,
    AssignmentStats, StudentPerformance
)
from config.config import assessment_service_settings

logger = get_logger("assessment-service")

class AssessmentService:
    """Assessment service business logic"""

    def __init__(self):
        self.db = assessment_db

    # Assignment operations
    async def create_assignment(self, assignment_data: AssignmentCreate) -> Assignment:
        """Create new assignment"""
        try:
            # Validate assignment data
            self._validate_assignment_data(assignment_data)

            assignment_dict = assignment_data.dict(by_alias=True)
            assignment_id = await self.db.create_assignment(assignment_dict)

            # Get created assignment
            created_assignment = await self.db.get_assignment(assignment_id)
            if not created_assignment:
                raise DatabaseError("create_assignment", "Failed to retrieve created assignment")

            logger.info("Assignment created", extra={
                "assignment_id": assignment_id,
                "course_id": assignment_data.course_id,
                "instructor_id": assignment_data.instructor_id
            })

            return Assignment(**created_assignment)

        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to create assignment", extra={"error": str(e)})
            raise DatabaseError("create_assignment", f"Assignment creation failed: {str(e)}")

    async def get_assignment(self, assignment_id: str) -> Assignment:
        """Get assignment by ID"""
        try:
            assignment_data = await self.db.get_assignment(assignment_id)
            if not assignment_data:
                raise NotFoundError("Assignment", assignment_id)

            return Assignment(**assignment_data)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get assignment", extra={
                "assignment_id": assignment_id,
                "error": str(e)
            })
            raise DatabaseError("get_assignment", f"Assignment retrieval failed: {str(e)}")

    async def get_course_assignments(self, course_id: str) -> List[Assignment]:
        """Get all assignments for a course"""
        try:
            assignments_data = await self.db.get_course_assignments(course_id)
            return [Assignment(**assignment) for assignment in assignments_data]

        except Exception as e:
            logger.error("Failed to get course assignments", extra={
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("get_course_assignments", f"Course assignments retrieval failed: {str(e)}")

    async def update_assignment(self, assignment_id: str, updates: AssignmentUpdate) -> Assignment:
        """Update assignment"""
        try:
            # Validate updates
            update_dict = updates.dict(exclude_unset=True)
            if not update_dict:
                raise ValidationError("No valid fields provided for update", "updates")

            # Update assignment
            success = await self.db.update_assignment(assignment_id, update_dict)
            if not success:
                raise DatabaseError("update_assignment", "Failed to update assignment")

            # Get updated assignment
            updated_assignment = await self.get_assignment(assignment_id)

            logger.info("Assignment updated", extra={
                "assignment_id": assignment_id,
                "updated_fields": list(update_dict.keys())
            })

            return updated_assignment

        except (ValidationError, NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to update assignment", extra={
                "assignment_id": assignment_id,
                "error": str(e)
            })
            raise DatabaseError("update_assignment", f"Assignment update failed: {str(e)}")

    # Submission operations
    async def create_submission(self, submission_data: SubmissionCreate) -> Submission:
        """Create new submission"""
        try:
            # Validate submission
            await self._validate_submission(submission_data)

            submission_dict = submission_data.dict(by_alias=True)
            submission_id = await self.db.create_submission(submission_dict)

            # Get created submission
            created_submission = await self.db.get_submission(submission_id)
            if not created_submission:
                raise DatabaseError("create_submission", "Failed to retrieve created submission")

            logger.info("Submission created", extra={
                "submission_id": submission_id,
                "assignment_id": submission_data.assignment_id,
                "student_id": submission_data.student_id
            })

            return Submission(**created_submission)

        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to create submission", extra={"error": str(e)})
            raise DatabaseError("create_submission", f"Submission creation failed: {str(e)}")

    async def get_submission(self, submission_id: str) -> Submission:
        """Get submission by ID"""
        try:
            submission_data = await self.db.get_submission(submission_id)
            if not submission_data:
                raise NotFoundError("Submission", submission_id)

            return Submission(**submission_data)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get submission", extra={
                "submission_id": submission_id,
                "error": str(e)
            })
            raise DatabaseError("get_submission", f"Submission retrieval failed: {str(e)}")

    async def get_assignment_submissions(self, assignment_id: str) -> List[Submission]:
        """Get all submissions for an assignment"""
        try:
            submissions_data = await self.db.get_assignment_submissions(assignment_id)
            return [Submission(**submission) for submission in submissions_data]

        except Exception as e:
            logger.error("Failed to get assignment submissions", extra={
                "assignment_id": assignment_id,
                "error": str(e)
            })
            raise DatabaseError("get_assignment_submissions", f"Assignment submissions retrieval failed: {str(e)}")

    async def get_student_submissions(self, student_id: str, assignment_id: Optional[str] = None) -> List[Submission]:
        """Get student's submissions"""
        try:
            submissions_data = await self.db.get_student_submissions(student_id, assignment_id)
            return [Submission(**submission) for submission in submissions_data]

        except Exception as e:
            logger.error("Failed to get student submissions", extra={
                "student_id": student_id,
                "assignment_id": assignment_id,
                "error": str(e)
            })
            raise DatabaseError("get_student_submissions", f"Student submissions retrieval failed: {str(e)}")

    # Grade operations
    async def create_grade(self, grade_data: GradeCreate) -> Grade:
        """Create new grade"""
        try:
            # Validate grade
            self._validate_grade(grade_data)

            grade_dict = grade_data.dict(by_alias=True)
            grade_id = await self.db.create_grade(grade_dict)

            logger.info("Grade created", extra={
                "grade_id": grade_id,
                "submission_id": grade_data.submission_id,
                "assignment_id": grade_data.assignment_id,
                "student_id": grade_data.student_id,
                "score": grade_data.score
            })

            # Get created grade
            created_grade = await self.db.get_grade(grade_data.submission_id)
            if not created_grade:
                raise DatabaseError("create_grade", "Failed to retrieve created grade")

            return Grade(**created_grade)

        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to create grade", extra={"error": str(e)})
            raise DatabaseError("create_grade", f"Grade creation failed: {str(e)}")

    async def get_grade(self, submission_id: str) -> Optional[Grade]:
        """Get grade for submission"""
        try:
            grade_data = await self.db.get_grade(submission_id)
            if not grade_data:
                return None

            return Grade(**grade_data)

        except Exception as e:
            logger.error("Failed to get grade", extra={
                "submission_id": submission_id,
                "error": str(e)
            })
            raise DatabaseError("get_grade", f"Grade retrieval failed: {str(e)}")

    async def update_grade(self, submission_id: str, updates: GradeUpdate) -> Grade:
        """Update grade"""
        try:
            update_dict = updates.dict(exclude_unset=True)
            if not update_dict:
                raise ValidationError("No valid fields provided for update", "updates")

            success = await self.db.update_grade(submission_id, update_dict)
            if not success:
                raise DatabaseError("update_grade", "Failed to update grade")

            # Get updated grade
            updated_grade = await self.get_grade(submission_id)
            if not updated_grade:
                raise DatabaseError("update_grade", "Failed to retrieve updated grade")

            logger.info("Grade updated", extra={
                "submission_id": submission_id,
                "updated_fields": list(update_dict.keys())
            })

            return updated_grade

        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to update grade", extra={
                "submission_id": submission_id,
                "error": str(e)
            })
            raise DatabaseError("update_grade", f"Grade update failed: {str(e)}")

    # Analytics operations
    async def get_assignment_stats(self, assignment_id: str) -> AssignmentStats:
        """Get statistics for an assignment"""
        try:
            stats_data = await self.db.get_assignment_stats(assignment_id)
            return AssignmentStats(**stats_data)

        except Exception as e:
            logger.error("Failed to get assignment stats", extra={
                "assignment_id": assignment_id,
                "error": str(e)
            })
            raise DatabaseError("get_assignment_stats", f"Assignment stats retrieval failed: {str(e)}")

    async def get_student_performance(self, student_id: str, course_id: Optional[str] = None) -> StudentPerformance:
        """Get student's performance statistics"""
        try:
            performance_data = await self.db.get_student_performance(student_id, course_id)
            return StudentPerformance(**performance_data)

        except Exception as e:
            logger.error("Failed to get student performance", extra={
                "student_id": student_id,
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("get_student_performance", f"Student performance retrieval failed: {str(e)}")

    # Helper methods
    def _validate_assignment_data(self, assignment_data: AssignmentCreate) -> None:
        """Validate assignment data"""
        if len(assignment_data.title) > assessment_service_settings.max_assignment_title_length:
            raise ValidationError("Assignment title too long", "title")

        if len(assignment_data.description) > assessment_service_settings.max_assignment_description_length:
            raise ValidationError("Assignment description too long", "description")

        if assignment_data.due_date <= datetime.now(timezone.utc):
            raise ValidationError("Due date must be in the future", "due_date")

    async def _validate_submission(self, submission_data: SubmissionCreate) -> None:
        """Validate submission"""
        # Check if assignment exists
        assignment = await self.db.get_assignment(submission_data.assignment_id)
        if not assignment:
            raise NotFoundError("Assignment", submission_data.assignment_id)

        # Check if assignment is still open
        if assignment["status"] != "published":
            raise ValidationError("Assignment is not available for submission", "assignment_id")

        # Check due date
        due_date = assignment["due_date"]
        if isinstance(due_date, str):
            due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))

        is_late = datetime.now(timezone.utc) > due_date
        if is_late and not assignment.get("allow_late_submissions", True):
            raise ValidationError("Late submissions are not allowed", "submitted_at")

        # Check submission content length
        if len(submission_data.content) > assessment_service_settings.max_submission_content_length:
            raise ValidationError("Submission content too long", "content")

    def _validate_grade(self, grade_data: GradeCreate) -> None:
        """Validate grade data"""
        if grade_data.score < 0 or grade_data.score > grade_data.max_score:
            raise ValidationError("Grade score out of valid range", "score")

        if grade_data.feedback and len(grade_data.feedback) > 2000:
            raise ValidationError("Feedback too long", "feedback")

# Global service instance
assessment_service = AssessmentService()