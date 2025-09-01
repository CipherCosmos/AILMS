"""
Database Indexes for Performance Optimization
"""

from typing import List, Tuple, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from shared.common.logging import get_logger

logger = get_logger("database-indexes")

# Database indexes for performance
INDEXES = [
    # Users collection
    ("users", [("email", 1)], {"unique": True}),
    ("users", [("role", 1)]),
    ("users", [("created_at", -1)]),

    # Courses collection
    ("courses", [("owner_id", 1)]),
    ("courses", [("published", 1)]),
    ("courses", [("enrolled_user_ids", 1)]),
    ("courses", [("created_at", -1)]),
    ("courses", [("title", "text"), ("description", "text")]),

    # Course progress collection
    ("course_progress", [("course_id", 1), ("user_id", 1)], {"unique": True}),
    ("course_progress", [("user_id", 1)]),
    ("course_progress", [("completed", 1)]),

    # Assignments collection
    ("assignments", [("course_id", 1)]),
    ("assignments", [("due_at", 1)]),
    ("assignments", [("created_at", -1)]),

    # Submissions collection
    ("submissions", [("assignment_id", 1)]),
    ("submissions", [("user_id", 1)]),
    ("submissions", [("created_at", -1)]),

    # Notifications collection
    ("notifications", [("user_id", 1)]),
    ("notifications", [("read", 1)]),
    ("notifications", [("created_at", -1)]),

    # Discussions collection
    ("discussions", [("course_id", 1)]),
    ("discussions", [("user_id", 1)]),
    ("discussions", [("created_at", -1)]),

    # Analytics collection
    ("course_analytics", [("course_id", 1)]),
    ("course_analytics", [("last_updated", -1)]),

    # User profiles
    ("user_profiles", [("user_id", 1)], {"unique": True}),

    # Career profiles
    ("career_profiles", [("user_id", 1)], {"unique": True}),

    # Achievements
    ("achievements", [("user_id", 1)]),
    ("achievements", [("earned_date", -1)]),

    # Study sessions
    ("study_sessions", [("user_id", 1)]),
    ("study_sessions", [("session_date", -1)]),
]

async def create_indexes(db: AsyncIOMotorDatabase):
    """Create optimized database indexes"""

    for collection_name, keys, options in INDEXES:
        try:
            collection = db[collection_name]
            await collection.create_index(keys, **options)
            logger.info(f"✅ Created index on {collection_name}: {keys}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to create index on {collection_name}: {e}")

async def create_collection_indexes(db: AsyncIOMotorDatabase, collection_name: str, indexes: List[Tuple]):
    """Create indexes for a specific collection"""

    for keys, options in indexes:
        try:
            collection = db[collection_name]
            await collection.create_index(keys, **options)
            logger.info(f"✅ Created index on {collection_name}: {keys}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to create index on {collection_name}: {e}")

async def drop_index(db: AsyncIOMotorDatabase, collection_name: str, index_name: str):
    """Drop a specific index"""

    try:
        collection = db[collection_name]
        await collection.drop_index(index_name)
        logger.info(f"✅ Dropped index {index_name} from {collection_name}")
    except Exception as e:
        logger.warning(f"⚠️  Failed to drop index {index_name} from {collection_name}: {e}")

async def list_indexes(db: AsyncIOMotorDatabase, collection_name: str) -> List[Dict[str, Any]]:
    """List all indexes for a collection"""

    try:
        collection = db[collection_name]
        indexes = await collection.list_indexes().to_list(length=None)
        return indexes
    except Exception as e:
        logger.error(f"Failed to list indexes for {collection_name}: {e}")
        return []