"""
Assessment Service Database Operations
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import json

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.errors import DatabaseError, NotFoundError
from config.config import assessment_service_settings

# Simple cache implementation for now
class SimpleCache:
    """Simple in-memory cache for assessment service"""
    def __init__(self):
        self.cache = {}

    async def init_cache(self):
        pass

    async def close(self):
        self.cache.clear()

    async def get(self, key: str) -> Optional[str]:
        return self.cache.get(key)

    async def set(self, key: str, value: str, ttl: int = 300):
        self.cache[key] = value
        # In production, implement TTL logic

    async def delete(self, key: str):
        self.cache.pop(key, None)

logger = get_logger("assessment-service-db")

class AssessmentDatabase:
    """Assessment service database operations with caching"""

    def __init__(self):
        self.client = None
        self.db = None
        self.cache = SimpleCache()
        self._initialized = False

    async def init_db(self):
        """Initialize database connection"""
        if self._initialized:
            return

        try:
            self.client = AsyncIOMotorClient(settings.mongo_url)
            self.db = self.client[settings.db_name]
            await self._create_indexes()
            await self.cache.init_cache()
            self._initialized = True
            logger.info("Assessment database initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize assessment database", extra={"error": str(e)})
            raise DatabaseError("init_db", f"Database initialization failed: {str(e)}")

    async def close_db(self):
        """Close database connection"""
        if self.client:
            self.client.close()
        await self.cache.close()
        self._initialized = False
        logger.info("Assessment database connection closed")

    async def _create_indexes(self):
        """Create necessary database indexes"""
        try:
            # Assignments indexes
            await self.db.assignments.create_index("course_id")
            await self.db.assignments.create_index("instructor_id")
            await self.db.assignments.create_index("due_date")
            await self.db.assignments.create_index("status")
            await self.db.assignments.create_index([("course_id", 1), ("due_date", -1)])

            # Submissions indexes
            await self.db.submissions.create_index("assignment_id")
            await self.db.submissions.create_index("student_id")
            await self.db.submissions.create_index("submitted_at")
            await self.db.submissions.create_index([("assignment_id", 1), ("student_id", 1)])
            await self.db.submissions.create_index([("student_id", 1), ("submitted_at", -1)])

            # Grades indexes
            await self.db.grades.create_index("submission_id", unique=True)
            await self.db.grades.create_index("assignment_id")
            await self.db.grades.create_index("student_id")
            await self.db.grades.create_index("graded_at")
            await self.db.grades.create_index([("assignment_id", 1), ("student_id", 1)])

            # Rubrics indexes
            await self.db.rubrics.create_index("assignment_id")
            await self.db.rubrics.create_index("created_by")

            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error("Failed to create database indexes", extra={"error": str(e)})

    # Assignment operations
    async def create_assignment(self, assignment_data: Dict[str, Any]) -> str:
        """Create new assignment"""
        try:
            assignment_data["created_at"] = datetime.now(timezone.utc)
            assignment_data["updated_at"] = datetime.now(timezone.utc)

            result = await self.db.assignments.insert_one(assignment_data)
            assignment_id = str(result.inserted_id)

            logger.info("Assignment created", extra={"assignment_id": assignment_id})
            return assignment_id

        except Exception as e:
            logger.error("Failed to create assignment", extra={"error": str(e)})
            raise DatabaseError("create_assignment", f"Assignment creation failed: {str(e)}")

    async def get_assignment(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        """Get assignment by ID"""
        try:
            assignment = await self.db.assignments.find_one({"_id": assignment_id})
            return assignment

        except Exception as e:
            logger.error("Failed to get assignment", extra={
                "assignment_id": assignment_id,
                "error": str(e)
            })
            raise DatabaseError("get_assignment", f"Assignment retrieval failed: {str(e)}")

    async def get_course_assignments(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all assignments for a course"""
        try:
            assignments = await self.db.assignments.find(
                {"course_id": course_id}
            ).sort("due_date", 1).to_list(50)
            return assignments

        except Exception as e:
            logger.error("Failed to get course assignments", extra={
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("get_course_assignments", f"Course assignments retrieval failed: {str(e)}")

    async def update_assignment(self, assignment_id: str, updates: Dict[str, Any]) -> bool:
        """Update assignment"""
        try:
            updates["updated_at"] = datetime.now(timezone.utc)
            result = await self.db.assignments.update_one(
                {"_id": assignment_id},
                {"$set": updates}
            )

            success = result.modified_count > 0
            if success:
                logger.info("Assignment updated", extra={"assignment_id": assignment_id})

            return success

        except Exception as e:
            logger.error("Failed to update assignment", extra={
                "assignment_id": assignment_id,
                "error": str(e)
            })
            raise DatabaseError("update_assignment", f"Assignment update failed: {str(e)}")

    # Submission operations
    async def create_submission(self, submission_data: Dict[str, Any]) -> str:
        """Create new submission"""
        try:
            submission_data["submitted_at"] = datetime.now(timezone.utc)

            result = await self.db.submissions.insert_one(submission_data)
            submission_id = str(result.inserted_id)

            logger.info("Submission created", extra={"submission_id": submission_id})
            return submission_id

        except Exception as e:
            logger.error("Failed to create submission", extra={"error": str(e)})
            raise DatabaseError("create_submission", f"Submission creation failed: {str(e)}")

    async def get_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Get submission by ID"""
        try:
            submission = await self.db.submissions.find_one({"_id": submission_id})
            return submission

        except Exception as e:
            logger.error("Failed to get submission", extra={
                "submission_id": submission_id,
                "error": str(e)
            })
            raise DatabaseError("get_submission", f"Submission retrieval failed: {str(e)}")

    async def get_assignment_submissions(self, assignment_id: str) -> List[Dict[str, Any]]:
        """Get all submissions for an assignment"""
        try:
            submissions = await self.db.submissions.find(
                {"assignment_id": assignment_id}
            ).sort("submitted_at", -1).to_list(100)
            return submissions

        except Exception as e:
            logger.error("Failed to get assignment submissions", extra={
                "assignment_id": assignment_id,
                "error": str(e)
            })
            raise DatabaseError("get_assignment_submissions", f"Assignment submissions retrieval failed: {str(e)}")

    async def get_student_submissions(self, student_id: str, assignment_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get student's submissions"""
        try:
            query = {"student_id": student_id}
            if assignment_id:
                query["assignment_id"] = assignment_id

            submissions = await self.db.submissions.find(query).sort("submitted_at", -1).to_list(20)
            return submissions

        except Exception as e:
            logger.error("Failed to get student submissions", extra={
                "student_id": student_id,
                "assignment_id": assignment_id,
                "error": str(e)
            })
            raise DatabaseError("get_student_submissions", f"Student submissions retrieval failed: {str(e)}")

    # Grade operations
    async def create_grade(self, grade_data: Dict[str, Any]) -> str:
        """Create new grade"""
        try:
            grade_data["graded_at"] = datetime.now(timezone.utc)

            result = await self.db.grades.insert_one(grade_data)
            grade_id = str(result.inserted_id)

            logger.info("Grade created", extra={"grade_id": grade_id})
            return grade_id

        except Exception as e:
            logger.error("Failed to create grade", extra={"error": str(e)})
            raise DatabaseError("create_grade", f"Grade creation failed: {str(e)}")

    async def get_grade(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Get grade for submission"""
        try:
            grade = await self.db.grades.find_one({"submission_id": submission_id})
            return grade

        except Exception as e:
            logger.error("Failed to get grade", extra={
                "submission_id": submission_id,
                "error": str(e)
            })
            raise DatabaseError("get_grade", f"Grade retrieval failed: {str(e)}")

    async def update_grade(self, submission_id: str, grade_data: Dict[str, Any]) -> bool:
        """Update grade"""
        try:
            grade_data["graded_at"] = datetime.now(timezone.utc)
            result = await self.db.grades.update_one(
                {"submission_id": submission_id},
                {"$set": grade_data},
                upsert=True
            )

            success = result.modified_count > 0 or result.upserted_id is not None
            if success:
                logger.info("Grade updated", extra={"submission_id": submission_id})

            return success

        except Exception as e:
            logger.error("Failed to update grade", extra={
                "submission_id": submission_id,
                "error": str(e)
            })
            raise DatabaseError("update_grade", f"Grade update failed: {str(e)}")

    # Analytics operations
    async def get_assignment_stats(self, assignment_id: str) -> Dict[str, Any]:
        """Get statistics for an assignment"""
        try:
            # Get submission count
            submission_count = await self.db.submissions.count_documents({"assignment_id": assignment_id})

            # Get graded submissions
            graded_count = await self.db.grades.count_documents({"assignment_id": assignment_id})

            # Get average grade
            pipeline = [
                {"$match": {"assignment_id": assignment_id}},
                {"$group": {"_id": None, "avg_grade": {"$avg": "$score"}}}
            ]

            avg_result = await self.db.grades.aggregate(pipeline).to_list(1)
            avg_grade = avg_result[0]["avg_grade"] if avg_result else 0

            return {
                "assignment_id": assignment_id,
                "total_submissions": submission_count,
                "graded_submissions": graded_count,
                "average_grade": round(avg_grade, 2),
                "grading_progress": round((graded_count / max(submission_count, 1)) * 100, 1)
            }

        except Exception as e:
            logger.error("Failed to get assignment stats", extra={
                "assignment_id": assignment_id,
                "error": str(e)
            })
            raise DatabaseError("get_assignment_stats", f"Assignment stats retrieval failed: {str(e)}")

    async def get_student_performance(self, student_id: str, course_id: Optional[str] = None) -> Dict[str, Any]:
        """Get student's performance statistics"""
        try:
            # Build query
            query: Dict[str, Any] = {"student_id": student_id}
            if course_id:
                query["course_id"] = course_id

            # Get grades
            pipeline = [
                {"$match": query},
                {"$lookup": {
                    "from": "assignments",
                    "localField": "assignment_id",
                    "foreignField": "_id",
                    "as": "assignment"
                }},
                {"$unwind": "$assignment"},
                {"$project": {
                    "score": 1,
                    "assignment_id": 1,
                    "course_id": "$assignment.course_id"
                }}
            ]

            grades = await self.db.grades.aggregate(pipeline).to_list(50)

            if not grades:
                return {
                    "student_id": student_id,
                    "total_assignments": 0,
                    "average_score": 0,
                    "performance_level": "No Data"
                }

            scores = [grade["score"] for grade in grades if grade.get("score")]
            avg_score = sum(scores) / len(scores) if scores else 0

            return {
                "student_id": student_id,
                "total_assignments": len(grades),
                "average_score": round(avg_score, 2),
                "performance_level": "Excellent" if avg_score >= 90 else "Good" if avg_score >= 80 else "Average" if avg_score >= 70 else "Needs Improvement"
            }

        except Exception as e:
            logger.error("Failed to get student performance", extra={
                "student_id": student_id,
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("get_student_performance", f"Student performance retrieval failed: {str(e)}")

# Global database instance
assessment_db = AssessmentDatabase()