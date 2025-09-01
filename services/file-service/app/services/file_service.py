"""
File Service Business Logic Layer
"""
import os
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    aiofiles = None
    AIOFILES_AVAILABLE = False

from shared.common.logging import get_logger
from shared.common.errors import ValidationError, DatabaseError, NotFoundError

from database.database import file_db
from models import (
    File, FileCreate, FileUpdate,
    FileVersion, SharedLink, SharedLinkCreate,
    FileAccessLog, Thumbnail,
    UploadRequest, UploadResponse,
    FileStorageStats, FileUploadStats,
    FileShareRequest, FileShareResponse,
    FileDownloadRequest, FileDownloadResponse,
    FileType, FileStatus, StorageBackend
)
from config.config import file_service_settings

logger = get_logger("file-service")

class FileService:
    """File service business logic"""

    def __init__(self):
        self.db = file_db

    # File operations
    async def create_file_metadata(self, file_data: FileCreate) -> File:
        """Create file metadata"""
        try:
            # Validate file data
            self._validate_file_data(file_data)

            # Generate unique file ID
            file_id = str(uuid.uuid4())

            file_dict = file_data.dict(by_alias=True)
            file_dict["file_id"] = file_id
            file_dict["status"] = FileStatus.UPLOADED
            file_dict["uploaded_at"] = datetime.now(timezone.utc)
            file_dict["updated_at"] = datetime.now(timezone.utc)

            # Save metadata
            await self.db.save_file_metadata(file_dict)

            logger.info("File metadata created", extra={
                "file_id": file_id,
                "user_id": file_data.user_id,
                "filename": file_data.filename
            })

            return File(**file_dict)

        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to create file metadata", extra={"error": str(e)})
            raise DatabaseError("create_file_metadata", f"File metadata creation failed: {str(e)}")

    async def get_file_metadata(self, file_id: str, user_id: Optional[str] = None) -> File:
        """Get file metadata"""
        try:
            file_data = await self.db.get_file_metadata(file_id)
            if not file_data:
                raise NotFoundError("File", file_id)

            # Check ownership if user_id provided
            if user_id and file_data.get("user_id") != user_id:
                raise NotFoundError("File", file_id)

            return File(**file_data)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get file metadata", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("get_file_metadata", f"File metadata retrieval failed: {str(e)}")

    async def get_user_files(self, user_id: str, limit: int = 50, file_type: Optional[FileType] = None) -> List[File]:
        """Get user's files"""
        try:
            files_data = await self.db.get_user_files(user_id, limit, file_type.value if file_type else None)
            return [File(**file_data) for file_data in files_data]

        except Exception as e:
            logger.error("Failed to get user files", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_user_files", f"User files retrieval failed: {str(e)}")

    async def update_file_metadata(self, file_id: str, user_id: str, updates: FileUpdate) -> File:
        """Update file metadata"""
        try:
            # Verify ownership
            file_data = await self.db.get_file_metadata(file_id)
            if not file_data or file_data.get("user_id") != user_id:
                raise NotFoundError("File", file_id)

            update_dict = updates.dict(exclude_unset=True)
            if not update_dict:
                raise ValidationError("No valid fields provided for update", "updates")

            success = await self.db.update_file_metadata(file_id, update_dict)
            if not success:
                raise DatabaseError("update_file_metadata", "Failed to update file metadata")

            # Get updated file
            updated_file = await self.get_file_metadata(file_id)

            logger.info("File metadata updated", extra={"file_id": file_id})

            return updated_file

        except (ValidationError, NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to update file metadata", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("update_file_metadata", f"File metadata update failed: {str(e)}")

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file"""
        try:
            # Verify ownership
            file_data = await self.db.get_file_metadata(file_id)
            if not file_data or file_data.get("user_id") != user_id:
                raise NotFoundError("File", file_id)

            # Delete physical file
            storage_path = file_data.get("storage_path")
            if storage_path and os.path.exists(storage_path):
                os.remove(storage_path)

            # Delete metadata
            success = await self.db.delete_file_metadata(file_id)

            if success:
                logger.info("File deleted", extra={"file_id": file_id})

            return success

        except (NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to delete file", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("delete_file", f"File deletion failed: {str(e)}")

    # Upload operations
    async def initiate_upload(self, upload_request: UploadRequest, user_id: str) -> UploadResponse:
        """Initiate file upload"""
        try:
            # Validate upload request
            self._validate_upload_request(upload_request)

            # Generate file ID and storage path
            file_id = str(uuid.uuid4())
            storage_path = self._generate_storage_path(file_id, upload_request.filename)

            # Create file metadata
            file_data = FileCreate(
                filename=upload_request.filename,
                file_type=self._determine_file_type(upload_request.filename),
                mime_type=upload_request.content_type,
                file_size=upload_request.file_size,
                storage_path=storage_path,
                user_id=user_id,
                checksum=upload_request.checksum
            )

            # Save metadata
            await self.create_file_metadata(file_data)

            # Generate upload URL (for local storage, return file path)
            upload_url = f"/api/files/upload/{file_id}"

            response = UploadResponse(
                file_id=file_id,
                upload_url=upload_url,
                fields={}
            )

            logger.info("Upload initiated", extra={
                "file_id": file_id,
                "user_id": user_id,
                "filename": upload_request.filename
            })

            return response

        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to initiate upload", extra={"error": str(e)})
            raise DatabaseError("initiate_upload", f"Upload initiation failed: {str(e)}")

    async def process_upload(self, file_id: str, file_content: bytes, user_id: str) -> File:
        """Process uploaded file"""
        try:
            # Get file metadata
            file_data = await self.db.get_file_metadata(file_id)
            if not file_data or file_data.get("user_id") != user_id:
                raise NotFoundError("File", file_id)

            storage_path = file_data.get("storage_path")

            # Save file to storage
            if not AIOFILES_AVAILABLE:
                raise DatabaseError("process_upload", "aiofiles package is required for file operations")

            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            async with aiofiles.open(storage_path, 'wb') as f:
                await f.write(file_content)

            # Update file status
            await self.db.update_file_metadata(file_id, {"status": FileStatus.READY.value})

            # Generate thumbnail if image
            if file_data.get("file_type") == FileType.IMAGE.value:
                await self._generate_thumbnail(file_id, storage_path)

            # Log access
            await self.db.log_file_access({
                "file_id": file_id,
                "user_id": user_id,
                "access_type": "upload"
            })

            updated_file = await self.get_file_metadata(file_id)

            logger.info("Upload processed", extra={"file_id": file_id})

            return updated_file

        except (NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to process upload", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("process_upload", f"Upload processing failed: {str(e)}")

    # Download operations
    async def get_download_url(self, download_request: FileDownloadRequest, user_id: Optional[str] = None) -> FileDownloadResponse:
        """Get file download URL"""
        try:
            file_id = download_request.file_id

            # Get file metadata
            file_data = await self.db.get_file_metadata(file_id)
            if not file_data:
                raise NotFoundError("File", file_id)

            # Check access permissions
            if not await self._check_file_access(file_data, user_id, download_request.share_token):
                raise NotFoundError("File", file_id)

            # Log access
            await self.db.log_file_access({
                "file_id": file_id,
                "user_id": user_id,
                "access_type": "download"
            })

            # Generate download URL
            download_url = f"/api/files/download/{file_id}"

            response = FileDownloadResponse(
                download_url=download_url,
                expires_in=3600  # 1 hour
            )

            logger.info("Download URL generated", extra={"file_id": file_id})

            return response

        except (NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to get download URL", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("get_download_url", f"Download URL generation failed: {str(e)}")

    async def get_file_content(self, file_id: str, user_id: Optional[str] = None, share_token: Optional[str] = None) -> bytes:
        """Get file content"""
        try:
            # Get file metadata
            file_data = await self.db.get_file_metadata(file_id)
            if not file_data:
                raise NotFoundError("File", file_id)

            # Check access permissions
            if not await self._check_file_access(file_data, user_id, share_token):
                raise NotFoundError("File", file_id)

            storage_path = file_data.get("storage_path")
            if not storage_path or not os.path.exists(storage_path):
                raise NotFoundError("File", file_id)

            # Read file content
            if not AIOFILES_AVAILABLE:
                raise DatabaseError("get_file_content", "aiofiles package is required for file operations")

            async with aiofiles.open(storage_path, 'rb') as f:
                content = await f.read()

            # Log access
            await self.db.log_file_access({
                "file_id": file_id,
                "user_id": user_id,
                "access_type": "download"
            })

            return content

        except (NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to get file content", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("get_file_content", f"File content retrieval failed: {str(e)}")

    # Sharing operations
    async def create_shared_link(self, share_request: FileShareRequest, user_id: str) -> FileShareResponse:
        """Create shared link for file"""
        try:
            file_id = share_request.file_id

            # Verify ownership
            file_data = await self.db.get_file_metadata(file_id)
            if not file_data or file_data.get("user_id") != user_id:
                raise NotFoundError("File", file_id)

            # Generate share token
            share_token = str(uuid.uuid4())

            expires_at = datetime.now(timezone.utc) + timedelta(days=share_request.expires_in_days)

            link_data = {
                "share_token": share_token,
                "file_id": file_id,
                "permissions": share_request.permissions,
                "password_protected": share_request.password_protected,
                "max_downloads": share_request.max_downloads,
                "download_count": 0,
                "created_by": user_id,
                "expires_at": expires_at
            }

            await self.db.create_shared_link(link_data)

            share_url = f"/api/files/shared/{share_token}"

            response = FileShareResponse(
                share_token=share_token,
                share_url=share_url,
                expires_at=expires_at
            )

            logger.info("Shared link created", extra={
                "file_id": file_id,
                "share_token": share_token
            })

            return response

        except (NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to create shared link", extra={
                "file_id": share_request.file_id,
                "error": str(e)
            })
            raise DatabaseError("create_shared_link", f"Shared link creation failed: {str(e)}")

    async def get_shared_file(self, share_token: str) -> File:
        """Get file from shared link"""
        try:
            link_data = await self.db.get_shared_link(share_token)
            if not link_data:
                raise NotFoundError("Shared link", share_token)

            file_id = link_data.get("file_id")
            file_data = await self.db.get_file_metadata(file_id)
            if not file_data:
                raise NotFoundError("File", file_id)

            return File(**file_data)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get shared file", extra={
                "share_token": share_token,
                "error": str(e)
            })
            raise DatabaseError("get_shared_file", f"Shared file retrieval failed: {str(e)}")

    # Analytics operations
    async def get_storage_stats(self, user_id: Optional[str] = None) -> FileStorageStats:
        """Get storage statistics"""
        try:
            stats_data = await self.db.get_storage_stats(user_id)

            # Calculate storage percentage
            total_size = stats_data.get("total_size", 0)
            max_storage = file_service_settings.max_total_storage_mb * 1024 * 1024
            storage_percentage = (total_size / max_storage) * 100 if max_storage > 0 else 0

            stats_data["storage_used_percentage"] = round(storage_percentage, 2)
            stats_data["generated_at"] = datetime.now(timezone.utc)

            return FileStorageStats(**stats_data)

        except Exception as e:
            logger.error("Failed to get storage stats", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_storage_stats", f"Storage stats retrieval failed: {str(e)}")

    async def get_upload_stats(self, days: int = 30) -> FileUploadStats:
        """Get upload statistics"""
        try:
            stats_data = await self.db.get_upload_stats(days)
            stats_data["generated_at"] = datetime.now(timezone.utc)

            return FileUploadStats(**stats_data)

        except Exception as e:
            logger.error("Failed to get upload stats", extra={
                "days": days,
                "error": str(e)
            })
            raise DatabaseError("get_upload_stats", f"Upload stats retrieval failed: {str(e)}")

    # Helper methods
    def _validate_file_data(self, file_data: FileCreate) -> None:
        """Validate file data"""
        # Check file size
        if file_data.file_size > file_service_settings.max_file_size_mb * 1024 * 1024:
            raise ValidationError("File size exceeds maximum allowed size", "file_size")

        # Check file extension
        filename = file_data.filename.lower()
        if not any(filename.endswith(ext) for ext in file_service_settings.allowed_extensions):
            raise ValidationError("File type not allowed", "filename")

        # Check MIME type
        if file_data.mime_type not in file_service_settings.allowed_mime_types:
            raise ValidationError("MIME type not allowed", "mime_type")

    def _validate_upload_request(self, upload_request: UploadRequest) -> None:
        """Validate upload request"""
        # Check file size
        if upload_request.file_size > file_service_settings.max_file_size_mb * 1024 * 1024:
            raise ValidationError("File size exceeds maximum allowed size", "file_size")

        # Check filename length
        if len(upload_request.filename) > file_service_settings.max_filename_length:
            raise ValidationError("Filename too long", "filename")

    def _determine_file_type(self, filename: str) -> FileType:
        """Determine file type from filename"""
        ext = filename.lower().split('.')[-1]

        if ext in ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt']:
            return FileType.DOCUMENT
        elif ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'svg']:
            return FileType.IMAGE
        elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv']:
            return FileType.VIDEO
        elif ext in ['mp3', 'wav', 'flac', 'aac', 'ogg', 'wma']:
            return FileType.AUDIO
        elif ext in ['zip', 'rar', '7z', 'tar', 'gz']:
            return FileType.ARCHIVE
        elif ext in ['py', 'js', 'html', 'css', 'json', 'xml', 'yaml', 'yml']:
            return FileType.CODE
        else:
            return FileType.OTHER

    def _generate_storage_path(self, file_id: str, filename: str) -> str:
        """Generate storage path for file"""
        # Create directory structure based on file ID
        dir1 = file_id[:2]
        dir2 = file_id[2:4]

        base_path = os.path.join(file_service_settings.upload_directory, dir1, dir2)
        os.makedirs(base_path, exist_ok=True)

        return os.path.join(base_path, file_id)

    async def _check_file_access(self, file_data: Dict[str, Any], user_id: Optional[str],
                               share_token: Optional[str] = None) -> bool:
        """Check if user has access to file"""
        # Owner always has access
        if user_id and file_data.get("user_id") == user_id:
            return True

        # Check shared link access
        if share_token:
            link_data = await self.db.get_shared_link(share_token)
            if link_data and link_data.get("file_id") == file_data.get("file_id"):
                # Check expiration
                expires_at = link_data.get("expires_at")
                if expires_at and isinstance(expires_at, datetime) and expires_at > datetime.now(timezone.utc):
                    # Check download limit
                    max_downloads = link_data.get("max_downloads")
                    download_count = link_data.get("download_count", 0)
                    if max_downloads is None or download_count < max_downloads:
                        return True

        return False

    async def _generate_thumbnail(self, file_id: str, file_path: str) -> None:
        """Generate thumbnail for image file"""
        try:
            # This would integrate with image processing library
            # For now, just log the attempt
            logger.info("Thumbnail generation attempted", extra={"file_id": file_id})

        except Exception as e:
            logger.warning("Failed to generate thumbnail", extra={
                "file_id": file_id,
                "error": str(e)
            })

# Global service instance
file_service = FileService()