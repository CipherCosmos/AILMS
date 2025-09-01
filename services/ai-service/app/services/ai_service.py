"""
AI Service Business Logic Layer
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from shared.common.logging import get_logger
from shared.common.errors import ValidationError, DatabaseError, ServiceUnavailableError

from database.database import ai_db
from models import (
    AIRequest, AIRequestCreate,
    AIResult, AIResultCreate,
    UserAIPreferences, UserAIPreferencesCreate,
    ContentAnalysisRequest, ContentAnalysisResult,
    ContentGenerationRequest, ContentGenerationResult,
    ContentEnhancementRequest, ContentEnhancementResult,
    PersonalizationRequest, PersonalizationResult,
    AIUsageStats,
    PerformanceAnalysisRequest, PerformanceAnalysisResponse,
    CoursePerformanceAnalysisRequest, CoursePerformanceAnalysisResponse,
    PerformancePredictionRequest, PerformancePredictionResponse
)
from config.config import ai_service_settings

logger = get_logger("ai-service")

class AIService:
    """AI service business logic"""

    def __init__(self):
        self.db = ai_db

    # Core AI operations
    async def process_ai_request(self, request_data: AIRequestCreate) -> AIResult:
        """Process AI request and return result"""
        try:
            # Validate request
            self._validate_request(request_data)

            # Check rate limits
            await self._check_rate_limits(request_data.user_id, request_data.request_type.value)

            # Log request
            request_id = await self.db.log_ai_request({
                "user_id": request_data.user_id,
                "request_type": request_data.request_type.value,
                "input_text": request_data.input_text,
                "parameters": request_data.parameters,
                "model": request_data.model.value if request_data.model else ai_service_settings.default_model
            })

            # Process based on request type
            result = await self._process_request_type(request_data, request_id)

            # Save result
            result_id = await self.db.save_ai_result({
                "request_id": request_id,
                "user_id": request_data.user_id,
                "result_type": result.result_type.value,
                "content": result.content,
                "confidence_score": result.confidence_score,
                "metadata": result.metadata
            })

            logger.info("AI request processed", extra={
                "request_id": request_id,
                "user_id": request_data.user_id,
                "request_type": request_data.request_type.value,
                "result_id": result_id
            })

            return result

        except (ValidationError, DatabaseError, ServiceUnavailableError):
            raise
        except Exception as e:
            logger.error("Failed to process AI request", extra={
                "user_id": request_data.user_id,
                "request_type": request_data.request_type.value,
                "error": str(e)
            })
            raise ServiceUnavailableError("ai-service", f"AI processing failed: {str(e)}")

    async def _process_request_type(self, request_data: AIRequestCreate, request_id: str) -> AIResult:
        """Process request based on type"""
        if request_data.request_type.value == "analysis":
            return await self._analyze_content(request_data, request_id)
        elif request_data.request_type.value == "generation":
            return await self._generate_content(request_data, request_id)
        elif request_data.request_type.value == "enhancement":
            return await self._enhance_content(request_data, request_id)
        elif request_data.request_type.value == "personalization":
            return await self._personalize_content(request_data, request_id)
        else:
            raise ValidationError("Unsupported request type", "request_type")

    # Content Analysis
    async def _analyze_content(self, request_data: AIRequestCreate, request_id: str) -> AIResult:
        """Analyze content using AI"""
        try:
            # Check cache first
            content_hash = self._generate_content_hash(request_data.input_text)
            cached_result = await self.db.get_cached_content(content_hash)

            if cached_result and ai_service_settings.enable_caching:
                logger.info("Using cached analysis result", extra={"request_id": request_id})
                return AIResult(**cached_result["content"])

            # Perform analysis (simplified - would call actual AI API)
            analysis_result = await self._perform_content_analysis(request_data.input_text)

            # Save result to database and return it
            result_id = await self.db.save_ai_result({
                "request_id": request_id,
                "user_id": request_data.user_id,
                "result_type": "analysis_report",
                "content": analysis_result.dict(),
                "confidence_score": analysis_result.quality_score
            })

            # Get the saved result
            saved_result = await self.db.get_ai_result(result_id)
            if not saved_result:
                raise DatabaseError("save_ai_result", "Failed to retrieve saved result")

            # Cache result
            if ai_service_settings.enable_caching:
                await self.db.save_cached_content({
                    "content_hash": content_hash,
                    "content": saved_result,
                    "request_type": "analysis"
                })

            return AIResult(**saved_result)

        except Exception as e:
            logger.error("Content analysis failed", extra={
                "request_id": request_id,
                "error": str(e)
            })
            raise ServiceUnavailableError("ai-service", f"Content analysis failed: {str(e)}")

    async def _perform_content_analysis(self, content: str) -> ContentAnalysisResult:
        """Perform actual content analysis"""
        # This would integrate with OpenAI/Anthropic APIs
        # For now, return mock analysis
        word_count = len(content.split())
        readability_score = min(100, max(0, 100 - (word_count / 10)))

        return ContentAnalysisResult(
            readability_score=readability_score,
            complexity_level="intermediate",
            key_topics=["programming", "education"],
            suggestions=["Add more examples", "Include code snippets"],
            word_count=word_count,
            estimated_reading_time=max(1, word_count // 200),
            quality_score=0.85
        )

    # Content Generation
    async def _generate_content(self, request_data: AIRequestCreate, request_id: str) -> AIResult:
        """Generate content using AI"""
        try:
            # Check cache
            content_hash = self._generate_content_hash(str(request_data.dict()))
            cached_result = await self.db.get_cached_content(content_hash)

            if cached_result and ai_service_settings.enable_caching:
                logger.info("Using cached generation result", extra={"request_id": request_id})
                return AIResult(**cached_result["content"])

            # Generate content (simplified)
            generation_result = await self._perform_content_generation(request_data)

            # Save result to database
            result_id = await self.db.save_ai_result({
                "request_id": request_id,
                "user_id": request_data.user_id,
                "result_type": "course_content",
                "content": generation_result.dict()
            })

            # Get the saved result
            saved_result = await self.db.get_ai_result(result_id)
            if not saved_result:
                raise DatabaseError("save_ai_result", "Failed to retrieve saved result")

            # Cache result
            if ai_service_settings.enable_caching:
                await self.db.save_cached_content({
                    "content_hash": content_hash,
                    "content": saved_result,
                    "request_type": "generation"
                })

            return AIResult(**saved_result)

        except Exception as e:
            logger.error("Content generation failed", extra={
                "request_id": request_id,
                "error": str(e)
            })
            raise ServiceUnavailableError("ai-service", f"Content generation failed: {str(e)}")

    async def _perform_content_generation(self, request_data: AIRequestCreate) -> ContentGenerationResult:
        """Perform actual content generation"""
        # This would integrate with AI APIs
        # Mock generation for now
        topic = (request_data.parameters or {}).get("topic", "General Topic")

        return ContentGenerationResult(
            title=f"Understanding {topic}",
            content=f"This is generated content about {topic}. It covers the key concepts and provides practical examples.",
            metadata={
                "topic": topic,
                "difficulty": (request_data.parameters or {}).get("difficulty_level", "intermediate"),
                "word_count": 150
            }
        )

    # Content Enhancement
    async def _enhance_content(self, request_data: AIRequestCreate, request_id: str) -> AIResult:
        """Enhance content using AI"""
        try:
            enhancement_result = await self._perform_content_enhancement(request_data)

            # Save result to database
            result_id = await self.db.save_ai_result({
                "request_id": request_id,
                "user_id": request_data.user_id,
                "result_type": "enhanced_content",
                "content": enhancement_result.dict(),
                "confidence_score": enhancement_result.confidence_score
            })

            # Get the saved result
            saved_result = await self.db.get_ai_result(result_id)
            if not saved_result:
                raise DatabaseError("save_ai_result", "Failed to retrieve saved result")

            return AIResult(**saved_result)

        except Exception as e:
            logger.error("Content enhancement failed", extra={
                "request_id": request_id,
                "error": str(e)
            })
            raise ServiceUnavailableError("ai-service", f"Content enhancement failed: {str(e)}")

    async def _perform_content_enhancement(self, request_data: AIRequestCreate) -> ContentEnhancementResult:
        """Perform actual content enhancement"""
        original_content = request_data.input_text
        original_length = len(original_content)

        # Mock enhancement
        enhanced_content = original_content + "\n\nAdditional enhanced content with more details and examples."

        return ContentEnhancementResult(
            enhanced_content=enhanced_content,
            improvements_made=["Added examples", "Improved clarity", "Enhanced structure"],
            confidence_score=0.88,
            original_length=original_length,
            enhanced_length=len(enhanced_content)
        )

    # Personalization
    async def _personalize_content(self, request_data: AIRequestCreate, request_id: str) -> AIResult:
        """Personalize content using AI"""
        try:
            personalization_result = await self._perform_content_personalization(request_data)

            # Save result to database
            result_id = await self.db.save_ai_result({
                "request_id": request_id,
                "user_id": request_data.user_id,
                "result_type": "recommendations",
                "content": personalization_result.dict(),
                "confidence_score": personalization_result.confidence_score
            })

            # Get the saved result
            saved_result = await self.db.get_ai_result(result_id)
            if not saved_result:
                raise DatabaseError("save_ai_result", "Failed to retrieve saved result")

            return AIResult(**saved_result)

        except Exception as e:
            logger.error("Content personalization failed", extra={
                "request_id": request_id,
                "error": str(e)
            })
            raise ServiceUnavailableError("ai-service", f"Content personalization failed: {str(e)}")

    async def _perform_content_personalization(self, request_data: AIRequestCreate) -> PersonalizationResult:
        """Perform actual content personalization"""
        # Mock personalization based on user preferences
        user_prefs = await self.db.get_user_preferences(request_data.user_id)

        recommendations = [
            {
                "type": "course",
                "title": "Advanced Python Programming",
                "reason": "Based on your learning preferences",
                "confidence": 0.9
            },
            {
                "type": "skill",
                "title": "Data Analysis",
                "reason": "Matches your career goals",
                "confidence": 0.85
            }
        ]

        return PersonalizationResult(
            recommendations=recommendations,
            user_profile=user_prefs or {},
            confidence_score=0.87
        )

    # User Preferences
    async def get_user_preferences(self, user_id: str) -> Optional[UserAIPreferences]:
        """Get user AI preferences"""
        try:
            prefs_data = await self.db.get_user_preferences(user_id)
            if not prefs_data:
                return None

            return UserAIPreferences(**prefs_data)

        except Exception as e:
            logger.error("Failed to get user preferences", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_user_preferences", f"User preferences retrieval failed: {str(e)}")

    async def update_user_preferences(self, user_id: str, preferences: UserAIPreferencesCreate) -> UserAIPreferences:
        """Update user AI preferences"""
        try:
            success = await self.db.update_user_preferences(user_id, preferences.dict())
            if not success:
                raise DatabaseError("update_user_preferences", "Failed to update preferences")

            # Get updated preferences
            updated_prefs = await self.get_user_preferences(user_id)
            if not updated_prefs:
                raise DatabaseError("update_user_preferences", "Failed to retrieve updated preferences")

            logger.info("User AI preferences updated", extra={"user_id": user_id})
            return updated_prefs

        except (DatabaseError, ValidationError):
            raise
        except Exception as e:
            logger.error("Failed to update user preferences", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("update_user_preferences", f"User preferences update failed: {str(e)}")

    # Analytics and Usage
    async def get_usage_stats(self, user_id: Optional[str] = None, days: int = 30) -> AIUsageStats:
        """Get AI usage statistics"""
        try:
            stats_data = await self.db.get_usage_stats(user_id, days)
            return AIUsageStats(**stats_data)

        except Exception as e:
            logger.error("Failed to get usage stats", extra={
                "user_id": user_id,
                "days": days,
                "error": str(e)
            })
            raise DatabaseError("get_usage_stats", f"Usage stats retrieval failed: {str(e)}")

    # Helper methods
    def _validate_request(self, request_data: AIRequestCreate) -> None:
        """Validate AI request"""
        if len(request_data.input_text) > ai_service_settings.max_analysis_input_length:
            raise ValidationError("Input text too long", "input_text")

        if request_data.parameters and len(str(request_data.parameters)) > 1000:
            raise ValidationError("Parameters too complex", "parameters")

    async def _check_rate_limits(self, user_id: str, request_type: str) -> None:
        """Check rate limits for user"""
        # This would implement actual rate limiting logic
        # For now, just log the check
        logger.info("Rate limit check", extra={
            "user_id": user_id,
            "request_type": request_type
        })

    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content caching"""
        return hashlib.md5(content.encode()).hexdigest()

    # Performance Analysis Methods
    async def analyze_performance(self, user_id: str, course_id: Optional[str] = None,
                                timeframe: Optional[str] = "month", requested_by: Optional[str] = None) -> PerformanceAnalysisResponse:
        """Analyze student performance using AI"""
        try:
            # Get performance data from database (would be from other services)
            # For now, simulate data retrieval
            performance_data = await self._get_performance_data(user_id, course_id, timeframe)

            # Generate AI analysis
            analysis_result = await self._generate_performance_analysis(performance_data)

            return PerformanceAnalysisResponse(
                analysis=analysis_result["analysis"],
                metrics=analysis_result["metrics"],
                performance_level=analysis_result["performance_level"],
                recommendations=analysis_result["recommendations"],
                generated_at=datetime.now(timezone.utc).isoformat(),
                analyzed_by=requested_by or "system",
                target_user=user_id
            )

        except Exception as e:
            logger.error("Performance analysis failed", extra={
                "user_id": user_id,
                "course_id": course_id,
                "error": str(e)
            })
            raise ServiceUnavailableError("ai-service", f"Performance analysis failed: {str(e)}")

    async def analyze_course_performance(self, course_id: str, include_individual_students: bool = False,
                                       requested_by: Optional[str] = None) -> CoursePerformanceAnalysisResponse:
        """Analyze course performance using AI"""
        try:
            # Get course data
            course_data = await self._get_course_data(course_id)

            # Generate AI analysis
            analysis_result = await self._generate_course_analysis(course_data, include_individual_students)

            return CoursePerformanceAnalysisResponse(
                course_analysis=analysis_result["course_analysis"],
                course_metrics=analysis_result["course_metrics"],
                engagement_indicators=analysis_result["engagement_indicators"],
                generated_at=datetime.now(timezone.utc).isoformat(),
                analyzed_by=requested_by or "system",
                individual_analyses=analysis_result.get("individual_analyses")
            )

        except Exception as e:
            logger.error("Course performance analysis failed", extra={
                "course_id": course_id,
                "error": str(e)
            })
            raise ServiceUnavailableError("ai-service", f"Course performance analysis failed: {str(e)}")

    async def predict_performance(self, user_id: str, course_id: str, requested_by: Optional[str] = None) -> PerformancePredictionResponse:
        """Predict student performance using AI"""
        try:
            # Get historical data
            historical_data = await self._get_historical_performance_data(user_id, course_id)

            # Generate AI prediction
            prediction_result = await self._generate_performance_prediction(historical_data)

            return PerformancePredictionResponse(
                prediction=prediction_result["prediction"],
                current_metrics=prediction_result["current_metrics"],
                prediction_factors=prediction_result["prediction_factors"],
                generated_at=datetime.now(timezone.utc).isoformat(),
                predicted_for=user_id,
                course_id=course_id,
                predicted_by=requested_by or "system"
            )

        except Exception as e:
            logger.error("Performance prediction failed", extra={
                "user_id": user_id,
                "course_id": course_id,
                "error": str(e)
            })
            raise ServiceUnavailableError("ai-service", f"Performance prediction failed: {str(e)}")

    # Helper methods for performance analysis
    async def _get_performance_data(self, user_id: str, course_id: Optional[str] = None,
                                  timeframe: Optional[str] = "month") -> Dict[str, Any]:
        """Get performance data (would integrate with other services)"""
        # Mock data for now
        return {
            "user_id": user_id,
            "course_id": course_id,
            "timeframe": timeframe,
            "completed_courses": 3,
            "average_progress": 75.5,
            "total_submissions": 15,
            "average_grade": 82.3,
            "enrolled_courses": 5
        }

    async def _get_course_data(self, course_id: str) -> Dict[str, Any]:
        """Get course data (would integrate with course service)"""
        # Mock data for now
        return {
            "course_id": course_id,
            "title": "Python Programming",
            "total_enrolled": 50,
            "active_students": 45,
            "completion_rate": 68.5,
            "average_progress": 72.3,
            "completed_students": 31
        }

    async def _get_historical_performance_data(self, user_id: str, course_id: str) -> Dict[str, Any]:
        """Get historical performance data"""
        # Mock data for now
        return {
            "user_id": user_id,
            "course_id": course_id,
            "completed_courses": 3,
            "average_progress": 75.5,
            "average_grade": 82.3,
            "total_submissions": 15
        }

    async def _generate_performance_analysis(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered performance analysis"""
        # Mock AI analysis for now
        avg_progress = performance_data.get("average_progress", 0)

        analysis = f"""
        Performance Analysis for User {performance_data['user_id']}

        Overall Assessment: {'Excellent' if avg_progress > 85 else 'Good' if avg_progress > 70 else 'Developing'}

        Key Metrics:
        - Courses Completed: {performance_data.get('completed_courses', 0)}
        - Average Progress: {avg_progress:.1f}%
        - Average Grade: {performance_data.get('average_grade', 0):.1f}%
        - Total Submissions: {performance_data.get('total_submissions', 0)}

        Recommendations:
        1. Continue with current study habits for excellent progress
        2. Focus on completing remaining course modules
        3. Consider advanced topics for further skill development
        """

        return {
            "analysis": analysis.strip(),
            "metrics": {
                "completed_courses": performance_data.get("completed_courses", 0),
                "average_progress": round(avg_progress, 1),
                "total_submissions": performance_data.get("total_submissions", 0),
                "average_grade": round(performance_data.get("average_grade", 0), 1),
                "enrolled_courses": performance_data.get("enrolled_courses", 0)
            },
            "performance_level": "Excellent" if avg_progress > 85 else "Good" if avg_progress > 70 else "Developing",
            "recommendations": [
                "Continue with current study habits",
                "Focus on completing remaining modules",
                "Consider advanced topics"
            ]
        }

    async def _generate_course_analysis(self, course_data: Dict[str, Any],
                                      include_individual: bool = False) -> Dict[str, Any]:
        """Generate AI-powered course analysis"""
        # Mock AI analysis for now
        completion_rate = course_data.get("completion_rate", 0)

        analysis = f"""
        Course Performance Analysis: {course_data.get('title', 'Unknown Course')}

        Overall Effectiveness: {'High' if completion_rate > 75 else 'Moderate' if completion_rate > 60 else 'Needs Improvement'}

        Key Metrics:
        - Total Enrolled: {course_data.get('total_enrolled', 0)}
        - Active Students: {course_data.get('active_students', 0)}
        - Completion Rate: {completion_rate:.1f}%
        - Average Progress: {course_data.get('average_progress', 0):.1f}%

        Recommendations:
        1. Content is engaging with good completion rates
        2. Consider additional support for struggling students
        3. Review course structure for optimal learning flow
        """

        result = {
            "course_analysis": analysis.strip(),
            "course_metrics": {
                "course_id": course_data.get("course_id"),
                "course_title": course_data.get("title", "Unknown"),
                "total_enrolled": course_data.get("total_enrolled", 0),
                "active_students": course_data.get("active_students", 0),
                "completion_rate": round(completion_rate, 1),
                "average_progress": round(course_data.get("average_progress", 0), 1),
                "completed_students": course_data.get("completed_students", 0)
            },
            "engagement_indicators": {
                "enrollment_rate": round((course_data.get("active_students", 0) / max(course_data.get("total_enrolled", 1), 1)) * 100, 1),
                "completion_rate": round(completion_rate, 1),
                "average_progress": round(course_data.get("average_progress", 0), 1)
            }
        }

        if include_individual:
            # Mock individual analyses
            result["individual_analyses"] = [
                {
                    "user_id": "user_1",
                    "progress": 85.5,
                    "completed": True,
                    "analysis": "Excellent performance with consistent engagement"
                },
                {
                    "user_id": "user_2",
                    "progress": 62.3,
                    "completed": False,
                    "analysis": "Good progress but needs additional support"
                }
            ]

        return result

    async def _generate_performance_prediction(self, historical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered performance prediction"""
        # Mock AI prediction for now
        avg_progress = historical_data.get("average_progress", 0)
        avg_grade = historical_data.get("average_grade", 0)

        prediction = f"""
        Performance Prediction for User {historical_data['user_id']}

        Predicted Final Grade: {'A' if avg_grade > 90 else 'B' if avg_grade > 80 else 'C' if avg_grade > 70 else 'D'}

        Predicted Completion Probability: {min(95, avg_progress + 10)}%

        Key Factors:
        - Historical Performance: {'Strong' if avg_progress > 75 else 'Moderate' if avg_progress > 50 else 'Developing'}
        - Grade Performance: {'Excellent' if avg_grade > 85 else 'Good' if avg_grade > 75 else 'Needs Improvement'}
        - Engagement Level: {'High' if historical_data.get('total_submissions', 0) > 10 else 'Medium'}

        Recommendations to Improve Prediction:
        1. Maintain consistent study schedule
        2. Focus on understanding core concepts
        3. Seek additional help when needed
        """

        return {
            "prediction": prediction.strip(),
            "current_metrics": {
                "completed_courses": historical_data.get("completed_courses", 0),
                "average_progress": round(avg_progress, 1),
                "average_grade": round(avg_grade, 1),
                "total_submissions": historical_data.get("total_submissions", 0)
            },
            "prediction_factors": {
                "historical_performance": "Strong" if avg_progress > 75 else "Moderate" if avg_progress > 50 else "Developing",
                "consistency": "High" if historical_data.get("total_submissions", 0) > 10 else "Medium" if historical_data.get("total_submissions", 0) > 5 else "Low",
                "engagement": "High" if historical_data.get("completed_courses", 0) > 2 else "Medium" if historical_data.get("completed_courses", 0) > 0 else "Low"
            }
        }

# Global service instance
ai_service = AIService()