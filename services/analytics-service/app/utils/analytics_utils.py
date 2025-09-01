"""
Analytics Service Utility Functions
"""
import statistics
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from shared.common.logging import get_logger
from config.config import analytics_service_settings

logger = get_logger("analytics-service-utils")

def calculate_performance_trend(scores: List[float]) -> str:
    """Calculate performance trend from score history"""
    if len(scores) < 2:
        return "insufficient_data"

    # Calculate moving averages
    recent_avg = statistics.mean(scores[-3:]) if len(scores) >= 3 else statistics.mean(scores)
    earlier_avg = statistics.mean(scores[:-3]) if len(scores) > 3 else recent_avg

    if recent_avg > earlier_avg + 5:
        return "improving"
    elif recent_avg < earlier_avg - 5:
        return "declining"
    else:
        return "stable"

def calculate_completion_rate(completed: int, total: int) -> float:
    """Calculate completion rate as percentage"""
    if total == 0:
        return 0.0
    return round((completed / total) * 100, 2)

def calculate_engagement_score(metrics: Dict[str, Any]) -> float:
    """Calculate engagement score from various metrics"""
    score = 0.0

    # Login frequency (max 30 points)
    login_freq = metrics.get("login_frequency", 0)
    score += min(login_freq * 2, 30)

    # Session duration (max 25 points)
    session_duration = metrics.get("session_duration", 0)
    score += min(session_duration / 10, 25)  # 1 point per 10 minutes

    # Content interactions (max 25 points)
    interactions = metrics.get("content_interactions", 0)
    score += min(interactions / 2, 25)  # 1 point per 2 interactions

    # Quiz attempts (max 20 points)
    quiz_attempts = metrics.get("quiz_attempts", 0)
    score += min(quiz_attempts * 2, 20)

    return round(score, 2)

def detect_anomalies(data_points: List[float], threshold: float = 2.0) -> List[int]:
    """Detect anomalous data points using standard deviation"""
    if len(data_points) < 3:
        return []

    mean = statistics.mean(data_points)
    stdev = statistics.stdev(data_points)

    anomalies = []
    for i, point in enumerate(data_points):
        if abs(point - mean) > threshold * stdev:
            anomalies.append(i)

    return anomalies

def calculate_percentile_rank(value: float, population: List[float]) -> float:
    """Calculate percentile rank of a value in a population"""
    if not population:
        return 0.0

    sorted_population = sorted(population)
    count = len(sorted_population)

    # Find position
    for i, pop_value in enumerate(sorted_population):
        if value <= pop_value:
            return (i / count) * 100

    return 100.0

def aggregate_time_series_data(data_points: List[Dict[str, Any]], interval: str = "day") -> Dict[str, List[float]]:
    """Aggregate time series data by interval"""
    aggregated = {}

    for point in data_points:
        timestamp = point.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        if interval == "day":
            key = timestamp.date().isoformat()
        elif interval == "hour":
            key = timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
        else:
            key = timestamp.date().isoformat()

        if key not in aggregated:
            aggregated[key] = []

        value = point.get("value", 0)
        aggregated[key].append(value)

    # Calculate averages for each interval
    for key in aggregated:
        aggregated[key] = round(statistics.mean(aggregated[key]), 2)

    return aggregated

def generate_performance_insights(analytics_data: Dict[str, Any]) -> List[str]:
    """Generate performance insights from analytics data"""
    insights = []

    avg_performance = analytics_data.get("average_performance", 0)
    completion_rate = analytics_data.get("completion_rate", 0)
    total_study_hours = analytics_data.get("total_study_hours", 0)

    if avg_performance >= 85:
        insights.append("Excellent performance - student is excelling")
    elif avg_performance >= 70:
        insights.append("Good performance with potential for improvement")
    elif avg_performance >= 60:
        insights.append("Performance needs attention")
    else:
        insights.append("Significant performance concerns - intervention recommended")

    if completion_rate >= 80:
        insights.append("Strong course completion rate")
    elif completion_rate >= 60:
        insights.append("Moderate completion rate - could be improved")
    else:
        insights.append("Low completion rate - focus on engagement")

    if total_study_hours > 50:
        insights.append("High study time commitment")
    elif total_study_hours > 20:
        insights.append("Moderate study time")
    else:
        insights.append("Low study time - consider increasing engagement")

    return insights

def calculate_risk_score(student_data: Dict[str, Any]) -> float:
    """Calculate risk score for student performance issues"""
    score = 0.0

    # Performance factor
    avg_performance = student_data.get("average_performance", 100)
    if avg_performance < 60:
        score += 40
    elif avg_performance < 70:
        score += 20

    # Completion factor
    completion_rate = student_data.get("completion_rate", 100)
    if completion_rate < 50:
        score += 30
    elif completion_rate < 75:
        score += 15

    # Engagement factor
    engagement_score = student_data.get("engagement_score", 100)
    if engagement_score < 30:
        score += 30
    elif engagement_score < 50:
        score += 15

    return min(score, 100.0)

def generate_recommendations(risk_score: float, student_data: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on risk score"""
    recommendations = []

    if risk_score > 70:
        recommendations.extend([
            "Immediate intervention recommended",
            "Schedule meeting with academic advisor",
            "Consider tutoring support",
            "Review study habits and time management"
        ])
    elif risk_score > 50:
        recommendations.extend([
            "Monitor closely",
            "Provide additional resources",
            "Encourage increased study time",
            "Consider peer mentoring"
        ])
    elif risk_score > 30:
        recommendations.extend([
            "Light monitoring recommended",
            "Suggest study groups",
            "Provide additional practice materials"
        ])
    else:
        recommendations.append("Student performing well - continue current approach")

    return recommendations

def validate_analytics_data(data: Dict[str, Any]) -> bool:
    """Validate analytics data structure"""
    required_fields = ["student_id", "course_id", "performance_score"]

    for field in required_fields:
        if field not in data:
            return False

    # Validate score ranges
    score = data.get("performance_score", 0)
    if not (0 <= score <= 100):
        return False

    return True

def anonymize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Anonymize sensitive data for analytics"""
    anonymized = data.copy()

    # Remove or hash sensitive fields
    sensitive_fields = ["email", "name", "personal_info"]
    for field in sensitive_fields:
        if field in anonymized:
            if analytics_service_settings.enable_pii_masking:
                anonymized[field] = "REDACTED"
            else:
                del anonymized[field]

    return anonymized

def calculate_learning_velocity(progress_data: List[Dict[str, Any]]) -> float:
    """Calculate learning velocity (progress per unit time)"""
    if len(progress_data) < 2:
        return 0.0

    # Sort by time
    sorted_data = sorted(progress_data, key=lambda x: x.get("timestamp", datetime.now(timezone.utc)))

    # Calculate total progress and time span
    first_timestamp = sorted_data[0].get("timestamp")
    last_timestamp = sorted_data[-1].get("timestamp")

    if isinstance(first_timestamp, str):
        first_timestamp = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00'))
    if isinstance(last_timestamp, str):
        last_timestamp = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))

    time_span_hours = (last_timestamp - first_timestamp).total_seconds() / 3600

    if time_span_hours == 0:
        return 0.0

    first_progress = sorted_data[0].get("progress", 0)
    last_progress = sorted_data[-1].get("progress", 0)

    progress_change = last_progress - first_progress

    return round(progress_change / time_span_hours, 4)

def format_analytics_for_export(analytics_data: Dict[str, Any], format_type: str) -> Dict[str, Any]:
    """Format analytics data for export"""
    if format_type == "csv":
        # Flatten nested structures for CSV
        flattened = {}
        for key, value in analytics_data.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flattened[f"{key}_{sub_key}"] = sub_value
            elif isinstance(value, list):
                flattened[key] = ", ".join(map(str, value))
            else:
                flattened[key] = value
        return flattened

    elif format_type == "json":
        return analytics_data

    else:
        return analytics_data

def calculate_confidence_interval(data: List[float], confidence: float = 0.95) -> Dict[str, float]:
    """Calculate confidence interval for data"""
    if len(data) < 2:
        return {"mean": statistics.mean(data) if data else 0, "lower": 0, "upper": 0}

    mean = statistics.mean(data)
    stdev = statistics.stdev(data)
    n = len(data)

    # Z-score for 95% confidence
    z_score = 1.96

    margin = z_score * (stdev / (n ** 0.5))

    return {
        "mean": round(mean, 2),
        "lower": round(mean - margin, 2),
        "upper": round(mean + margin, 2),
        "confidence_level": confidence
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