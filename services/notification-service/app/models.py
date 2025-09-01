"""
Notification Service Pydantic Models
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class NotificationType(str, Enum):
    """Notification types"""
    COURSE_UPDATE = "course_update"
    ASSIGNMENT_DUE = "assignment_due"
    GRADE_AVAILABLE = "grade_available"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    COURSE_REMINDER = "course_reminder"
    DEADLINE_WARNING = "deadline_warning"
    WELCOME_MESSAGE = "welcome_message"

class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationStatus(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

class NotificationChannel(str, Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    IN_APP = "in_app"
    SMS = "sms"
    PUSH = "push"

class NotificationBase(BaseModel):
    """Base notification model"""
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    type: NotificationType = Field(..., description="Type of notification")
    priority: NotificationPriority = Field(NotificationPriority.MEDIUM, description="Priority level")
    recipient_id: str = Field(..., description="User ID of recipient")
    sender_id: Optional[str] = Field(None, description="User ID of sender (optional)")
    course_id: Optional[str] = Field(None, description="Related course ID")
    assignment_id: Optional[str] = Field(None, description="Related assignment ID")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional notification data")

class NotificationCreate(NotificationBase):
    """Model for creating notifications"""
    channels: List[NotificationChannel] = Field(default_factory=lambda: [NotificationChannel.IN_APP], description="Delivery channels")

class NotificationUpdate(BaseModel):
    """Model for updating notifications"""
    status: Optional[NotificationStatus] = None
    read_at: Optional[datetime] = None

class Notification(NotificationBase):
    """Complete notification model"""
    id: str = Field(..., alias="_id")
    status: NotificationStatus = Field(NotificationStatus.PENDING, description="Delivery status")
    channels: List[NotificationChannel] = Field(default_factory=list, description="Delivery channels used")
    sent_at: Optional[datetime] = Field(None, description="When notification was sent")
    delivered_at: Optional[datetime] = Field(None, description="When notification was delivered")
    read_at: Optional[datetime] = Field(None, description="When notification was read")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class NotificationTemplateBase(BaseModel):
    """Base notification template model"""
    name: str = Field(..., description="Template name")
    type: NotificationType = Field(..., description="Notification type")
    subject_template: str = Field(..., description="Email subject template")
    message_template: str = Field(..., description="Message template")
    variables: List[str] = Field(default_factory=list, description="Available template variables")

class NotificationTemplate(NotificationTemplateBase):
    """Complete notification template model"""
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class NotificationSettingsBase(BaseModel):
    """Base notification settings model"""
    user_id: str = Field(..., description="User ID")
    email_enabled: bool = Field(True, description="Enable email notifications")
    in_app_enabled: bool = Field(True, description="Enable in-app notifications")
    sms_enabled: bool = Field(False, description="Enable SMS notifications")
    push_enabled: bool = Field(False, description="Enable push notifications")

    # Notification type preferences
    course_updates: bool = Field(True, description="Course update notifications")
    assignment_deadlines: bool = Field(True, description="Assignment deadline notifications")
    grade_notifications: bool = Field(True, description="Grade notifications")
    achievement_notifications: bool = Field(True, description="Achievement notifications")
    system_announcements: bool = Field(True, description="System announcement notifications")

class NotificationSettings(NotificationSettingsBase):
    """Complete notification settings model"""
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class NotificationBatch(BaseModel):
    """Model for batch notification operations"""
    notifications: List[NotificationCreate] = Field(..., description="List of notifications to send")
    priority: NotificationPriority = Field(NotificationPriority.MEDIUM, description="Batch priority")

class NotificationStats(BaseModel):
    """Notification statistics model"""
    total_sent: int = Field(0, description="Total notifications sent")
    total_delivered: int = Field(0, description="Total notifications delivered")
    total_read: int = Field(0, description="Total notifications read")
    delivery_rate: float = Field(0.0, description="Delivery rate percentage")
    read_rate: float = Field(0.0, description="Read rate percentage")
    period: str = Field(..., description="Time period for statistics")

class UserPrivate(BaseModel):
    """Private user information for internal use"""
    id: str = Field(..., alias="_id")
    email: str
    role: str = "student"
    name: str = ""

    class Config:
        allow_population_by_field_name = True