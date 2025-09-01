"""
Grading routes for Assessment Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("assessment-service")
router = APIRouter()

@router.post("/grade/{submission_id}")
async def grade_submission(
    submission_id: str,
    grade_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Grade a submission.

    - **submission_id**: Submission identifier
    - **ai_grade**: AI-generated grade (optional)
    - **manual_grade**: Manual grade (optional)
    - **feedback**: Grading feedback (optional)
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only instructors can grade submissions")

        # Get submission
        submissions_db = DatabaseOperations("submissions")
        submission = await submissions_db.find_one({"_id": submission_id})
        if not submission:
            raise NotFoundError("Submission", submission_id)

        # Verify assignment ownership
        assignments_db = DatabaseOperations("assignments")
        assignment = await assignments_db.find_one({
            "_id": submission["assignment_id"]
        })
        if not assignment:
            raise NotFoundError("Assignment", submission["assignment_id"])

        # Check if instructor owns the assignment or is admin
        if not (
            current_user["role"] == "admin" or
            assignment.get("created_by") == current_user["id"]
        ):
            raise AuthorizationError("Not authorized to grade this submission")

        # Prepare grade data
        updates = {
            "graded_by": current_user["id"],
            "graded_at": datetime.now(timezone.utc)
        }

        if "ai_grade" in grade_data:
            updates["ai_grade"] = grade_data["ai_grade"]
        if "manual_grade" in grade_data:
            updates["manual_grade"] = grade_data["manual_grade"]
        if "feedback" in grade_data:
            updates["feedback"] = grade_data["feedback"]

        # Update submission
        submissions_db = DatabaseOperations("submissions")
        await submissions_db.update_one({"_id": submission_id}, updates)

        logger.info("Submission graded", extra={
            "submission_id": submission_id,
            "assignment_id": submission["assignment_id"],
            "graded_by": current_user["id"],
            "grade_type": "ai" if "ai_grade" in grade_data else "manual"
        })

        return {
            "status": "graded",
            "submission_id": submission_id,
            "message": "Submission graded successfully"
        }

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to grade submission", extra={
            "submission_id": submission_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to grade submission")

@router.get("/grades/{assignment_id}")
async def get_assignment_grades(
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all grades for an assignment (instructor only).

    - **assignment_id**: Assignment identifier
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only instructors can view grades")

        # Verify assignment exists and ownership
        assignments_db = DatabaseOperations("assignments")
        assignment = await assignments_db.find_one({"_id": assignment_id})
        if not assignment:
            raise NotFoundError("Assignment", assignment_id)

        if not (
            current_user["role"] == "admin" or
            assignment.get("created_by") == current_user["id"]
        ):
            raise AuthorizationError("Not authorized to view grades for this assignment")

        # Get all submissions with grades
        submissions_db = DatabaseOperations("submissions")
        submissions = await submissions_db.find_many({
            "assignment_id": assignment_id
        })

        # Calculate grade statistics
        graded_submissions = [s for s in submissions if s.get("ai_grade") or s.get("manual_grade")]
        total_submissions = len(submissions)
        graded_count = len(graded_submissions)

        # Calculate average grade
        grades = []
        for submission in graded_submissions:
            if submission.get("manual_grade"):
                grades.append(submission["manual_grade"].get("score", 0))
            elif submission.get("ai_grade"):
                grades.append(submission["ai_grade"].get("score", 0))

        avg_grade = sum(grades) / len(grades) if grades else 0

        return {
            "assignment_id": assignment_id,
            "assignment_title": assignment.get("title"),
            "total_submissions": total_submissions,
            "graded_submissions": graded_count,
            "average_grade": round(avg_grade, 1),
            "grading_progress": round((graded_count / total_submissions * 100), 1) if total_submissions > 0 else 0,
            "submissions": graded_submissions
        }

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get assignment grades", extra={
            "assignment_id": assignment_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve grades")

@router.get("/my-grades")
async def get_my_grades(current_user: dict = Depends(get_current_user)):
    """
    Get all grades for current user.
    """
    try:
        # Get all user's submissions with grades
        submissions_db = DatabaseOperations("submissions")
        submissions = await submissions_db.find_many({
            "user_id": current_user["id"]
        })

        # Filter only graded submissions
        graded_submissions = []
        for submission in submissions:
            if submission.get("ai_grade") or submission.get("manual_grade"):
                # Get assignment details
                assignments_db = DatabaseOperations("assignments")
                assignment = await assignments_db.find_one({
                    "_id": submission["assignment_id"]
                })

                graded_submission = {
                    "submission_id": submission["_id"],
                    "assignment_id": submission["assignment_id"],
                    "assignment_title": assignment.get("title") if assignment else "Unknown",
                    "course_id": assignment.get("course_id") if assignment else None,
                    "submitted_at": submission.get("submitted_at"),
                    "graded_at": submission.get("graded_at"),
                    "ai_grade": submission.get("ai_grade"),
                    "manual_grade": submission.get("manual_grade"),
                    "feedback": submission.get("feedback")
                }
                graded_submissions.append(graded_submission)

        # Calculate statistics
        total_graded = len(graded_submissions)
        avg_grade = 0

        if graded_submissions:
            grades = []
            for submission in graded_submissions:
                if submission.get("manual_grade"):
                    grades.append(submission["manual_grade"].get("score", 0))
                elif submission.get("ai_grade"):
                    grades.append(submission["ai_grade"].get("score", 0))

            avg_grade = sum(grades) / len(grades) if grades else 0

        return {
            "total_graded_submissions": total_graded,
            "average_grade": round(avg_grade, 1),
            "submissions": graded_submissions
        }

    except Exception as e:
        logger.error("Failed to get user grades", extra={
            "user_id": current_user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve grades")

@router.put("/grade/{submission_id}/feedback")
async def update_feedback(
    submission_id: str,
    feedback_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Update feedback for a graded submission.

    - **submission_id**: Submission identifier
    - **feedback**: Updated feedback text
    """
    try:
        # Check permissions
        if current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Only instructors can update feedback")

        # Get submission
        submissions_db = DatabaseOperations("submissions")
        submission = await submissions_db.find_one({"_id": submission_id})
        if not submission:
            raise NotFoundError("Submission", submission_id)

        # Verify assignment ownership
        assignments_db = DatabaseOperations("assignments")
        assignment = await assignments_db.find_one({
            "_id": submission["assignment_id"]
        })
        if not assignment:
            raise NotFoundError("Assignment", submission["assignment_id"])

        if not (
            current_user["role"] == "admin" or
            assignment.get("created_by") == current_user["id"]
        ):
            raise AuthorizationError("Not authorized to update feedback for this submission")

        # Update feedback
        updates = {
            "feedback": feedback_data.get("feedback", ""),
            "feedback_updated_at": datetime.now(timezone.utc),
            "feedback_updated_by": current_user["id"]
        }

        submissions_db = DatabaseOperations("submissions")
        await submissions_db.update_one({"_id": submission_id}, updates)

        logger.info("Feedback updated", extra={
            "submission_id": submission_id,
            "updated_by": current_user["id"]
        })

        return {"status": "updated", "message": "Feedback updated successfully"}

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to update feedback", extra={
            "submission_id": submission_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to update feedback")