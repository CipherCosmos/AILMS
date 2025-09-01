"""
File Service Pydantic Models
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class FileType(str, Enum):
    """File type categories"""
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    CODE = "code"
    OTHER = "other"

class FileStatus(str, Enum):
    """File status"""
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    DELETED = "deleted"
    QUARANTINED = "quarantined"

class StorageBackend(str, Enum):
    """Storage backend types"""
    LOCAL = "local"
    S3 = "s3"
    AZURE = "azure"
    GCS = "gcs"

class FileBase(BaseModel):
    """Base file model"""
    filename: str = Field(..., max_length=255, description="Original filename")
    file_type: FileType = Field(..., description="File type category")
    mime_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., description="File size in bytes")
    storage_path: str = Field(..., description="Storage path")
    storage_backend: StorageBackend = Field(StorageBackend.LOCAL, description="Storage backend")

class FileCreate(FileBase):
    """Model for creating file"""
    user_id: str = Field(..., description="Owner user ID")
    checksum: Optional[str] = Field(None, description="File checksum")

class FileUpdate(BaseModel):
    """Model for updating file"""
    filename: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = Field(None, description="File tags")
    description: Optional[str] = Field(None, max_length=1000)

class File(FileBase):
    """Complete file model"""
    id: str = Field(..., alias="_id")
    file_id: str = Field(..., description="Unique file identifier")
    user_id: str = Field(..., description="Owner user ID")
    status: FileStatus = Field(FileStatus.UPLOADED, description="File status")
    checksum: Optional[str] = Field(None, description="File checksum")
    tags: Optional[List[str]] = Field(default_factory=list, description="File tags")
    description: Optional[str] = Field(None, max_length=1000, description="File description")
    thumbnail_path: Optional[str] = Field(None, description="Thumbnail path")
    versions_count: int = Field(0, description="Number of versions")
    download_count: int = Field(0, description="Download count")
    last_accessed: Optional[datetime] = Field(None, description="Last access time")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FileVersionBase(BaseModel):
    """Base file version model"""
    version_number: int = Field(..., description="Version number")
    file_size: int = Field(..., description="Version file size")
    storage_path: str = Field(..., description="Version storage path")
    checksum: str = Field(..., description="Version checksum")
    changes_description: Optional[str] = Field(None, max_length=500, description="Changes description")

class FileVersion(FileVersionBase):
    """Complete file version model"""
    id: str = Field(..., alias="_id")
    file_id: str = Field(..., description="Parent file ID")
    created_by: str = Field(..., description="User who created version")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SharedLinkBase(BaseModel):
    """Base shared link model"""
    share_token: str = Field(..., description="Unique share token")
    file_id: str = Field(..., description="File ID being shared")
    permissions: List[str] = Field(default_factory=lambda: ["read"], description="Access permissions")
    password_protected: bool = Field(False, description="Whether link is password protected")
    max_downloads: Optional[int] = Field(None, description="Maximum download count")
    download_count: int = Field(0, description="Current download count")

class SharedLinkCreate(SharedLinkBase):
    """Model for creating shared link"""
    created_by: str = Field(..., description="User who created the link")
    expires_at: Optional[datetime] = Field(None, description="Link expiration time")

class SharedLink(SharedLinkBase):
    """Complete shared link model"""
    id: str = Field(..., alias="_id")
    created_by: str = Field(..., description="User who created the link")
    expires_at: Optional[datetime] = Field(None, description="Link expiration time")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: Optional[datetime] = Field(None, description="Last access time")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FileAccessLogBase(BaseModel):
    """Base file access log model"""
    access_type: str = Field(..., description="Type of access (download, view, share)")
    ip_address: Optional[str] = Field(None, description="IP address of accessor")
    user_agent: Optional[str] = Field(None, description="User agent string")

class FileAccessLog(FileAccessLogBase):
    """Complete file access log model"""
    id: str = Field(..., alias="_id")
    file_id: str = Field(..., description="File ID accessed")
    user_id: Optional[str] = Field(None, description="User who accessed (if authenticated)")
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ThumbnailBase(BaseModel):
    """Base thumbnail model"""
    size: str = Field(..., description="Thumbnail size (e.g., '100x100')")
    format: str = Field("jpeg", description="Thumbnail format")
    storage_path: str = Field(..., description="Thumbnail storage path")
    file_size: int = Field(..., description="Thumbnail file size")

class Thumbnail(ThumbnailBase):
    """Complete thumbnail model"""
    id: str = Field(..., alias="_id")
    file_id: str = Field(..., description="Parent file ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UploadRequest(BaseModel):
    """Upload request model"""
    filename: str = Field(..., max_length=255, description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="Content type")
    checksum: Optional[str] = Field(None, description="File checksum")

class UploadResponse(BaseModel):
    """Upload response model"""
    file_id: str = Field(..., description="Unique file identifier")
    upload_url: str = Field(..., description="Upload URL")
    fields: Dict[str, Any] = Field(default_factory=dict, description="Additional upload fields")

class FileStorageStats(BaseModel):
    """File storage statistics model"""
    total_files: int
    total_size: int
    file_types: List[str]
    storage_used_percentage: float
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FileUploadStats(BaseModel):
    """File upload statistics model"""
    upload_stats: List[Dict[str, Any]]
    total_uploads: int
    total_size_uploaded: int
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FileShareRequest(BaseModel):
    """File share request model"""
    file_id: str = Field(..., description="File to share")
    permissions: List[str] = Field(default_factory=lambda: ["read"], description="Share permissions")
    expires_in_days: int = Field(7, description="Link expiration in days")
    password_protected: bool = Field(False, description="Whether to password protect")
    max_downloads: Optional[int] = Field(None, description="Maximum downloads allowed")

class FileShareResponse(BaseModel):
    """File share response model"""
    share_token: str = Field(..., description="Share token")
    share_url: str = Field(..., description="Share URL")
    expires_at: datetime = Field(..., description="Expiration time")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FileDownloadRequest(BaseModel):
    """File download request model"""
    file_id: str = Field(..., description="File to download")
    share_token: Optional[str] = Field(None, description="Share token if accessing via shared link")

class FileDownloadResponse(BaseModel):
    """File download response model"""
    download_url: str = Field(..., description="Download URL")
    expires_in: int = Field(3600, description="URL expiration in seconds")

class UserPrivate(BaseModel):
    """Private user information for internal use"""
    id: str = Field(..., alias="_id")
    email: str
    role: str = "student"
    name: str = ""

    class Config:
        allow_population_by_field_name = True