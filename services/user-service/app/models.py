"""
User Service Pydantic Models
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
# from shared.common.models import BaseUserModel  # Not available, define locally

class UserProfileBase(BaseModel):
    """Base user profile model"""
    bio: Optional[str] = ""
    avatar_url: Optional[str] = ""
    location: Optional[str] = ""
    website: Optional[str] = ""
    social_links: Optional[Dict[str, str]] = {}
    skills: Optional[List[str]] = []
    interests: Optional[List[str]] = []
    learning_goals: Optional[List[str]] = []
    preferred_learning_style: Optional[str] = "visual"
    timezone: Optional[str] = "UTC"
    language: Optional[str] = "en"
    notifications_enabled: Optional[bool] = True
    privacy_settings: Optional[Dict[str, Any]] = {
        "show_profile": True,
        "show_progress": True,
        "show_achievements": True,
        "allow_messages": True
    }

class UserProfileCreate(UserProfileBase):
    """Model for creating user profile"""
    user_id: str = Field(..., description="User ID")

class UserProfileUpdate(UserProfileBase):
    """Model for updating user profile"""
    pass

class UserProfile(UserProfileBase):
    """Complete user profile model"""
    id: str = Field(..., alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CareerProfileBase(BaseModel):
    """Base career profile model"""
    career_goals: Optional[List[str]] = []
    target_industries: Optional[List[str]] = []
    target_roles: Optional[List[str]] = []
    skills_to_develop: Optional[List[str]] = []
    resume_data: Optional[Dict[str, Any]] = {}
    linkedin_profile: Optional[str] = ""
    portfolio_url: Optional[str] = ""
    mentor_ids: Optional[List[str]] = []
    mentee_ids: Optional[List[str]] = []

class CareerProfileCreate(CareerProfileBase):
    """Model for creating career profile"""
    user_id: str = Field(..., description="User ID")

class CareerProfileUpdate(CareerProfileBase):
    """Model for updating career profile"""
    pass

class CareerProfile(CareerProfileBase):
    """Complete career profile model"""
    id: str = Field(..., alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class StudyPlanBase(BaseModel):
    """Base study plan model"""
    weekly_hours: Optional[int] = 15
    daily_sessions: Optional[int] = 2
    focus_areas: Optional[List[Dict[str, Any]]] = []
    today_schedule: Optional[List[Dict[str, Any]]] = []
    stats: Optional[Dict[str, Any]] = {}

class StudyPlanCreate(StudyPlanBase):
    """Model for creating study plan"""
    user_id: str = Field(..., description="User ID")

class StudyPlanUpdate(StudyPlanBase):
    """Model for updating study plan"""
    pass

class StudyPlan(StudyPlanBase):
    """Complete study plan model"""
    id: str = Field(..., alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AchievementBase(BaseModel):
    """Base achievement model"""
    title: str = Field(..., description="Achievement title")
    description: str = Field(..., description="Achievement description")
    icon: Optional[str] = "🏆"
    category: Optional[str] = "general"
    points: Optional[int] = 0

class AchievementCreate(AchievementBase):
    """Model for creating achievement"""
    user_id: str = Field(..., description="User ID")

class Achievement(AchievementBase):
    """Complete achievement model"""
    id: str = Field(..., alias="_id")
    user_id: str
    earned_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class StudySessionBase(BaseModel):
    """Base study session model"""
    duration_minutes: Optional[int] = 0
    productivity_score: Optional[int] = 7
    session_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StudySessionCreate(StudySessionBase):
    """Model for creating study session"""
    user_id: str = Field(..., description="User ID")

class StudySession(StudySessionBase):
    """Complete study session model"""
    id: str = Field(..., alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class LearningAnalytics(BaseModel):
    """Learning analytics model"""
    timeframe: str
    total_sessions: int
    total_study_hours: float
    average_productivity: float
    daily_average: float
    most_productive_hour: int
    consistency_score: int
    daily_stats: List[Dict[str, Any]]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SkillGap(BaseModel):
    """Skill gap analysis model"""
    skill: str
    current_level: int
    target_level: int
    gap_description: str

class CareerReadiness(BaseModel):
    """Career readiness assessment model"""
    overall_score: int
    assessment: str
    skills_match: int
    experience_level: int
    industry_fit: int
    recommended_careers: List[Dict[str, Any]]
    skills_to_develop: List[Dict[str, Any]]

class UserPrivate(BaseModel):
    """Private user information for internal use"""
    id: str = Field(..., alias="_id")
    email: EmailStr
    role: str = "student"
    name: str = ""

    class Config:
        allow_population_by_field_name = True

class UserUpdate(BaseModel):
    """Model for updating user information"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None