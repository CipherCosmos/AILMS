"""
AI Service Pydantic Models
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class AIRequestType(str, Enum):
    """AI request types"""
    ANALYSIS = "analysis"
    GENERATION = "generation"
    ENHANCEMENT = "enhancement"
    PERSONALIZATION = "personalization"

class AIResultType(str, Enum):
    """AI result types"""
    COURSE_CONTENT = "course_content"
    QUIZ_QUESTIONS = "quiz_questions"
    LESSON_CONTENT = "lesson_content"
    ANALYSIS_REPORT = "analysis_report"
    ENHANCED_CONTENT = "enhanced_content"
    RECOMMENDATIONS = "recommendations"

class AIModel(str, Enum):
    """Available AI models"""
    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    CLAUDE_3 = "claude-3"

class AIRequestBase(BaseModel):
    """Base AI request model"""
    request_type: AIRequestType
    input_text: str = Field(..., max_length=10000, description="Input text for AI processing")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional parameters")
    model: Optional[AIModel] = Field(AIModel.GPT_4, description="AI model to use")

class AIRequestCreate(AIRequestBase):
    """Model for creating AI request"""
    user_id: str = Field(..., description="User ID")

class AIRequest(AIRequestBase):
    """Complete AI request model"""
    id: str = Field(..., alias="_id")
    user_id: str
    status: str = Field("pending", description="Request status")
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AIResultBase(BaseModel):
    """Base AI result model"""
    result_type: AIResultType
    content: Dict[str, Any] = Field(..., description="AI generated content")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

class AIResultCreate(AIResultBase):
    """Model for creating AI result"""
    request_id: str = Field(..., description="Request ID")
    user_id: str = Field(..., description="User ID")

class AIResult(AIResultBase):
    """Complete AI result model"""
    id: str = Field(..., alias="_id")
    request_id: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserAIPreferencesBase(BaseModel):
    """Base user AI preferences model"""
    preferred_model: Optional[AIModel] = Field(AIModel.GPT_4, description="Preferred AI model")
    content_complexity: Optional[str] = Field("intermediate", description="Preferred content complexity")
    learning_style: Optional[str] = Field("balanced", description="Preferred learning style")
    enable_caching: Optional[bool] = Field(True, description="Enable result caching")
    max_tokens: Optional[int] = Field(2000, description="Maximum tokens per request")
    custom_instructions: Optional[str] = Field("", max_length=1000, description="Custom instructions")

class UserAIPreferencesCreate(UserAIPreferencesBase):
    """Model for creating user AI preferences"""
    user_id: str = Field(..., description="User ID")

class UserAIPreferences(UserAIPreferencesBase):
    """Complete user AI preferences model"""
    id: str = Field(..., alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ContentAnalysisRequest(BaseModel):
    """Content analysis request model"""
    content: str = Field(..., max_length=10000, description="Content to analyze")
    analysis_type: str = Field("comprehensive", description="Type of analysis")
    include_suggestions: Optional[bool] = Field(True, description="Include improvement suggestions")

class ContentAnalysisResult(BaseModel):
    """Content analysis result model"""
    readability_score: float
    complexity_level: str
    key_topics: List[str]
    suggestions: List[str]
    word_count: int
    estimated_reading_time: int
    quality_score: float

class ContentGenerationRequest(BaseModel):
    """Content generation request model"""
    topic: str = Field(..., max_length=200, description="Content topic")
    content_type: str = Field("lesson", description="Type of content to generate")
    target_audience: Optional[str] = Field("general", description="Target audience")
    difficulty_level: Optional[str] = Field("intermediate", description="Difficulty level")
    length_requirement: Optional[str] = Field("medium", description="Content length requirement")

class ContentGenerationResult(BaseModel):
    """Content generation result model"""
    title: str
    content: str
    metadata: Dict[str, Any]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ContentEnhancementRequest(BaseModel):
    """Content enhancement request model"""
    original_content: str = Field(..., max_length=5000, description="Original content to enhance")
    enhancement_type: str = Field("clarity", description="Type of enhancement")
    target_improvements: Optional[List[str]] = Field(default_factory=list, description="Specific improvements to target")

class ContentEnhancementResult(BaseModel):
    """Content enhancement result model"""
    enhanced_content: str
    improvements_made: List[str]
    confidence_score: float
    original_length: int
    enhanced_length: int

class PersonalizationRequest(BaseModel):
    """Personalization request model"""
    user_id: str = Field(..., description="User ID")
    content_type: str = Field("recommendations", description="Type of personalization")
    context_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Contextual data")

class PersonalizationResult(BaseModel):
    """Personalization result model"""
    recommendations: List[Dict[str, Any]]
    user_profile: Dict[str, Any]
    confidence_score: float
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PerformanceAnalysisRequest(BaseModel):
    """Performance analysis request model"""
    user_id: str = Field(..., description="User ID to analyze")
    course_id: Optional[str] = Field(None, description="Specific course to analyze")
    timeframe: Optional[str] = Field("month", description="Analysis timeframe")

class PerformanceAnalysisResponse(BaseModel):
    """Performance analysis response model"""
    analysis: str
    metrics: Dict[str, Any]
    performance_level: str
    recommendations: List[str]
    generated_at: str
    analyzed_by: str
    target_user: str

class CoursePerformanceAnalysisRequest(BaseModel):
    """Course performance analysis request model"""
    course_id: str = Field(..., description="Course to analyze")
    include_individual_students: Optional[bool] = Field(False, description="Include individual student analysis")

class CoursePerformanceAnalysisResponse(BaseModel):
    """Course performance analysis response model"""
    course_analysis: str
    course_metrics: Dict[str, Any]
    engagement_indicators: Dict[str, Any]
    generated_at: str
    analyzed_by: str
    individual_analyses: Optional[List[Dict[str, Any]]] = None

class PerformancePredictionRequest(BaseModel):
    """Performance prediction request model"""
    user_id: str = Field(..., description="User to predict performance for")
    course_id: str = Field(..., description="Course to predict performance in")

class PerformancePredictionResponse(BaseModel):
    """Performance prediction response model"""
    prediction: str
    current_metrics: Dict[str, Any]
    prediction_factors: Dict[str, Any]
    generated_at: str
    predicted_for: str
    course_id: str
    predicted_by: str

class AIUsageStats(BaseModel):
    """AI usage statistics model"""
    total_requests: int
    requests_by_type: Dict[str, int]
    total_tokens_used: int
    period_days: int
    average_cost_per_request: Optional[float] = None
    most_used_model: Optional[str] = None

class UserPrivate(BaseModel):
    """Private user information for internal use"""
    id: str = Field(..., alias="_id")
    email: str
    role: str = "student"
    name: str = ""

    class Config:
        allow_population_by_field_name = True