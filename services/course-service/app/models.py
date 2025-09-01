"""
Course Service Pydantic Models
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
# from shared.common.models import BaseUserModel  # Not available, define locally

class CourseBase(BaseModel):
    """Base course model"""
    title: str = Field(..., max_length=200, description="Course title")
    description: Optional[str] = Field(None, max_length=2000, description="Course description")
    audience: str = Field("General", description="Target audience")
    difficulty: str = Field("beginner", description="Difficulty level")
    topic: Optional[str] = Field(None, description="Course topic (legacy)")
    published: bool = Field(False, description="Whether course is published")
    lessons: List[Dict[str, Any]] = Field(default_factory=list, description="Course lessons")
    quiz: List[Dict[str, Any]] = Field(default_factory=list, description="Course quiz questions")

class CourseCreate(CourseBase):
    """Model for creating a course"""
    pass

class CourseUpdate(BaseModel):
    """Model for updating a course"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    audience: Optional[str] = None
    difficulty: Optional[str] = None
    published: Optional[bool] = None
    lessons: Optional[List[Dict[str, Any]]] = None
    quiz: Optional[List[Dict[str, Any]]] = None

class Course(CourseBase):
    """Complete course model"""
    id: str = Field(..., alias="_id")
    owner_id: str = Field(..., description="Course owner ID")
    enrolled_user_ids: List[str] = Field(default_factory=list, description="Enrolled user IDs")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class LessonBase(BaseModel):
    """Base lesson model"""
    title: str = Field(..., max_length=150, description="Lesson title")
    content: str = Field(..., max_length=50000, description="Lesson content")
    order: int = Field(..., ge=0, description="Lesson order in course")
    duration_minutes: Optional[int] = Field(None, ge=0, description="Estimated duration in minutes")
    resources: List[Dict[str, Any]] = Field(default_factory=list, description="Lesson resources")

class LessonCreate(LessonBase):
    """Model for creating a lesson"""
    course_id: str = Field(..., description="Course ID")

class LessonUpdate(BaseModel):
    """Model for updating a lesson"""
    title: Optional[str] = Field(None, max_length=150)
    content: Optional[str] = Field(None, max_length=50000)
    order: Optional[int] = Field(None, ge=0)
    duration_minutes: Optional[int] = Field(None, ge=0)
    resources: Optional[List[Dict[str, Any]]] = None

class Lesson(LessonBase):
    """Complete lesson model"""
    id: str = Field(..., alias="_id")
    course_id: str = Field(..., description="Course ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CourseProgressBase(BaseModel):
    """Base course progress model"""
    overall_progress: float = Field(0.0, ge=0.0, le=100.0, description="Overall progress percentage")
    completed: bool = Field(False, description="Whether course is completed")
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lesson_progress: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Progress per lesson")

class CourseProgressCreate(CourseProgressBase):
    """Model for creating course progress"""
    user_id: str = Field(..., description="User ID")
    course_id: str = Field(..., description="Course ID")

class CourseProgressUpdate(BaseModel):
    """Model for updating course progress"""
    overall_progress: Optional[float] = Field(None, ge=0.0, le=100.0)
    completed: Optional[bool] = None
    last_accessed: Optional[datetime] = None
    lesson_progress: Optional[Dict[str, Dict[str, Any]]] = None

class CourseProgress(CourseProgressBase):
    """Complete course progress model"""
    id: str = Field(..., alias="_id")
    user_id: str = Field(..., description="User ID")
    course_id: str = Field(..., description="Course ID")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CourseStats(BaseModel):
    """Course statistics model"""
    total_courses: int
    published_courses: int
    draft_courses: int
    total_enrollments: int
    average_enrollment_per_course: float

class EnrollmentRequest(BaseModel):
    """Enrollment request model"""
    course_id: str = Field(..., description="Course ID to enroll in")

class EnrollmentResponse(BaseModel):
    """Enrollment response model"""
    status: str
    message: str
    enrolled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CourseListRequest(BaseModel):
    """Course list request model"""
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    published_only: bool = False
    audience: Optional[str] = None
    difficulty: Optional[str] = None
    search: Optional[str] = None

class CourseListResponse(BaseModel):
    """Course list response model"""
    courses: List[Course]
    total: int
    limit: int
    offset: int

class UserPrivate(BaseModel):
    """Private user information for internal use"""
    id: str = Field(..., alias="_id")
    email: EmailStr
    role: str = "student"
    name: str = ""

    class Config:
        allow_population_by_field_name = True