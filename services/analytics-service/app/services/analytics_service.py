"""
Analytics Service Business Logic Layer
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from shared.common.logging import get_logger
from shared.common.errors import ValidationError, DatabaseError, NotFoundError

from database.database import analytics_db
from models import (
    CourseAnalytics, StudentAnalytics,
    PerformanceMetric, Report, RealTimeMetric,
    AnalyticsDashboard, PerformanceInsights,
    EngagementMetrics, PredictiveAnalytics,
    MetricType, ReportType, TimeRange
)
from config.config import analytics_service_settings

logger = get_logger("analytics-service")

class AnalyticsService:
    """Analytics service business logic"""

    def __init__(self):
        self.db = analytics_db

    # Course analytics operations
    async def get_course_analytics(self, course_id: str) -> CourseAnalytics:
        """Get course analytics"""
        try:
            analytics_data = await self.db.get_course_analytics(course_id)
            if not analytics_data:
                # Generate analytics if not found
                return await self._generate_course_analytics(course_id)

            return CourseAnalytics(**analytics_data)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get course analytics", extra={
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("get_course_analytics", f"Course analytics retrieval failed: {str(e)}")

    async def _generate_course_analytics(self, course_id: str) -> CourseAnalytics:
        """Generate course analytics from raw data"""
        try:
            # Aggregate data from various sources
            aggregated_data = await self.db.aggregate_course_performance(course_id)

            analytics_data = {
                "course_id": course_id,
                "enrollment_count": aggregated_data.get("total_students", 0),
                "completion_rate": aggregated_data.get("completion_rate", 0.0) * 100,
                "average_performance": aggregated_data.get("avg_performance", 0.0),
                "total_study_hours": aggregated_data.get("total_study_hours", 0),
                "active_students": aggregated_data.get("total_students", 0),  # Simplified
                "dropout_rate": 0.0,  # Would calculate from enrollment data
                "last_updated": datetime.now(timezone.utc)
            }

            # Save to database
            await self.db.update_course_analytics(course_id, analytics_data)

            logger.info("Course analytics generated", extra={
                "course_id": course_id,
                "enrollment_count": analytics_data["enrollment_count"]
            })

            return CourseAnalytics(**analytics_data)

        except Exception as e:
            logger.error("Failed to generate course analytics", extra={
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("generate_course_analytics", f"Course analytics generation failed: {str(e)}")

    # Student analytics operations
    async def get_student_analytics(self, student_id: str) -> StudentAnalytics:
        """Get student analytics"""
        try:
            analytics_data = await self.db.get_student_analytics(student_id)
            if not analytics_data:
                # Generate analytics if not found
                return await self._generate_student_analytics(student_id)

            return StudentAnalytics(**analytics_data)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get student analytics", extra={
                "student_id": student_id,
                "error": str(e)
            })
            raise DatabaseError("get_student_analytics", f"Student analytics retrieval failed: {str(e)}")

    async def _generate_student_analytics(self, student_id: str) -> StudentAnalytics:
        """Generate student analytics from raw data"""
        try:
            # Aggregate data from various sources
            aggregated_data = await self.db.aggregate_student_performance(student_id)

            analytics_data = {
                "student_id": student_id,
                "courses_enrolled": aggregated_data.get("total_courses", 0),
                "courses_completed": aggregated_data.get("courses_completed", 0),
                "average_performance": aggregated_data.get("avg_performance", 0.0),
                "total_study_hours": aggregated_data.get("total_study_hours", 0),
                "current_streak": 0,  # Would calculate from session data
                "learning_velocity": 0.0,  # Would calculate from progress data
                "last_updated": datetime.now(timezone.utc)
            }

            # Save to database
            await self.db.update_student_analytics(student_id, analytics_data)

            logger.info("Student analytics generated", extra={
                "student_id": student_id,
                "courses_enrolled": analytics_data["courses_enrolled"]
            })

            return StudentAnalytics(**analytics_data)

        except Exception as e:
            logger.error("Failed to generate student analytics", extra={
                "student_id": student_id,
                "error": str(e)
            })
            raise DatabaseError("generate_student_analytics", f"Student analytics generation failed: {str(e)}")

    # Performance metrics operations
    async def record_performance_metric(self, metric_data: Dict[str, Any]) -> str:
        """Record a performance metric"""
        try:
            # Validate metric data
            self._validate_performance_metric(metric_data)

            metric_id = await self.db.save_performance_metric(metric_data)

            logger.info("Performance metric recorded", extra={
                "metric_id": metric_id,
                "student_id": metric_data.get("student_id"),
                "course_id": metric_data.get("course_id")
            })

            return metric_id

        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to record performance metric", extra={"error": str(e)})
            raise DatabaseError("record_performance_metric", f"Performance metric recording failed: {str(e)}")

    async def get_performance_metrics(self, student_id: str, course_id: Optional[str] = None,
                                    time_range: TimeRange = TimeRange.MONTH) -> List[PerformanceMetric]:
        """Get performance metrics for a student"""
        try:
            # Calculate date range
            now = datetime.now(timezone.utc)
            if time_range == TimeRange.DAY:
                start_date = now - timedelta(days=1)
            elif time_range == TimeRange.WEEK:
                start_date = now - timedelta(weeks=1)
            elif time_range == TimeRange.MONTH:
                start_date = now - timedelta(days=30)
            elif time_range == TimeRange.QUARTER:
                start_date = now - timedelta(days=90)
            else:  # YEAR
                start_date = now - timedelta(days=365)

            # Get metrics from database
            metrics_data = await self.db.get_performance_metrics(student_id, course_id, 1000)

            # Filter by date range
            filtered_metrics = [
                metric for metric in metrics_data
                if metric.get("recorded_at") and
                isinstance(metric["recorded_at"], datetime) and
                metric["recorded_at"] >= start_date
            ]

            return [PerformanceMetric(**metric) for metric in filtered_metrics]

        except Exception as e:
            logger.error("Failed to get performance metrics", extra={
                "student_id": student_id,
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("get_performance_metrics", f"Performance metrics retrieval failed: {str(e)}")

    # Report generation operations
    async def generate_report(self, report_type: ReportType, parameters: Dict[str, Any],
                            created_by: str) -> Report:
        """Generate an analytics report"""
        try:
            # Generate report data based on type
            if report_type == ReportType.COURSE_ANALYTICS:
                report_data = await self._generate_course_report(parameters)
            elif report_type == ReportType.STUDENT_PROGRESS:
                report_data = await self._generate_student_report(parameters)
            elif report_type == ReportType.PERFORMANCE_SUMMARY:
                report_data = await self._generate_performance_report(parameters)
            else:
                report_data = {"message": "Custom report generation not implemented"}

            report_dict = {
                "title": f"{report_type.value.replace('_', ' ').title()} Report",
                "description": f"Generated {report_type.value} report",
                "report_type": report_type,
                "data": report_data,
                "parameters": parameters,
                "created_by": created_by,
                "generated_at": datetime.now(timezone.utc)
            }

            # Save report
            report_id = await self.db.save_report(report_dict)

            logger.info("Report generated", extra={
                "report_id": report_id,
                "report_type": report_type.value,
                "created_by": created_by
            })

            return Report(**report_dict)

        except Exception as e:
            logger.error("Failed to generate report", extra={
                "report_type": report_type.value,
                "error": str(e)
            })
            raise DatabaseError("generate_report", f"Report generation failed: {str(e)}")

    async def get_reports(self, report_type: Optional[ReportType] = None, limit: int = 50) -> List[Report]:
        """Get generated reports"""
        try:
            reports_data = await self.db.get_reports(report_type.value if report_type else None, limit)
            return [Report(**report) for report in reports_data]

        except Exception as e:
            logger.error("Failed to get reports", extra={
                "report_type": report_type.value if report_type else None,
                "error": str(e)
            })
            raise DatabaseError("get_reports", f"Reports retrieval failed: {str(e)}")

    # Dashboard operations
    async def get_analytics_dashboard(self, user_id: str, user_role: str) -> AnalyticsDashboard:
        """Get analytics dashboard for user"""
        try:
            dashboard_data = {
                "course_analytics": [],
                "student_analytics": [],
                "recent_metrics": [],
                "generated_at": datetime.now(timezone.utc)
            }

            if user_role == "instructor":
                # Get course analytics for instructor's courses
                # This would query course service to get instructor's courses
                course_ids = ["course_1", "course_2"]  # Mock data
                for course_id in course_ids:
                    try:
                        course_analytics = await self.get_course_analytics(course_id)
                        dashboard_data["course_analytics"].append(course_analytics)
                    except NotFoundError:
                        continue

            elif user_role == "student":
                # Get student's analytics
                try:
                    student_analytics = await self.get_student_analytics(user_id)
                    dashboard_data["student_analytics"].append(student_analytics)
                except NotFoundError:
                    pass

            # Get recent real-time metrics
            recent_metrics = await self.db.get_real_time_metrics("performance", hours=24)
            dashboard_data["recent_metrics"] = [RealTimeMetric(**metric) for metric in recent_metrics[:10]]

            return AnalyticsDashboard(**dashboard_data)

        except Exception as e:
            logger.error("Failed to get analytics dashboard", extra={
                "user_id": user_id,
                "user_role": user_role,
                "error": str(e)
            })
            raise DatabaseError("get_analytics_dashboard", f"Dashboard retrieval failed: {str(e)}")

    # Real-time metrics operations
    async def record_real_time_metric(self, metric_type: MetricType, value: float,
                                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """Record a real-time metric"""
        try:
            metric_data = {
                "metric_type": metric_type,
                "value": value,
                "metadata": metadata or {}
            }

            metric_id = await self.db.save_real_time_metric(metric_data)

            logger.info("Real-time metric recorded", extra={
                "metric_id": metric_id,
                "metric_type": metric_type.value,
                "value": value
            })

            return metric_id

        except Exception as e:
            logger.error("Failed to record real-time metric", extra={
                "metric_type": metric_type.value,
                "error": str(e)
            })
            raise DatabaseError("record_real_time_metric", f"Real-time metric recording failed: {str(e)}")

    # Predictive analytics operations
    async def generate_predictive_analytics(self, student_id: str, course_id: str) -> PredictiveAnalytics:
        """Generate predictive analytics for student performance"""
        try:
            # Get historical performance data
            performance_metrics = await self.get_performance_metrics(student_id, course_id, TimeRange.MONTH)

            # Simple predictive model (would use ML in production)
            if not performance_metrics:
                completion_probability = 0.5
                expected_grade = 70.0
            else:
                # Calculate based on recent performance
                recent_scores = [m.performance_score for m in performance_metrics[-5:]]
                avg_recent = sum(recent_scores) / len(recent_scores) if recent_scores else 70.0

                completion_probability = min(1.0, avg_recent / 100.0)
                expected_grade = avg_recent

            # Determine risk factors
            risk_factors = []
            if expected_grade < 60:
                risk_factors.append("Low recent performance")
            if len(performance_metrics) < 3:
                risk_factors.append("Limited performance data")

            # Generate interventions
            interventions = []
            if expected_grade < 70:
                interventions.append("Increase study time")
                interventions.append("Seek additional tutoring")

            predictive_data = {
                "student_id": student_id,
                "course_id": course_id,
                "completion_probability": completion_probability,
                "expected_grade": expected_grade,
                "risk_factors": risk_factors,
                "interventions": interventions,
                "predicted_at": datetime.now(timezone.utc)
            }

            return PredictiveAnalytics(**predictive_data)

        except Exception as e:
            logger.error("Failed to generate predictive analytics", extra={
                "student_id": student_id,
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("generate_predictive_analytics", f"Predictive analytics generation failed: {str(e)}")

    # Helper methods
    def _validate_performance_metric(self, metric_data: Dict[str, Any]) -> None:
        """Validate performance metric data"""
        required_fields = ["student_id", "course_id", "performance_score"]
        for field in required_fields:
            if field not in metric_data:
                raise ValidationError(f"Missing required field: {field}", field)

        if not (0 <= metric_data["performance_score"] <= 100):
            raise ValidationError("Performance score must be between 0 and 100", "performance_score")

    async def _generate_course_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate course analytics report"""
        course_id = parameters.get("course_id")
        if not course_id:
            raise ValidationError("Course ID required for course report", "course_id")

        course_analytics = await self.get_course_analytics(course_id)

        return {
            "course_id": course_id,
            "analytics": course_analytics.dict(),
            "summary": {
                "enrollment_trend": "stable",  # Would analyze historical data
                "performance_trend": "improving" if course_analytics.average_performance > 75 else "needs_attention",
                "completion_trend": "good" if course_analytics.completion_rate > 80 else "concerning"
            }
        }

    async def _generate_student_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate student progress report"""
        student_id = parameters.get("student_id")
        if not student_id:
            raise ValidationError("Student ID required for student report", "student_id")

        student_analytics = await self.get_student_analytics(student_id)

        return {
            "student_id": student_id,
            "analytics": student_analytics.dict(),
            "insights": await self._generate_performance_insights(student_id)
        }

    async def _generate_performance_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance summary report"""
        # Generate overall performance summary
        return {
            "total_students": 0,  # Would aggregate from database
            "average_performance": 0.0,
            "completion_rate": 0.0,
            "top_performers": [],
            "needs_attention": []
        }

    async def _generate_performance_insights(self, student_id: str) -> List[str]:
        """Generate performance insights for a student"""
        try:
            student_analytics = await self.get_student_analytics(student_id)
            insights = []

            if student_analytics.average_performance > 85:
                insights.append("Excellent performance across all courses")
            elif student_analytics.average_performance > 70:
                insights.append("Good performance with room for improvement")
            else:
                insights.append("Performance needs attention and additional support")

            if student_analytics.courses_completed > student_analytics.courses_enrolled * 0.8:
                insights.append("Strong course completion rate")
            else:
                insights.append("Consider focusing on course completion")

            return insights

        except Exception:
            return ["Unable to generate insights due to limited data"]

# Global service instance
analytics_service = AnalyticsService()