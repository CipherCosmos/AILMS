"""
Assignment management routes for Assessment Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("assessment-service")
router = APIRouter()
assignments_db = DatabaseOperations("assignments")

@router.post("/")
async def create_assignment(
    assignment_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new assignment.

    - **course_id**: ID of the course this assignment belongs to
    - **title**: Assignment title
    - **description**: Assignment description
    - **due_at**: Due date (optional)
    - **rubric**: Grading rubric (optional)
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only admins and instructors can create assignments")

        # Validate required fields
        course_id = assignment_data.get("course_id")
        title = assignment_data.get("title")

        if not course_id:
            raise ValidationError("Course ID is required", "course_id")
        if not title:
            raise ValidationError("Assignment title is required", "title")

        # Verify course exists (would need to call course service)
        # For now, we'll assume the course exists

        from shared.database.database import _uuid
        assignment = {
            "_id": _uuid(),
            "course_id": course_id,
            "title": title,
            "description": assignment_data.get("description", ""),
            "due_at": assignment_data.get("due_at"),
            "rubric": assignment_data.get("rubric", []),
            "created_by": current_user["id"],
            "created_at": datetime.now(timezone.utc)
        }

        await assignments_db.insert_one(assignment)

        logger.info("Assignment created", extra={
            "assignment_id": assignment["_id"],
            "course_id": course_id,
            "created_by": current_user["id"]
        })

        return {
            "status": "created",
            "assignment_id": assignment["_id"],
            "message": "Assignment created successfully"
        }

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to create assignment", extra={
            "course_id": assignment_data.get("course_id"),
            "error": str(e)
        })
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
        assignments = await assignments_db.find_many({"course_id": course_id})

        # Add submission status for current user
        submissions_db = DatabaseOperations("submissions")
        for assignment in assignments:
            submission_count = len(await submissions_db.find_many({
                "assignment_id": assignment["_id"],
                "user_id": current_user["id"]
            }))
            assignment["submitted"] = submission_count > 0

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
        raise HTTPException(500, "Failed to retrieve assignments")

@router.get("/{assignment_id}")
async def get_assignment(
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific assignment.

    - **assignment_id**: Assignment identifier
    """
    try:
        assignment = await assignments_db.find_one({"_id": assignment_id})

        if not assignment:
            raise NotFoundError("Assignment", assignment_id)

        # Check if user has access to this assignment's course
        # For now, we'll assume they do

        # Add submission status
        submissions_db = DatabaseOperations("submissions")
        submission_count = len(await submissions_db.find_many({
            "assignment_id": assignment_id,
            "user_id": current_user["id"]
        }))
        assignment["submitted"] = submission_count > 0

        return assignment

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to get assignment", extra={
            "assignment_id": assignment_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve assignment")

@router.put("/{assignment_id}")
async def update_assignment(
    assignment_id: str,
    assignment_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an assignment.

    - **assignment_id**: Assignment identifier
    - **title**: New title (optional)
    - **description**: New description (optional)
    - **due_at**: New due date (optional)
    - **rubric**: New rubric (optional)
    """
    try:
        # Get existing assignment
        assignment = await assignments_db.find_one({"_id": assignment_id})
        if not assignment:
            raise NotFoundError("Assignment", assignment_id)

        # Check permissions
        if not (
            current_user["role"] in ["admin", "instructor"] or
            assignment.get("created_by") == current_user["id"]
        ):
            raise AuthorizationError("Not authorized to update this assignment")

        # Prepare updates
        updates = {}
        if "title" in assignment_data:
            updates["title"] = assignment_data["title"]
        if "description" in assignment_data:
            updates["description"] = assignment_data["description"]
        if "due_at" in assignment_data:
            updates["due_at"] = assignment_data["due_at"]
        if "rubric" in assignment_data:
            updates["rubric"] = assignment_data["rubric"]

        if updates:
            updates["updated_at"] = datetime.now(timezone.utc)
            await assignments_db.update_one({"_id": assignment_id}, updates)

            logger.info("Assignment updated", extra={
                "assignment_id": assignment_id,
                "updated_fields": list(updates.keys())
            })

        return {"status": "updated", "message": "Assignment updated successfully"}

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to update assignment", extra={
            "assignment_id": assignment_id,
            "error": str(e)
        })
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
        # Get existing assignment
        assignment = await assignments_db.find_one({"_id": assignment_id})
        if not assignment:
            raise NotFoundError("Assignment", assignment_id)

        # Check permissions
        if not (
            current_user["role"] in ["admin", "instructor"] or
            assignment.get("created_by") == current_user["id"]
        ):
            raise AuthorizationError("Not authorized to delete this assignment")

        # Delete assignment
        await assignments_db.delete_one({"_id": assignment_id})

        # Delete all submissions for this assignment
        submissions_db = DatabaseOperations("submissions")
        submissions_to_delete = await submissions_db.find_many({"assignment_id": assignment_id})
        for submission in submissions_to_delete:
            await submissions_db.delete_one({"_id": submission["_id"]})

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
        raise HTTPException(500, "Failed to delete assignment")