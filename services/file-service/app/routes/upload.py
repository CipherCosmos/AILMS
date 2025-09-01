"""
File upload routes for File Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import Optional
import os
import uuid
import aiofiles

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations
from shared.common.errors import ValidationError, AuthorizationError
from shared.common.logging import get_logger
from shared.database.database import _uuid

logger = get_logger("file-service")
router = APIRouter()
files_db = DatabaseOperations("files")

# File upload configuration
ALLOWED_TYPES = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf',
    'text/plain', 'text/csv',
    'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
UPLOAD_DIR = "uploads"

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = None,
    tags: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a file.

    - **file**: The file to upload
    - **description**: Optional file description
    - **tags**: Optional comma-separated tags
    """
    try:
        # Validate file type
        if file.content_type not in ALLOWED_TYPES:
            raise ValidationError(
                f"File type '{file.content_type}' not allowed. Allowed types: {', '.join(ALLOWED_TYPES)}",
                "file"
            )

        # Read file content
        content = await file.read()

        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise ValidationError(
                f"File size {len(content)} bytes exceeds maximum allowed size of {MAX_FILE_SIZE} bytes",
                "file"
            )

        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        # Create upload directory if it doesn't exist
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # Save file to disk
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

        # Save file metadata to database
        file_doc = {
            "_id": _uuid(),
            "filename": file.filename,
            "unique_filename": unique_filename,
            "file_path": file_path,
            "content_type": file.content_type,
            "size": len(content),
            "description": description,
            "tags": tag_list,
            "uploaded_by": current_user["id"],
            "uploaded_at": datetime.now(timezone.utc)
        }

        await files_db.insert_one(file_doc)

        logger.info("File uploaded successfully", extra={
            "file_id": file_doc["_id"],
            "filename": file.filename,
            "size": len(content),
            "content_type": file.content_type,
            "uploaded_by": current_user["id"]
        })

        return {
            "file_id": file_doc["_id"],
            "filename": file.filename,
            "size": len(content),
            "content_type": file.content_type,
            "message": "File uploaded successfully"
        }

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to upload file", extra={
            "filename": file.filename if file else None,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to upload file")

@router.post("/upload/multiple")
async def upload_multiple_files(
    files: list[UploadFile] = File(...),
    descriptions: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Upload multiple files.

    - **files**: List of files to upload
    - **descriptions**: Optional comma-separated descriptions for each file
    """
    try:
        if len(files) > 10:
            raise ValidationError("Maximum 10 files can be uploaded at once", "files")

        descriptions_list = []
        if descriptions:
            descriptions_list = [desc.strip() for desc in descriptions.split(',')]

        uploaded_files = []

        for i, file in enumerate(files):
            # Validate file type
            if file.content_type not in ALLOWED_TYPES:
                logger.warning("Skipping file with invalid type", extra={
                    "filename": file.filename,
                    "content_type": file.content_type
                })
                continue

            # Read file content
            content = await file.read()

            # Validate file size
            if len(content) > MAX_FILE_SIZE:
                logger.warning("Skipping file that exceeds size limit", extra={
                    "filename": file.filename,
                    "size": len(content)
                })
                continue

            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
            unique_filename = f"{uuid.uuid4()}{file_extension}"

            # Save file to disk
            file_path = os.path.join(UPLOAD_DIR, unique_filename)

            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)

            # Get description for this file
            description = descriptions_list[i] if i < len(descriptions_list) else None

            # Save file metadata to database
            file_doc = {
                "_id": _uuid(),
                "filename": file.filename,
                "unique_filename": unique_filename,
                "file_path": file_path,
                "content_type": file.content_type,
                "size": len(content),
                "description": description,
                "uploaded_by": current_user["id"],
                "uploaded_at": datetime.now(timezone.utc)
            }

            await files_db.insert_one(file_doc)
            uploaded_files.append(file_doc)

        logger.info("Multiple files uploaded", extra={
            "uploaded_count": len(uploaded_files),
            "total_attempted": len(files),
            "uploaded_by": current_user["id"]
        })

        return {
            "uploaded_files": uploaded_files,
            "total_uploaded": len(uploaded_files),
            "total_attempted": len(files),
            "message": f"Successfully uploaded {len(uploaded_files)} of {len(files)} files"
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error("Failed to upload multiple files", extra={
            "total_files": len(files),
            "error": str(e)
        })
        raise HTTPException(500, "Failed to upload files")

@router.get("/upload/limits")
async def get_upload_limits():
    """
    Get file upload limits and allowed file types.
    """
    return {
        "max_file_size": MAX_FILE_SIZE,
        "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
        "allowed_types": ALLOWED_TYPES,
        "max_files_per_upload": 10
    }