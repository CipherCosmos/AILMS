"""
Assessment Service - Handles assignments, quizzes, and grading
"""
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.config.config import settings
from shared.database.database import get_database, _uuid
from shared.models.models import Assignment, Submission

app = FastAPI(title='Assessment Service', version='1.0.0')

# Mock user authentication for service-to-service calls
async def _current_user(token: Optional[str] = None):
    """Mock user authentication for service-to-service calls"""
    return {"id": "user_123", "role": "instructor", "email": "user@example.com", "name": "Test User"}

def _require_role(user, allowed: list[str]):
    """Check if user has required role"""
    if user.get("role") not in allowed:
        raise HTTPException(403, "Insufficient permissions")

@app.post("/assignments")
async def create_assignment(assignment_data: dict, user=Depends(_current_user)):
    """Create a new assignment"""
    _require_role(user, ["admin", "instructor"])

    db = get_database()
    assignment = {
        "_id": _uuid(),
        "course_id": assignment_data.get("course_id"),
        "title": assignment_data.get("title"),
        "description": assignment_data.get("description", ""),
        "due_at": assignment_data.get("due_at"),
        "rubric": assignment_data.get("rubric", []),
        "created_at": datetime.now(timezone.utc)
    }

    await db.assignments.insert_one(assignment)
    return {"status": "created", "assignment_id": assignment["_id"]}

@app.get("/assignments/{course_id}")
async def get_assignments(course_id: str, user=Depends(_current_user)):
    """Get assignments for a course"""
    db = get_database()
    assignments = await db.assignments.find({"course_id": course_id}).to_list(50)
    return assignments

@app.post("/submissions")
async def submit_assignment(submission_data: dict, user=Depends(_current_user)):
    """Submit an assignment"""
    db = get_database()
    submission = {
        "_id": _uuid(),
        "assignment_id": submission_data.get("assignment_id"),
        "user_id": user["id"],
        "text_answer": submission_data.get("text_answer"),
        "file_ids": submission_data.get("file_ids", []),
        "created_at": datetime.now(timezone.utc)
    }

    await db.submissions.insert_one(submission)
    return {"status": "submitted", "submission_id": submission["_id"]}

@app.get("/submissions/{assignment_id}")
async def get_submissions(assignment_id: str, user=Depends(_current_user)):
    """Get submissions for an assignment"""
    _require_role(user, ["admin", "instructor"])

    db = get_database()
    submissions = await db.submissions.find({"assignment_id": assignment_id}).to_list(100)
    return submissions

@app.post("/grade/{submission_id}")
async def grade_submission(submission_id: str, grade_data: dict, user=Depends(_current_user)):
    """Grade a submission"""
    _require_role(user, ["admin", "instructor"])

    db = get_database()
    await db.submissions.update_one(
        {"_id": submission_id},
        {"$set": {
            "ai_grade": grade_data.get("ai_grade"),
            "graded_at": datetime.now(timezone.utc)
        }}
    )
    return {"status": "graded"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "assessment"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Assessment Service", "status": "running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=settings.environment == 'development')