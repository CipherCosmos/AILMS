"""
Assessment Service Pydantic Models
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class AssignmentStatus(str, Enum):
    """Assignment status"""
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"

class SubmissionStatus(str, Enum):
    """Submission status"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    LATE = "late"
    GRADED = "graded"

class GradeType(str, Enum):
    """Grade type"""
    NUMERIC = "numeric"
    LETTER = "letter"
    PASS_FAIL = "pass_fail"
    COMPLETE_INCOMPLETE = "complete_incomplete"

class AssignmentBase(BaseModel):
    """Base assignment model"""
    title: str = Field(..., max_length=200, description="Assignment title")
    description: str = Field(..., max_length=2000, description="Assignment description")
    course_id: str = Field(..., description="Course ID")
    instructor_id: str = Field(..., description="Instructor ID")
    due_date: datetime = Field(..., description="Assignment due date")
    max_points: int = Field(100, ge=0, description="Maximum points")
    instructions: Optional[str] = Field(None, max_length=5000, description="Assignment instructions")
    attachments: Optional[List[str]] = Field(default_factory=list, description="File attachments")
    rubric_id: Optional[str] = None
    allow_late_submissions: Optional[bool] = Field(True, description="Allow late submissions")
    late_penalty_percent: Optional[int] = Field(10, ge=0, le=100, description="Late submission penalty")

class AssignmentCreate(AssignmentBase):
    """Model for creating assignment"""
    pass

class AssignmentUpdate(BaseModel):
    """Model for updating assignment"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    due_date: Optional[datetime] = None
    max_points: Optional[int] = Field(None, ge=0)
    instructions: Optional[str] = Field(None, max_length=5000)
    attachments: Optional[List[str]] = None
    rubric_id: Optional[str] = None
    allow_late_submissions: Optional[bool] = None
    late_penalty_percent: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[AssignmentStatus] = None

class Assignment(AssignmentBase):
    """Complete assignment model"""
    id: str = Field(..., alias="_id")
    status: AssignmentStatus = Field(AssignmentStatus.DRAFT, description="Assignment status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SubmissionBase(BaseModel):
    """Base submission model"""
    assignment_id: str = Field(..., description="Assignment ID")
    student_id: str = Field(..., description="Student ID")
    content: str = Field(..., max_length=10000, description="Submission content")
    attachments: Optional[List[str]] = Field(default_factory=list, description="File attachments")
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SubmissionCreate(SubmissionBase):
    """Model for creating submission"""
    pass

class SubmissionUpdate(BaseModel):
    """Model for updating submission"""
    content: Optional[str] = Field(None, max_length=10000)
    attachments: Optional[List[str]] = None

class Submission(SubmissionBase):
    """Complete submission model"""
    id: str = Field(..., alias="_id")
    status: SubmissionStatus = Field(SubmissionStatus.SUBMITTED, description="Submission status")
    is_late: bool = Field(False, description="Whether submission is late")
    grade_id: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class GradeBase(BaseModel):
    """Base grade model"""
    submission_id: str = Field(..., description="Submission ID")
    assignment_id: str = Field(..., description="Assignment ID")
    student_id: str = Field(..., description="Student ID")
    score: float = Field(..., ge=0, description="Numeric score")
    max_score: int = Field(100, ge=0, description="Maximum possible score")
    grade_type: GradeType = Field(GradeType.NUMERIC, description="Grade type")
    feedback: Optional[str] = Field(None, max_length=2000, description="Instructor feedback")
    rubric_scores: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Rubric-based scores")
    graded_by: str = Field(..., description="Instructor who graded")
    graded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GradeCreate(GradeBase):
    """Model for creating grade"""
    pass

class GradeUpdate(BaseModel):
    """Model for updating grade"""
    score: Optional[float] = Field(None, ge=0)
    feedback: Optional[str] = Field(None, max_length=2000)
    rubric_scores: Optional[Dict[str, Any]] = None

class Grade(GradeBase):
    """Complete grade model"""
    id: str = Field(..., alias="_id")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class RubricBase(BaseModel):
    """Base rubric model"""
    assignment_id: str = Field(..., description="Assignment ID")
    criteria: List[Dict[str, Any]] = Field(..., description="Rubric criteria")
    created_by: str = Field(..., description="Instructor who created rubric")

class RubricCreate(RubricBase):
    """Model for creating rubric"""
    pass

class Rubric(RubricBase):
    """Complete rubric model"""
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AssignmentStats(BaseModel):
    """Assignment statistics model"""
    assignment_id: str
    total_submissions: int
    graded_submissions: int
    average_grade: float
    grading_progress: float

class StudentPerformance(BaseModel):
    """Student performance model"""
    student_id: str
    total_assignments: int
    average_score: float
    performance_level: str

class UserPrivate(BaseModel):
    """Private user information for internal use"""
    id: str = Field(..., alias="_id")
    email: str
    role: str = "student"
    name: str = ""

    class Config:
        allow_population_by_field_name = True