"""
File management routes for File Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import os

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("file-service")
router = APIRouter()
files_db = DatabaseOperations("files")

@router.get("/")
async def list_files(
    limit: int = 50,
    offset: int = 0,
    file_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List user's files.

    - **limit**: Maximum number of files to return
    - **offset**: Number of files to skip
    - **file_type**: Filter by file type (optional)
    """
    try:
        # Build query
        query = {"uploaded_by": current_user["id"]}
        if file_type:
            query["content_type"] = {"$regex": file_type, "$options": "i"}

        # Get files
        files = await files_db.find_many(
            query,
            sort=[("uploaded_at", -1)],
            limit=limit,
            skip=offset
        )

        # Get total count
        total_count = len(await files_db.find_many(query))

        return {
            "files": files,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "file_type_filter": file_type
        }

    except Exception as e:
        logger.error("Failed to list files", extra={
            "user_id": current_user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve files")

@router.get("/{file_id}")
async def get_file(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get file metadata.

    - **file_id**: File identifier
    """
    try:
        file_doc = await files_db.find_one({
            "_id": file_id,
            "uploaded_by": current_user["id"]
        })

        if not file_doc:
            raise NotFoundError("File", file_id)

        return file_doc

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to get file", extra={
            "file_id": file_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve file")

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a file.

    - **file_id**: File identifier
    """
    try:
        # Get file document
        file_doc = await files_db.find_one({
            "_id": file_id,
            "uploaded_by": current_user["id"]
        })

        if not file_doc:
            raise NotFoundError("File", file_id)

        # Delete file from disk
        file_path = file_doc.get("file_path")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info("File deleted from disk", extra={
                    "file_path": file_path,
                    "file_id": file_id
                })
            except Exception as e:
                logger.warning("Failed to delete file from disk", extra={
                    "file_path": file_path,
                    "error": str(e)
                })

        # Delete from database
        result = await files_db.delete_one({"_id": file_id})
        if not result:
            raise HTTPException(404, "File not found")

        logger.info("File deleted", extra={
            "file_id": file_id,
            "user_id": current_user["id"]
        })

        return {"status": "deleted", "message": "File deleted successfully"}

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to delete file", extra={
            "file_id": file_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to delete file")

@router.get("/stats/summary")
async def get_file_stats(current_user: dict = Depends(get_current_user)):
    """
    Get file statistics for the current user.
    """
    try:
        # Get user's files
        files = await files_db.find_many({"uploaded_by": current_user["id"]})

        if not files:
            return {
                "total_files": 0,
                "total_size": 0,
                "file_types": {},
                "message": "No files found"
            }

        # Calculate statistics
        total_size = sum(file.get("size", 0) for file in files)
        file_types = {}

        for file in files:
            content_type = file.get("content_type", "unknown")
            if content_type not in file_types:
                file_types[content_type] = 0
            file_types[content_type] += 1

        # Get recent uploads (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc).timestamp() - (30 * 24 * 60 * 60)
        recent_files = [
            f for f in files
            if f.get("uploaded_at", datetime.min.replace(tzinfo=timezone.utc)).timestamp() > thirty_days_ago
        ]

        return {
            "total_files": len(files),
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": file_types,
            "recent_uploads": len(recent_files),
            "average_file_size": round(total_size / max(len(files), 1), 2)
        }

    except Exception as e:
        logger.error("Failed to get file stats", extra={
            "user_id": current_user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve file statistics")

@router.put("/{file_id}/metadata")
async def update_file_metadata(
    file_id: str,
    metadata: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Update file metadata.

    - **file_id**: File identifier
    - **metadata**: Metadata to update
    """
    try:
        # Get existing file
        file_doc = await files_db.find_one({
            "_id": file_id,
            "uploaded_by": current_user["id"]
        })

        if not file_doc:
            raise NotFoundError("File", file_id)

        # Prepare updates
        allowed_fields = ["filename", "description", "tags"]
        updates = {k: v for k, v in metadata.items() if k in allowed_fields}
        updates["updated_at"] = datetime.now(timezone.utc)

        if updates:
            result = await files_db.update_one({"_id": file_id}, updates)
            if not result:
                raise HTTPException(404, "File not found")

            logger.info("File metadata updated", extra={
                "file_id": file_id,
                "updated_fields": list(updates.keys())
            })

        return {"status": "updated", "message": "File metadata updated successfully"}

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to update file metadata", extra={
            "file_id": file_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to update file metadata")