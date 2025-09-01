"""
File Service Utility Functions
"""
import os
import hashlib
import mimetypes
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from shared.common.logging import get_logger
from config.config import file_service_settings

logger = get_logger("file-service-utils")

def calculate_file_checksum(file_path: str, algorithm: str = "sha256") -> str:
    """Calculate file checksum"""
    try:
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    except Exception as e:
        logger.error("Failed to calculate file checksum", extra={
            "file_path": file_path,
            "error": str(e)
        })
        return ""

def get_file_mime_type(filename: str) -> str:
    """Get MIME type from filename"""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"

def validate_file_extension(filename: str) -> bool:
    """Validate file extension against allowed extensions"""
    if not filename:
        return False

    ext = filename.lower().split('.')[-1]
    return f".{ext}" in file_service_settings.allowed_extensions

def validate_file_size(file_size: int) -> bool:
    """Validate file size against limits"""
    max_size = file_service_settings.max_file_size_mb * 1024 * 1024
    return file_size <= max_size

def validate_mime_type(mime_type: str) -> bool:
    """Validate MIME type against allowed types"""
    return mime_type in file_service_settings.allowed_mime_types

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent security issues"""
    # Remove path separators
    filename = os.path.basename(filename)

    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')

    # Limit length
    if len(filename) > file_service_settings.max_filename_length:
        name, ext = os.path.splitext(filename)
        max_name_length = file_service_settings.max_filename_length - len(ext)
        filename = name[:max_name_length] + ext

    return filename

def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename to prevent conflicts"""
    import uuid
    name, ext = os.path.splitext(original_filename)
    unique_id = str(uuid.uuid4())[:8]
    return f"{name}_{unique_id}{ext}"

def get_file_category(filename: str) -> str:
    """Get file category based on extension"""
    ext = filename.lower().split('.')[-1]

    categories = {
        # Documents
        ('pdf', 'doc', 'docx', 'txt', 'rtf', 'odt'): 'document',
        # Spreadsheets
        ('xls', 'xlsx', 'csv', 'ods'): 'spreadsheet',
        # Presentations
        ('ppt', 'pptx', 'odp'): 'presentation',
        # Images
        ('jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'svg'): 'image',
        # Videos
        ('mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'): 'video',
        # Audio
        ('mp3', 'wav', 'flac', 'aac', 'ogg', 'wma'): 'audio',
        # Archives
        ('zip', 'rar', '7z', 'tar', 'gz'): 'archive',
        # Code
        ('py', 'js', 'html', 'css', 'json', 'xml', 'yaml', 'yml'): 'code'
    }

    for extensions, category in categories.items():
        if ext in extensions:
            return category

    return 'other'

def format_file_size(bytes_size: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return ".1f"
        bytes_size /= 1024.0
    return ".1f"

def calculate_storage_usage(user_id: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate storage usage for user"""
    total_size = sum(file.get('file_size', 0) for file in files)
    file_count = len(files)

    # Group by file type
    type_usage = {}
    for file in files:
        file_type = file.get('file_type', 'unknown')
        if file_type not in type_usage:
            type_usage[file_type] = {'count': 0, 'size': 0}
        type_usage[file_type]['count'] += 1
        type_usage[file_type]['size'] += file.get('file_size', 0)

    return {
        'user_id': user_id,
        'total_files': file_count,
        'total_size': total_size,
        'total_size_formatted': format_file_size(total_size),
        'type_breakdown': type_usage,
        'last_updated': datetime.now(timezone.utc)
    }

def check_storage_quota(user_id: str, current_usage: int) -> Dict[str, Any]:
    """Check if user is within storage quota"""
    max_storage = file_service_settings.max_total_storage_mb * 1024 * 1024
    usage_percentage = (current_usage / max_storage) * 100 if max_storage > 0 else 0

    return {
        'user_id': user_id,
        'current_usage': current_usage,
        'max_storage': max_storage,
        'usage_percentage': round(usage_percentage, 2),
        'within_quota': current_usage <= max_storage,
        'remaining_storage': max(0, max_storage - current_usage)
    }

def generate_file_preview(file_path: str, file_type: str) -> Optional[str]:
    """Generate file preview (text excerpt or image thumbnail path)"""
    try:
        if file_type == 'text' or file_path.endswith(('.txt', '.md', '.py', '.js', '.html', '.css')):
            # Generate text preview
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(500)  # First 500 characters
                return content[:200] + '...' if len(content) > 200 else content

        elif file_type == 'image':
            # For images, return thumbnail path (would be generated separately)
            return f"{file_path}.thumb.jpg"

        return None

    except Exception as e:
        logger.error("Failed to generate file preview", extra={
            "file_path": file_path,
            "error": str(e)
        })
        return None

def detect_file_encoding(file_path: str) -> str:
    """Detect file encoding"""
    try:
        import chardet
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB
            result = chardet.detect(raw_data)
            return result.get('encoding', 'utf-8')
    except ImportError:
        # Fallback if chardet is not available
        return 'utf-8'
    except Exception as e:
        logger.error("Failed to detect file encoding", extra={
            "file_path": file_path,
            "error": str(e)
        })
        return 'utf-8'

def extract_file_metadata(file_path: str) -> Dict[str, Any]:
    """Extract detailed metadata from file"""
    metadata = {
        'file_path': file_path,
        'exists': os.path.exists(file_path),
        'size': 0,
        'modified_time': None,
        'created_time': None,
        'encoding': None
    }

    if metadata['exists']:
        stat = os.stat(file_path)
        metadata.update({
            'size': stat.st_size,
            'modified_time': datetime.fromtimestamp(stat.st_mtime, timezone.utc),
            'created_time': datetime.fromtimestamp(stat.st_ctime, timezone.utc),
            'encoding': detect_file_encoding(file_path)
        })

    return metadata

def validate_file_integrity(file_path: str, expected_checksum: str) -> bool:
    """Validate file integrity using checksum"""
    if not expected_checksum:
        return True

    actual_checksum = calculate_file_checksum(file_path)
    return actual_checksum == expected_checksum

def generate_share_token() -> str:
    """Generate secure share token"""
    import secrets
    return secrets.token_urlsafe(32)

def validate_share_token(token: str) -> bool:
    """Validate share token format"""
    import re
    # URL-safe base64 pattern
    pattern = r'^[A-Za-z0-9_-]+$'
    return bool(re.match(pattern, token)) and len(token) >= 32

def calculate_download_stats(files: List[Dict[str, Any]], days: int = 30) -> Dict[str, Any]:
    """Calculate download statistics"""
    from datetime import timedelta

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    total_downloads = 0
    recent_downloads = 0
    file_downloads = {}

    for file in files:
        download_count = file.get('download_count', 0)
        total_downloads += download_count

        last_accessed = file.get('last_accessed')
        if last_accessed and last_accessed > cutoff_date:
            recent_downloads += download_count

        file_type = file.get('file_type', 'unknown')
        if file_type not in file_downloads:
            file_downloads[file_type] = 0
        file_downloads[file_type] += download_count

    return {
        'total_downloads': total_downloads,
        'recent_downloads': recent_downloads,
        'downloads_by_type': file_downloads,
        'period_days': days,
        'generated_at': datetime.now(timezone.utc)
    }

def cleanup_temp_files(temp_dir: str, max_age_hours: int = 24) -> int:
    """Clean up temporary files older than specified hours"""
    import glob
    from datetime import timedelta

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    deleted_count = 0

    try:
        # Find all files in temp directory
        for file_path in glob.glob(os.path.join(temp_dir, '**'), recursive=True):
            if os.path.isfile(file_path):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path), timezone.utc)
                if file_mtime < cutoff_time:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except OSError as e:
                        logger.warning("Failed to delete temp file", extra={
                            "file_path": file_path,
                            "error": str(e)
                        })

    except Exception as e:
        logger.error("Failed to cleanup temp files", extra={
            "temp_dir": temp_dir,
            "error": str(e)
        })

    return deleted_count

def optimize_storage_layout(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze and suggest storage optimization"""
    total_size = sum(f.get('file_size', 0) for f in files)
    large_files = [f for f in files if f.get('file_size', 0) > 100 * 1024 * 1024]  # > 100MB
    old_files = [f for f in files if f.get('uploaded_at') and
                (datetime.now(timezone.utc) - f['uploaded_at']).days > 365]

    return {
        'total_files': len(files),
        'total_size': total_size,
        'large_files_count': len(large_files),
        'old_files_count': len(old_files),
        'optimization_suggestions': [
            f"Consider archiving {len(old_files)} files older than 1 year" if old_files else None,
            f"Review {len(large_files)} large files for compression" if large_files else None
        ],
        'generated_at': datetime.now(timezone.utc)
    }

async def get_current_user(token: Optional[str] = None):
    """Get current authenticated user from JWT token"""
    if not token:
        from fastapi import HTTPException
        raise HTTPException(401, "No authentication token provided")

    try:
        import jwt
        from shared.config.config import settings

        # Decode and validate JWT token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        # Verify token hasn't expired
        if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            from fastapi import HTTPException
            raise HTTPException(401, "Token has expired")

        # Get user from database (simplified for now)
        # In production, this would query the auth service or user database
        user = {
            "id": payload.get("sub"),
            "role": payload.get("role", "student"),
            "email": payload.get("email", ""),
            "name": payload.get("name", "")
        }

        if not user["id"]:
            from fastapi import HTTPException
            raise HTTPException(401, "Invalid token: missing user ID")

        return user

    except jwt.ExpiredSignatureError:
        from fastapi import HTTPException
        raise HTTPException(401, "Token has expired")
    except jwt.InvalidTokenError:
        from fastapi import HTTPException
        raise HTTPException(401, "Invalid token")
    except Exception as e:
        logger.error("Authentication failed", extra={"error": str(e)})
        from fastapi import HTTPException
        raise HTTPException(401, f"Authentication failed: {str(e)}")

def require_role(user, allowed: list[str]):
    """Check if user has required role"""
    if user.get("role") not in allowed:
        from fastapi import HTTPException
        raise HTTPException(403, "Insufficient permissions")