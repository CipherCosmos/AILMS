"""
Advanced data validation utilities for LMS microservices
"""
import re
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Annotated
from pydantic.v1 import validator as v1_validator
from datetime import datetime, timezone
from shared.common.errors import ValidationError


class UserCreateRequest(BaseModel):
    """User creation request with enhanced validation"""
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: Optional[str] = Field(
        default="student",
        pattern=r"^(super_admin|org_admin|dept_admin|instructor|teaching_assistant|content_author|student|auditor|parent_guardian|proctor|support_moderator|career_coach|marketplace_manager|industry_reviewer|alumni)$"
    )

    @v1_validator('email')
    def validate_email_format(cls, v):
        """Validate email format with additional checks"""
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValidationError("Invalid email format", field="email", value=v)
        return v.lower().strip()

    @v1_validator('name')
    def validate_name_format(cls, v):
        """Validate name format"""
        if not re.match(r'^[a-zA-Z\s\-]+$', v):
            raise ValidationError(
                "Name can only contain letters, spaces, and hyphens",
                field="name",
                value=v
            )
        return v.strip()

    @v1_validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValidationError("Password must be at least 8 characters", field="password")

        if not re.search(r'[A-Z]', v):
            raise ValidationError("Password must contain at least one uppercase letter", field="password")

        if not re.search(r'[a-z]', v):
            raise ValidationError("Password must contain at least one lowercase letter", field="password")

        if not re.search(r'\d', v):
            raise ValidationError("Password must contain at least one digit", field="password")

        return v


class UserUpdateRequest(BaseModel):
    """User update request with validation"""
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    role: Optional[str] = Field(
        None,
        pattern=r"^(super_admin|org_admin|dept_admin|instructor|teaching_assistant|content_author|student|auditor|parent_guardian|proctor|support_moderator|career_coach|marketplace_manager|industry_reviewer|alumni)$"
    )

    @v1_validator('email')
    def validate_email_format(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValidationError("Invalid email format", field="email", value=v)
        return v.lower().strip() if v else v

    @v1_validator('name')
    def validate_name_format(cls, v):
        if v and not re.match(r'^[a-zA-Z\s\-]+$', v):
            raise ValidationError(
                "Name can only contain letters, spaces, and hyphens",
                field="name",
                value=v
            )
        return v.strip() if v else v


class CourseCreateRequest(BaseModel):
    """Course creation request with validation"""
    title: str = Field(min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    audience: str = Field(min_length=2, max_length=50)
    difficulty: str = Field(pattern=r"^(beginner|intermediate|advanced)$")
    tags: Optional[List[str]] = Field(None, max_items=10)
    prerequisites: Optional[List[str]] = Field(None, max_items=20)

    @v1_validator('title')
    def validate_title(cls, v):
        """Validate course title"""
        if not v.strip():
            raise ValidationError("Course title cannot be empty", field="title")
        return v.strip()

    @v1_validator('audience')
    def validate_audience(cls, v):
        """Validate audience field"""
        allowed_audiences = [
            "beginners", "intermediate", "advanced", "professionals",
            "students", "developers", "managers", "executives", "general"
        ]
        if v.lower() not in allowed_audiences:
            raise ValidationError(
                f"Audience must be one of: {', '.join(allowed_audiences)}",
                field="audience",
                value=v
            )
        return v.lower()

    @v1_validator('tags')
    def validate_tags(cls, v):
        """Validate course tags"""
        if v:
            for tag in v:
                if len(tag) > 30:
                    raise ValidationError("Each tag must be 30 characters or less", field="tags")
                if not re.match(r'^[a-zA-Z0-9\s\-_]+$', tag):
                    raise ValidationError(
                        "Tags can only contain letters, numbers, spaces, hyphens, and underscores",
                        field="tags"
                    )
        return v


class LessonCreateRequest(BaseModel):
    """Lesson creation request with validation"""
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=10, max_length=50000)  # Max 50KB
    content_type: str = Field(
        default="text",
        pattern=r"^(text|video|interactive|quiz|assignment)$"
    )
    duration_minutes: int = Field(ge=1, le=480)  # 1 minute to 8 hours
    difficulty_level: str = Field(pattern=r"^(beginner|intermediate|advanced)$")
    learning_objectives: Optional[List[str]] = Field(None, max_items=10)
    prerequisites: Optional[List[str]] = Field(None, max_items=10)

    @v1_validator('content')
    def validate_content_length(cls, v):
        """Validate content length"""
        if len(v.strip()) < 10:
            raise ValidationError("Content must be at least 10 characters", field="content")
        return v.strip()

    @v1_validator('learning_objectives')
    def validate_objectives(cls, v):
        """Validate learning objectives"""
        if v:
            for objective in v:
                if len(objective) > 200:
                    raise ValidationError(
                        "Each learning objective must be 200 characters or less",
                        field="learning_objectives"
                    )
        return v


class AssignmentCreateRequest(BaseModel):
    """Assignment creation request with validation"""
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    due_date: Optional[datetime] = None
    max_score: int = Field(default=100, ge=1, le=1000)
    rubric: Optional[List[str]] = Field(None, max_items=20)

    assignment_id: str = Field(pattern=r'^[a-fA-F0-9]{24}$')  # MongoDB ObjectId format
    text_answer: Optional[str] = Field(None, max_length=10000)
    file_ids: Optional[List[str]] = Field(None, max_items=10)

    @v1_validator('due_date')
    def validate_due_date(cls, v):
        """Validate due date is in the future"""
        if v and v <= datetime.now(timezone.utc):
            raise ValidationError("Due date must be in the future", field="due_date", value=v)
        return v

    @v1_validator('rubric')
    def validate_rubric(cls, v):
        """Validate rubric criteria"""
        if v:
            for criterion in v:
                if len(criterion) > 500:
                    raise ValidationError(
                        "Each rubric criterion must be 500 characters or less",
                        field="rubric"
                    )
        return v


class SubmissionCreateRequest(BaseModel):
    """Submission creation request with validation"""
    assignment_id: str = Field(pattern=r'^[a-fA-F0-9]{24}$')  # MongoDB ObjectId format
    text_answer: Optional[str] = Field(None, max_length=10000)
    file_ids: Optional[List[str]] = Field(None, max_items=10)

    @v1_validator('file_ids')
    def validate_file_ids(cls, v):
        """Validate file IDs format"""
        if v:
            for file_id in v:
                if not re.match(r'^[a-fA-F0-9]{24}$', file_id):
                    raise ValidationError(
                        "Invalid file ID format",
                        field="file_ids",
                        value=file_id
                    )
        return v


class NotificationCreateRequest(BaseModel):
    """Notification creation request with validation"""
    user_id: str = Field(pattern=r'^[a-fA-F0-9]{24}$')
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=1000)
    type: str = Field(pattern=r"^(assignment|quiz|course|system|announcement)$")
    priority: str = Field(default="normal", pattern=r"^(low|normal|high|urgent)$")

    @v1_validator('message')
    def validate_message_content(cls, v):
        """Validate message content"""
        if not v.strip():
            raise ValidationError("Message cannot be empty", field="message")
        return v.strip()


class SearchRequest(BaseModel):
    """Search request with validation"""
    query: str = Field(min_length=1, max_length=200)
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = Field(None, pattern=r"^(relevance|date|rating|popularity)$")
    sort_order: Optional[str] = Field(None, pattern=r"^(asc|desc)$")
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @v1_validator('query')
    def validate_query(cls, v):
        """Validate search query"""
        if not v.strip():
            raise ValidationError("Search query cannot be empty", field="query")
        return v.strip()


class PaginationRequest(BaseModel):
    """Pagination request with validation"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern=r"^(asc|desc)$")


# Utility functions for validation
def validate_object_id(value: str, field_name: str = "id") -> str:
    """Validate MongoDB ObjectId format"""
    if not re.match(r'^[a-fA-F0-9]{24}$', value):
        raise ValidationError(f"Invalid {field_name} format", field=field_name, value=value)
    return value


def validate_email_domain(email: str, allowed_domains: Optional[List[str]] = None) -> str:
    """Validate email domain"""
    if allowed_domains:
        domain = email.split('@')[1]
        if domain not in allowed_domains:
            raise ValidationError(
                f"Email domain not allowed. Allowed domains: {', '.join(allowed_domains)}",
                field="email",
                value=email
            )
    return email


def validate_file_size(size: int, max_size: int = 10 * 1024 * 1024) -> int:  # 10MB default
    """Validate file size"""
    if size > max_size:
        raise ValidationError(
            f"File size exceeds maximum allowed size of {max_size} bytes",
            field="file_size",
            value=size
        )
    return size


def validate_file_type(content_type: str, allowed_types: List[str]) -> str:
    """Validate file content type"""
    if content_type not in allowed_types:
        raise ValidationError(
            f"File type not allowed. Allowed types: {', '.join(allowed_types)}",
            field="content_type",
            value=content_type
        )
    return content_type


def sanitize_html_content(content: str) -> str:
    """Sanitize HTML content to prevent XSS"""
    # Remove potentially dangerous tags and attributes
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        r'on\w+="[^"]*"',  # Remove event handlers
        r'on\w+=\'[^\']*\'',  # Remove event handlers with single quotes
    ]

    for pattern in dangerous_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

    return content