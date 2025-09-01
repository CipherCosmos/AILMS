"""
Submission handling routes for Assessment Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("assessment-service")
router = APIRouter()
submissions_db = DatabaseOperations("submissions")

@router.post("/")
async def submit_assignment(
    submission_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit an assignment.

    - **assignment_id**: ID of the assignment being submitted
    - **text_answer**: Text response (optional)
    - **file_ids**: List of uploaded file IDs (optional)
    """
    try:
        assignment_id = submission_data.get("assignment_id")
        text_answer = submission_data.get("text_answer")
        file_ids = submission_data.get("file_ids", [])

        if not assignment_id:
            raise ValidationError("Assignment ID is required", "assignment_id")

        # Verify assignment exists
        assignments_db = DatabaseOperations("assignments")
        assignment = await assignments_db.find_one({"_id": assignment_id})
        if not assignment:
            raise NotFoundError("Assignment", assignment_id)

        # Check if user already submitted
        existing_submission = await submissions_db.find_one({
            "assignment_id": assignment_id,
            "user_id": current_user["id"]
        })

        if existing_submission:
            raise ValidationError("Assignment already submitted", "assignment_id")

        # Check if assignment is past due
        due_at = assignment.get("due_at")
        if due_at:
            due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > due_date:
                logger.warning("Late submission", extra={
                    "assignment_id": assignment_id,
                    "user_id": current_user["id"],
                    "due_date": due_at
                })

        from shared.database.database import _uuid
        submission = {
            "_id": _uuid(),
            "assignment_id": assignment_id,
            "user_id": current_user["id"],
            "text_answer": text_answer,
            "file_ids": file_ids,
            "submitted_at": datetime.now(timezone.utc),
            "status": "submitted"
        }

        await submissions_db.insert_one(submission)

        logger.info("Assignment submitted", extra={
            "submission_id": submission["_id"],
            "assignment_id": assignment_id,
            "user_id": current_user["id"]
        })

        return {
            "status": "submitted",
            "submission_id": submission["_id"],
            "message": "Assignment submitted successfully"
        }

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.error("Failed to submit assignment", extra={
            "assignment_id": submission_data.get("assignment_id"),
            "error": str(e)
        })
        raise HTTPException(500, "Failed to submit assignment")

@router.get("/assignment/{assignment_id}")
async def get_assignment_submissions(
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all submissions for an assignment (instructor only).

    - **assignment_id**: Assignment identifier
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only instructors can view all submissions")

        # Verify assignment exists
        assignments_db = DatabaseOperations("assignments")
        assignment = await assignments_db.find_one({"_id": assignment_id})
        if not assignment:
            raise NotFoundError("Assignment", assignment_id)

        submissions = await submissions_db.find_many({"assignment_id": assignment_id})

        # Add user information to submissions
        for submission in submissions:
            # Would need to get user info from auth service
            # For now, just include user_id
            pass

        return {
            "assignment_id": assignment_id,
            "assignment_title": assignment.get("title"),
            "submissions": submissions,
            "total_submissions": len(submissions)
        }

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get assignment submissions", extra={
            "assignment_id": assignment_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve submissions")

@router.get("/my/{assignment_id}")
async def get_my_submission(
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's submission for an assignment.

    - **assignment_id**: Assignment identifier
    """
    try:
        submission = await submissions_db.find_one({
            "assignment_id": assignment_id,
            "user_id": current_user["id"]
        })

        if not submission:
            return {
                "assignment_id": assignment_id,
                "submitted": False,
                "message": "No submission found"
            }

        return {
            "assignment_id": assignment_id,
            "submitted": True,
            "submission": submission
        }

    except Exception as e:
        logger.error("Failed to get user submission", extra={
            "assignment_id": assignment_id,
            "user_id": current_user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve submission")

@router.put("/{submission_id}")
async def update_submission(
    submission_id: str,
    submission_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a submission (before grading).

    - **submission_id**: Submission identifier
    - **text_answer**: Updated text response (optional)
    - **file_ids**: Updated file IDs (optional)
    """
    try:
        # Get existing submission
        submission = await submissions_db.find_one({"_id": submission_id})
        if not submission:
            raise NotFoundError("Submission", submission_id)

        # Check ownership
        if submission["user_id"] != current_user["id"]:
            raise AuthorizationError("Not authorized to update this submission")

        # Check if already graded
        if submission.get("ai_grade") or submission.get("graded_at"):
            raise ValidationError("Cannot update a graded submission", "submission_id")

        # Prepare updates
        updates = {}
        if "text_answer" in submission_data:
            updates["text_answer"] = submission_data["text_answer"]
        if "file_ids" in submission_data:
            updates["file_ids"] = submission_data["file_ids"]

        if updates:
            updates["updated_at"] = datetime.now(timezone.utc)
            await submissions_db.update_one({"_id": submission_id}, updates)

            logger.info("Submission updated", extra={
                "submission_id": submission_id,
                "updated_fields": list(updates.keys())
            })

        return {"status": "updated", "message": "Submission updated successfully"}

    except (NotFoundError, AuthorizationError, ValidationError):
        raise
    except Exception as e:
        logger.error("Failed to update submission", extra={
            "submission_id": submission_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to update submission")

@router.delete("/{submission_id}")
async def delete_submission(
    submission_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a submission (before grading).

    - **submission_id**: Submission identifier
    """
    try:
        # Get existing submission
        submission = await submissions_db.find_one({"_id": submission_id})
        if not submission:
            raise NotFoundError("Submission", submission_id)

        # Check ownership
        if submission["user_id"] != current_user["id"]:
            raise AuthorizationError("Not authorized to delete this submission")

        # Check if already graded
        if submission.get("ai_grade") or submission.get("graded_at"):
            raise ValidationError("Cannot delete a graded submission", "submission_id")

        # Delete submission
        await submissions_db.delete_one({"_id": submission_id})

        logger.info("Submission deleted", extra={
            "submission_id": submission_id,
            "deleted_by": current_user["id"]
        })

        return {"status": "deleted", "message": "Submission deleted successfully"}

    except (NotFoundError, AuthorizationError, ValidationError):
        raise
    except Exception as e:
        logger.error("Failed to delete submission", extra={
            "submission_id": submission_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to delete submission")