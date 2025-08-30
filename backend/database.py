from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from typing import Dict, Any
from fastapi import HTTPException
from config import settings
import uuid

# Global variables for database connection
client = None
db = None
fs_bucket = None

def init_database():
    """Initialize database connection"""
    global client, db, fs_bucket
    if client is None:
        client = AsyncIOMotorClient(settings.mongo_url)
        db = client[settings.db_name]
        fs_bucket = AsyncIOMotorGridFSBucket(db)
    return db, fs_bucket

def get_database():
    """Get database instance, initializing if needed"""
    if db is None:
        init_database()
    return db

def get_fs_bucket():
    """Get GridFS bucket instance, initializing if needed"""
    if fs_bucket is None:
        init_database()
    return fs_bucket

def _uuid() -> str:
    return str(uuid.uuid4())

async def _insert_one(collection: str, doc: Dict[str, Any]):
    if "_id" not in doc:
        doc["_id"] = doc.get("id", _uuid())
    db = get_database()
    await db[collection].insert_one(doc)

async def _update_one(collection: str, filt: Dict[str, Any], update: Dict[str, Any]):
    db = get_database()
    await db[collection].update_one(filt, {'$set': update})

async def _find_one(collection: str, filt: Dict[str, Any]):
    db = get_database()
    return await db[collection].find_one(filt)

async def _require(collection: str, filt: Dict[str, Any], msg: str):
    doc = await _find_one(collection, filt)
    if not doc:
        raise HTTPException(404, msg)
    return doc