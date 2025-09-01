"""
File management routes for File Service
"""
from fastapi import APIRouter, Depends
from typing import Optional

from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

from utils.file_utils import get_current_user, require_role
from services.file_service import file_service
from models import (
    File, FileUpdate, FileStorageStats, FileType
)

logger = get_logger("file-service")
router = APIRouter()

@router.get("/")
async def list_files(
    limit: int = 50,
    file_type: Optional[FileType] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List user's files.

    - **limit**: Maximum number of files to return
    - **file_type**: Filter by file type (optional)
    """
    try:
        # Use service layer
        files = await file_service.get_user_files(current_user["id"], limit, file_type)

        logger.info("Files listed", extra={
            "user_id": current_user["id"],
            "count": len(files),
            "file_type": file_type.value if file_type else None
        })

        return {
            "files": [file.dict() for file in files],
            "total": len(files),
            "limit": limit,
            "file_type_filter": file_type.value if file_type else None
        }

    except Exception as e:
        logger.error("Failed to list files", extra={
            "user_id": current_user["id"],
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to retrieve files")

@router.get("/{file_id}", response_model=File)
async def get_file(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get file metadata.

    - **file_id**: File identifier
    """
    try:
        # Use service layer
        file_data = await file_service.get_file_metadata(file_id, current_user["id"])

        logger.info("File retrieved", extra={
            "file_id": file_id,
            "user_id": current_user["id"]
        })

        return file_data

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get file", extra={
            "file_id": file_id,
            "error": str(e)
        })
        from fastapi import HTTPException
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
        # Use service layer
        success = await file_service.delete_file(file_id, current_user["id"])

        if not success:
            raise NotFoundError("File", file_id)

        logger.info("File deleted", extra={
            "file_id": file_id,
            "user_id": current_user["id"]
        })

        return {"status": "deleted", "message": "File deleted successfully"}

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to delete file", extra={
            "file_id": file_id,
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to delete file")

@router.get("/stats/summary", response_model=FileStorageStats)
async def get_file_stats(current_user: dict = Depends(get_current_user)):
    """
    Get file statistics for the current user.
    """
    try:
        # Use service layer
        stats = await file_service.get_storage_stats(current_user["id"])

        logger.info("File stats retrieved", extra={
            "user_id": current_user["id"],
            "total_files": stats.total_files,
            "total_size": stats.total_size
        })

        return stats

    except Exception as e:
        logger.error("Failed to get file stats", extra={
            "user_id": current_user["id"],
            "error": str(e)
        })
        from fastapi import HTTPException
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
        # Prepare updates
        allowed_fields = ["filename", "description", "tags"]
        updates = {k: v for k, v in metadata.items() if k in allowed_fields}

        if not updates:
            from fastapi import HTTPException
            raise HTTPException(400, "No valid fields provided for update")

        # Use service layer
        update_data = FileUpdate(**updates)
        updated_file = await file_service.update_file_metadata(file_id, current_user["id"], update_data)

        logger.info("File metadata updated", extra={
            "file_id": file_id,
            "updated_fields": list(updates.keys())
        })

        return {"status": "updated", "message": "File metadata updated successfully"}

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to update file metadata", extra={
            "file_id": file_id,
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to update file metadata")