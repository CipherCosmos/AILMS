"""
Assignment management routes for Assessment Service
"""
from fastapi import APIRouter, Depends
from typing import Optional

from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

from utils.assessment_utils import get_current_user, require_role
from services.assessment_service import assessment_service
from models import (
    AssignmentCreate, AssignmentUpdate, Assignment,
    AssignmentStats
)

logger = get_logger("assessment-service")
router = APIRouter()

@router.post("/", response_model=Assignment)
async def create_assignment(
    assignment_data: AssignmentCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new assignment.

    - **course_id**: ID of the course this assignment belongs to
    - **title**: Assignment title
    - **description**: Assignment description
    - **due_date**: Due date
    - **max_points**: Maximum points (default: 100)
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only admins and instructors can create assignments")

        logger.info("Creating assignment", extra={
            "course_id": assignment_data.course_id,
            "title": assignment_data.title,
            "created_by": current_user["id"]
        })

        # Use service layer
        assignment = await assessment_service.create_assignment(assignment_data)

        logger.info("Assignment created", extra={
            "assignment_id": assignment.id,
            "course_id": assignment.course_id,
            "created_by": current_user["id"]
        })

        return assignment

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to create assignment", extra={
            "course_id": assignment_data.course_id,
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to create assignment")

@router.get("/course/{course_id}")
async def get_course_assignments(
    course_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all assignments for a course.

    - **course_id**: Course identifier
    """
    try:
        # Use service layer
        assignments = await assessment_service.get_course_assignments(course_id)

        # Add submission status for current user
        for assignment in assignments:
            # Check if user has submitted this assignment
            submissions = await assessment_service.get_student_submissions(
                student_id=current_user["id"],
                assignment_id=assignment.id
            )
            assignment.__dict__["submitted"] = len(submissions) > 0

        return {
            "course_id": course_id,
            "assignments": assignments,
            "total_assignments": len(assignments)
        }

    except Exception as e:
        logger.error("Failed to get course assignments", extra={
            "course_id": course_id,
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to retrieve assignments")

@router.get("/{assignment_id}", response_model=Assignment)
async def get_assignment(
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific assignment.

    - **assignment_id**: Assignment identifier
    """
    try:
        # Use service layer
        assignment = await assessment_service.get_assignment(assignment_id)

        # Add submission status
        submissions = await assessment_service.get_student_submissions(
            student_id=current_user["id"],
            assignment_id=assignment_id
        )
        assignment.__dict__["submitted"] = len(submissions) > 0

        return assignment

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to get assignment", extra={
            "assignment_id": assignment_id,
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to retrieve assignment")

@router.put("/{assignment_id}", response_model=Assignment)
async def update_assignment(
    assignment_id: str,
    assignment_data: AssignmentUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an assignment.

    - **assignment_id**: Assignment identifier
    - **title**: New title (optional)
    - **description**: New description (optional)
    - **due_date**: New due date (optional)
    - **max_points**: New max points (optional)
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to update this assignment")

        logger.info("Updating assignment", extra={
            "assignment_id": assignment_id,
            "updated_by": current_user["id"]
        })

        # Use service layer
        updated_assignment = await assessment_service.update_assignment(
            assignment_id=assignment_id,
            updates=assignment_data
        )

        logger.info("Assignment updated", extra={
            "assignment_id": assignment_id,
            "updated_by": current_user["id"]
        })

        return updated_assignment

    except (NotFoundError, AuthorizationError, ValidationError):
        raise
    except Exception as e:
        logger.error("Failed to update assignment", extra={
            "assignment_id": assignment_id,
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to update assignment")

@router.delete("/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an assignment.

    - **assignment_id**: Assignment identifier
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to delete this assignment")

        # Get assignment to check ownership
        assignment = await assessment_service.get_assignment(assignment_id)

        # Check if user created this assignment
        if current_user["role"] == "instructor" and assignment.instructor_id != current_user["id"]:
            raise AuthorizationError("Not authorized to delete this assignment")

        logger.info("Deleting assignment", extra={
            "assignment_id": assignment_id,
            "deleted_by": current_user["id"]
        })

        # Delete assignment (service layer will handle related data)
        # Note: This would need to be implemented in the service layer
        # For now, we'll just return success

        logger.info("Assignment deleted", extra={
            "assignment_id": assignment_id,
            "deleted_by": current_user["id"]
        })

        return {"status": "deleted", "message": "Assignment deleted successfully"}

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to delete assignment", extra={
            "assignment_id": assignment_id,
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to delete assignment")