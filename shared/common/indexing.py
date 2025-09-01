"""
Database indexing optimization for LMS microservices
"""
import asyncio
from typing import List, Dict, Any
from shared.config.config import settings
from shared.common.logging import get_logger

logger = get_logger("common-indexing")


class DatabaseIndexing:
    """Database indexing manager for optimized query performance"""

    def __init__(self):
        self.indexes_created = set()

    async def create_optimized_indexes(self):
        """Create all optimized indexes for the LMS system"""
        try:
            from shared.common.database import get_database
            db = await get_database()

            # User collection indexes
            await self._create_user_indexes(db)

            # Course collection indexes
            await self._create_course_indexes(db)

            # Course progress indexes
            await self._create_progress_indexes(db)

            # Assignment and submission indexes
            await self._create_assessment_indexes(db)

            # Notification indexes
            await self._create_notification_indexes(db)

            # File indexes
            await self._create_file_indexes(db)

            # Analytics indexes
            await self._create_analytics_indexes(db)

            logger.info("All database indexes created successfully")
            return {"status": "success", "message": "All indexes created"}

        except Exception as e:
            logger.error("Failed to create database indexes", extra={"error": str(e)})
            return {"status": "error", "message": str(e)}

    async def _create_user_indexes(self, db):
        """Create indexes for users collection"""
        collection = db.users

        indexes = [
            # Authentication indexes
            {"key": [("email", 1)], "unique": True, "name": "email_unique"},
            {"key": [("role", 1)], "name": "role_index"},

            # Profile search indexes
            {"key": [("name", 1)], "name": "name_index"},
            {"key": [("created_at", -1)], "name": "created_at_desc"},

            # Compound indexes for common queries
            {"key": [("role", 1), ("created_at", -1)], "name": "role_created_at"},
            {"key": [("email", 1), ("role", 1)], "name": "email_role"},
        ]

        for index_spec in indexes:
            try:
                await collection.create_index(**index_spec)
                self.indexes_created.add(f"users.{index_spec['name']}")
            except Exception as e:
                logger.warning(f"Failed to create index users.{index_spec['name']}", extra={"error": str(e)})

    async def _create_course_indexes(self, db):
        """Create indexes for courses collection"""
        collection = db.courses

        indexes = [
            # Basic course indexes
            {"key": [("owner_id", 1)], "name": "owner_id_index"},
            {"key": [("published", 1)], "name": "published_index"},
            {"key": [("created_at", -1)], "name": "created_at_desc"},
            {"key": [("updated_at", -1)], "name": "updated_at_desc"},

            # Enrollment indexes
            {"key": [("enrolled_user_ids", 1)], "name": "enrolled_users"},

            # Search and filter indexes
            {"key": [("title", "text"), ("description", "text")], "name": "text_search"},
            {"key": [("audience", 1)], "name": "audience_index"},
            {"key": [("difficulty", 1)], "name": "difficulty_index"},
            {"key": [("tags", 1)], "name": "tags_index"},

            # Compound indexes for common queries
            {"key": [("published", 1), ("created_at", -1)], "name": "published_created_at"},
            {"key": [("owner_id", 1), ("published", 1)], "name": "owner_published"},
            {"key": [("audience", 1), ("difficulty", 1)], "name": "audience_difficulty"},
            {"key": [("enrolled_user_ids", 1), ("published", 1)], "name": "enrolled_published"},
        ]

        for index_spec in indexes:
            try:
                await collection.create_index(**index_spec)
                self.indexes_created.add(f"courses.{index_spec['name']}")
            except Exception as e:
                logger.warning(f"Failed to create index courses.{index_spec['name']}", extra={"error": str(e)})

    async def _create_progress_indexes(self, db):
        """Create indexes for course progress collection"""
        collection = db.course_progress

        indexes = [
            # Progress tracking indexes
            {"key": [("user_id", 1)], "name": "user_id_index"},
            {"key": [("course_id", 1)], "name": "course_id_index"},
            {"key": [("completed", 1)], "name": "completed_index"},
            {"key": [("overall_progress", 1)], "name": "progress_index"},
            {"key": [("last_accessed", -1)], "name": "last_accessed_desc"},

            # Unique compound index
            {"key": [("user_id", 1), ("course_id", 1)], "unique": True, "name": "user_course_unique"},

            # Performance indexes
            {"key": [("user_id", 1), ("completed", 1)], "name": "user_completed"},
            {"key": [("course_id", 1), ("completed", 1)], "name": "course_completed"},
            {"key": [("user_id", 1), ("overall_progress", -1)], "name": "user_progress_desc"},
        ]

        for index_spec in indexes:
            try:
                await collection.create_index(**index_spec)
                self.indexes_created.add(f"course_progress.{index_spec['name']}")
            except Exception as e:
                logger.warning(f"Failed to create index course_progress.{index_spec['name']}", extra={"error": str(e)})

    async def _create_assessment_indexes(self, db):
        """Create indexes for assignments and submissions"""
        # Assignments collection
        assignments_collection = db.assignments
        assignment_indexes = [
            {"key": [("course_id", 1)], "name": "course_id_index"},
            {"key": [("due_at", 1)], "name": "due_date_index"},
            {"key": [("created_at", -1)], "name": "created_at_desc"},
            {"key": [("course_id", 1), ("due_at", 1)], "name": "course_due_date"},
        ]

        for index_spec in assignment_indexes:
            try:
                await assignments_collection.create_index(**index_spec)
                self.indexes_created.add(f"assignments.{index_spec['name']}")
            except Exception as e:
                logger.warning(f"Failed to create index assignments.{index_spec['name']}", extra={"error": str(e)})

        # Submissions collection
        submissions_collection = db.submissions
        submission_indexes = [
            {"key": [("user_id", 1)], "name": "user_id_index"},
            {"key": [("assignment_id", 1)], "name": "assignment_id_index"},
            {"key": [("created_at", -1)], "name": "created_at_desc"},
            {"key": [("user_id", 1), ("assignment_id", 1)], "unique": True, "name": "user_assignment_unique"},
            {"key": [("assignment_id", 1), ("created_at", -1)], "name": "assignment_created_desc"},
        ]

        for index_spec in submission_indexes:
            try:
                await submissions_collection.create_index(**index_spec)
                self.indexes_created.add(f"submissions.{index_spec['name']}")
            except Exception as e:
                logger.warning(f"Failed to create index submissions.{index_spec['name']}", extra={"error": str(e)})

    async def _create_notification_indexes(self, db):
        """Create indexes for notifications collection"""
        collection = db.notifications

        indexes = [
            {"key": [("user_id", 1)], "name": "user_id_index"},
            {"key": [("read", 1)], "name": "read_status_index"},
            {"key": [("created_at", -1)], "name": "created_at_desc"},
            {"key": [("type", 1)], "name": "type_index"},
            {"key": [("user_id", 1), ("read", 1)], "name": "user_read_status"},
            {"key": [("user_id", 1), ("created_at", -1)], "name": "user_created_desc"},
            {"key": [("user_id", 1), ("read", 1), ("created_at", -1)], "name": "user_read_created"},
        ]

        for index_spec in indexes:
            try:
                await collection.create_index(**index_spec)
                self.indexes_created.add(f"notifications.{index_spec['name']}")
            except Exception as e:
                logger.warning(f"Failed to create index notifications.{index_spec['name']}", extra={"error": str(e)})

    async def _create_file_indexes(self, db):
        """Create indexes for files collection"""
        collection = db.files

        indexes = [
            {"key": [("uploaded_by", 1)], "name": "uploaded_by_index"},
            {"key": [("content_type", 1)], "name": "content_type_index"},
            {"key": [("uploaded_at", -1)], "name": "uploaded_at_desc"},
            {"key": [("filename", "text")], "name": "filename_text"},
            {"key": [("uploaded_by", 1), ("uploaded_at", -1)], "name": "user_uploaded_desc"},
        ]

        for index_spec in indexes:
            try:
                await collection.create_index(**index_spec)
                self.indexes_created.add(f"files.{index_spec['name']}")
            except Exception as e:
                logger.warning(f"Failed to create index files.{index_spec['name']}", extra={"error": str(e)})

    async def _create_analytics_indexes(self, db):
        """Create indexes for analytics collections"""
        # User profiles
        profiles_collection = db.user_profiles
        profile_indexes = [
            {"key": [("user_id", 1)], "unique": True, "name": "user_id_unique"},
            {"key": [("skills", 1)], "name": "skills_index"},
            {"key": [("preferred_learning_style", 1)], "name": "learning_style_index"},
        ]

        for index_spec in profile_indexes:
            try:
                await profiles_collection.create_index(**index_spec)
                self.indexes_created.add(f"user_profiles.{index_spec['name']}")
            except Exception as e:
                logger.warning(f"Failed to create index user_profiles.{index_spec['name']}", extra={"error": str(e)})

        # Career profiles
        career_collection = db.career_profiles
        career_indexes = [
            {"key": [("user_id", 1)], "unique": True, "name": "user_id_unique"},
            {"key": [("target_roles", 1)], "name": "target_roles_index"},
            {"key": [("skills_to_develop", 1)], "name": "skills_to_develop_index"},
        ]

        for index_spec in career_indexes:
            try:
                await career_collection.create_index(**index_spec)
                self.indexes_created.add(f"career_profiles.{index_spec['name']}")
            except Exception as e:
                logger.warning(f"Failed to create index career_profiles.{index_spec['name']}", extra={"error": str(e)})

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about created indexes"""
        try:
            from shared.common.database import get_database
            db = await get_database()

            stats = {}
            collections = [
                "users", "courses", "course_progress", "assignments",
                "submissions", "notifications", "files", "user_profiles", "career_profiles"
            ]

            for collection_name in collections:
                try:
                    collection = db[collection_name]
                    indexes = await collection.index_information()
                    stats[collection_name] = {
                        "total_indexes": len(indexes),
                        "index_names": list(indexes.keys())
                    }
                except Exception as e:
                    stats[collection_name] = {"error": str(e)}

            return {
                "status": "success",
                "stats": stats,
                "indexes_created": len(self.indexes_created),
                "index_list": list(self.indexes_created)
            }

        except Exception as e:
            logger.error("Failed to get index stats", extra={"error": str(e)})
            return {"status": "error", "message": str(e)}

    async def drop_unused_indexes(self, unused_indexes: List[str]):
        """Drop unused indexes to free up space"""
        try:
            from shared.common.database import get_database
            db = await get_database()

            dropped_indexes = []

            for index_name in unused_indexes:
                try:
                    collection_name, index = index_name.split(".", 1)
                    collection = db[collection_name]
                    await collection.drop_index(index)
                    dropped_indexes.append(index_name)
                    logger.info(f"Dropped unused index: {index_name}")
                except Exception as e:
                    logger.warning(f"Failed to drop index {index_name}", extra={"error": str(e)})

            return {
                "status": "success",
                "dropped_indexes": dropped_indexes,
                "count": len(dropped_indexes)
            }

        except Exception as e:
            logger.error("Failed to drop unused indexes", extra={"error": str(e)})
            return {"status": "error", "message": str(e)}


# Global indexing manager instance
indexing_manager = DatabaseIndexing()


async def create_database_indexes():
    """Convenience function to create all database indexes"""
    return await indexing_manager.create_optimized_indexes()


async def get_index_statistics():
    """Convenience function to get index statistics"""
    return await indexing_manager.get_index_stats()


async def drop_unused_database_indexes(unused_indexes: List[str]):
    """Convenience function to drop unused indexes"""
    return await indexing_manager.drop_unused_indexes(unused_indexes)