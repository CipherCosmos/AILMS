"""
Analytics Service Pydantic Models
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class MetricType(str, Enum):
    """Analytics metric types"""
    PERFORMANCE = "performance"
    ENGAGEMENT = "engagement"
    COMPLETION = "completion"
    TIME_SPENT = "time_spent"
    PROGRESS = "progress"

class ReportType(str, Enum):
    """Report types"""
    STUDENT_PROGRESS = "student_progress"
    COURSE_ANALYTICS = "course_analytics"
    PERFORMANCE_SUMMARY = "performance_summary"
    ENGAGEMENT_REPORT = "engagement_report"
    CUSTOM = "custom"

class TimeRange(str, Enum):
    """Time range options"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"

class CourseAnalyticsBase(BaseModel):
    """Base course analytics model"""
    enrollment_count: int = Field(0, description="Total enrolled students")
    completion_rate: float = Field(0.0, description="Course completion rate")
    average_performance: float = Field(0.0, description="Average student performance")
    total_study_hours: int = Field(0, description="Total study hours across all students")
    active_students: int = Field(0, description="Currently active students")
    dropout_rate: float = Field(0.0, description="Student dropout rate")

class CourseAnalytics(CourseAnalyticsBase):
    """Complete course analytics model"""
    id: str = Field(..., alias="_id")
    course_id: str = Field(..., description="Course ID")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class StudentAnalyticsBase(BaseModel):
    """Base student analytics model"""
    courses_enrolled: int = Field(0, description="Number of courses enrolled")
    courses_completed: int = Field(0, description="Number of courses completed")
    average_performance: float = Field(0.0, description="Average performance across courses")
    total_study_hours: int = Field(0, description="Total study hours")
    current_streak: int = Field(0, description="Current learning streak in days")
    learning_velocity: float = Field(0.0, description="Rate of progress improvement")

class StudentAnalytics(StudentAnalyticsBase):
    """Complete student analytics model"""
    id: str = Field(..., alias="_id")
    student_id: str = Field(..., description="Student ID")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PerformanceMetricBase(BaseModel):
    """Base performance metric model"""
    performance_score: float = Field(..., description="Performance score (0-100)")
    completion_percentage: float = Field(0.0, description="Course completion percentage")
    study_hours: int = Field(0, description="Study hours for this period")
    engagement_score: float = Field(0.0, description="Engagement score")
    quiz_scores: Optional[List[float]] = Field(default_factory=list, description="Quiz scores")
    assignment_scores: Optional[List[float]] = Field(default_factory=list, description="Assignment scores")

class PerformanceMetric(PerformanceMetricBase):
    """Complete performance metric model"""
    id: str = Field(..., alias="_id")
    student_id: str = Field(..., description="Student ID")
    course_id: str = Field(..., description="Course ID")
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ReportBase(BaseModel):
    """Base report model"""
    title: str = Field(..., description="Report title")
    description: Optional[str] = Field(None, description="Report description")
    data: Dict[str, Any] = Field(..., description="Report data")
    format: str = Field("json", description="Report format")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Report generation parameters")

class Report(ReportBase):
    """Complete report model"""
    id: str = Field(..., alias="_id")
    report_type: ReportType = Field(..., description="Type of report")
    created_by: str = Field(..., description="User who created the report")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class RealTimeMetricBase(BaseModel):
    """Base real-time metric model"""
    value: float = Field(..., description="Metric value")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

class RealTimeMetric(RealTimeMetricBase):
    """Complete real-time metric model"""
    id: str = Field(..., alias="_id")
    metric_type: MetricType = Field(..., description="Type of metric")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AnalyticsDashboard(BaseModel):
    """Analytics dashboard model"""
    course_analytics: List[CourseAnalytics] = Field(default_factory=list)
    student_analytics: List[StudentAnalytics] = Field(default_factory=list)
    recent_metrics: List[RealTimeMetric] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PerformanceInsights(BaseModel):
    """Performance insights model"""
    student_id: str
    insights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    trends: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class EngagementMetrics(BaseModel):
    """Engagement metrics model"""
    course_id: str
    student_id: str
    login_frequency: int = Field(0, description="Logins per week")
    session_duration: int = Field(0, description="Average session duration in minutes")
    content_interactions: int = Field(0, description="Number of content interactions")
    quiz_attempts: int = Field(0, description="Number of quiz attempts")
    forum_posts: int = Field(0, description="Number of forum posts")
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PredictiveAnalytics(BaseModel):
    """Predictive analytics model"""
    student_id: str
    course_id: str
    completion_probability: float = Field(0.0, description="Probability of course completion")
    expected_grade: float = Field(0.0, description="Expected final grade")
    risk_factors: List[str] = Field(default_factory=list, description="Risk factors for poor performance")
    interventions: List[str] = Field(default_factory=list, description="Recommended interventions")
    predicted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserPrivate(BaseModel):
    """Private user information for internal use"""
    id: str = Field(..., alias="_id")
    email: str
    role: str = "student"
    name: str = ""

    class Config:
        allow_population_by_field_name = True