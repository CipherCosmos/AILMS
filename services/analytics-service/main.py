"""
Analytics Service - Handles learning analytics and reporting
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

app = FastAPI(title='Analytics Service', version='1.0.0')

# JWT token validation for service-to-service calls
async def _current_user(token: Optional[str] = None):
    """Validate JWT token for service-to-service calls"""
    if not token:
        raise HTTPException(401, "No authentication token provided")

    try:
        import jwt
        from shared.config.config import settings

        # Decode and validate JWT token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        # Verify token hasn't expired
        from datetime import datetime, timezone
        if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(401, "Token has expired")

        # Get user from database to ensure they still exist
        db = get_database()
        user = await db.users.find_one({"_id": payload.get("sub")})
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

@app.get("/analytics/course/{course_id}")
async def get_course_analytics(course_id: str, user=Depends(_current_user)):
    """Get analytics for a course"""
    _require_role(user, ["admin", "instructor"])

    db = get_database()

    # Get enrollment data
    enrollments = await db.courses.count_documents({"_id": course_id})

    # Get progress data
    progress_data = await db.course_progress.find({"course_id": course_id}).to_list(1000)

    # Calculate completion rate
    completed_count = len([p for p in progress_data if p.get("completed")])
    completion_rate = (completed_count / max(enrollments, 1)) * 100

    return {
        "course_id": course_id,
        "enrollments": enrollments,
        "completion_rate": round(completion_rate, 1),
        "total_progress_records": len(progress_data)
    }

@app.get("/analytics/student/{user_id}")
async def get_student_analytics(user_id: str, user=Depends(_current_user)):
    """Get analytics for a student"""
    if user["id"] != user_id and user["role"] not in ["admin", "instructor"]:
        raise HTTPException(403, "Not authorized")

    db = get_database()

    # Get student's progress data
    progress_data = await db.course_progress.find({"user_id": user_id}).to_list(20)

    # Calculate metrics
    lessons_completed = sum([p.get("lessons_progress", []) for p in progress_data], [])
    lessons_completed = sum(1 for lesson in lessons_completed if lesson.get("completed"))

    total_time_spent = sum([p.get("time_spent", 0) for p in progress_data])

    if progress_data:
        progress_percentage = sum([p.get("overall_progress", 0) for p in progress_data]) / len(progress_data)
    else:
        progress_percentage = 0

    return {
        "user_id": user_id,
        "lessons_completed": lessons_completed,
        "total_time_spent": total_time_spent,
        "progress_percentage": round(progress_percentage, 1)
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "analytics"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Analytics Service", "status": "running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=settings.environment == 'development')