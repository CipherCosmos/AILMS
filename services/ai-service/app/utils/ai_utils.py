"""
AI Service Utility Functions
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from shared.common.logging import get_logger
from shared.common.errors import ValidationError
from config.config import ai_service_settings

logger = get_logger("ai-service-utils")

def generate_content_hash(content: str) -> str:
    """Generate hash for content caching"""
    return hashlib.md5(content.encode()).hexdigest()

def validate_ai_request(request_data: Dict[str, Any]) -> None:
    """Validate AI request data"""
    if not request_data.get("input_text"):
        raise ValidationError("Input text is required", "input_text")

    if len(request_data["input_text"]) > ai_service_settings.max_analysis_input_length:
        raise ValidationError("Input text too long", "input_text")

    if request_data.get("parameters") and len(str(request_data["parameters"])) > 1000:
        raise ValidationError("Parameters too complex", "parameters")

def calculate_tokens(text: str) -> int:
    """Calculate approximate token count for text"""
    # Simple approximation: 1 token ≈ 4 characters
    return len(text) // 4

def estimate_cost(tokens: int, model: str) -> float:
    """Estimate cost for AI request"""
    # Simplified cost calculation
    if model == "gpt-4":
        return (tokens / 1000) * 0.03  # $0.03 per 1K tokens
    elif model == "gpt-3.5-turbo":
        return (tokens / 1000) * 0.002  # $0.002 per 1K tokens
    else:
        return (tokens / 1000) * 0.01  # Default rate

def check_rate_limit(user_id: str, request_type: str) -> bool:
    """Check if user has exceeded rate limits"""
    # This would integrate with Redis for actual rate limiting
    # For now, return True (allow request)
    logger.info("Rate limit check", extra={
        "user_id": user_id,
        "request_type": request_type
    })
    return True

def sanitize_content(content: str) -> str:
    """Sanitize content for AI processing"""
    # Remove potentially harmful content
    # This would include more sophisticated filtering
    return content.strip()

def format_ai_response(result: Dict[str, Any], result_type: str) -> Dict[str, Any]:
    """Format AI response for API output"""
    return {
        "result_type": result_type,
        "content": result,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "model": ai_service_settings.default_model,
            "service": "ai-service"
        }
    }

def extract_keywords(text: str, max_keywords: int = 10) -> list:
    """Extract keywords from text"""
    # Simple keyword extraction (would use NLP in production)
    words = text.lower().split()
    keywords = []

    # Filter out common stop words
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
    filtered_words = [word for word in words if word not in stop_words and len(word) > 3]

    # Count frequency
    word_count = {}
    for word in filtered_words:
        word_count[word] = word_count.get(word, 0) + 1

    # Sort by frequency
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)

    # Return top keywords
    keywords = [word for word, count in sorted_words[:max_keywords]]

    return keywords

def calculate_readability_score(text: str) -> float:
    """Calculate readability score for text"""
    sentences = text.split('.')
    words = text.split()
    syllables = sum(count_syllables(word) for word in words)

    if not sentences or not words:
        return 0.0

    # Flesch Reading Ease formula
    score = 206.835 - 1.015 * (len(words) / len(sentences)) - 84.6 * (syllables / len(words))

    return max(0.0, min(100.0, score))

def count_syllables(word: str) -> int:
    """Count syllables in a word"""
    word = word.lower()
    count = 0
    vowels = "aeiouy"

    if word[0] in vowels:
        count += 1

    for i in range(1, len(word)):
        if word[i] in vowels and word[i - 1] not in vowels:
            count += 1

    if word.endswith("e"):
        count -= 1

    return max(1, count)

def generate_cache_key(user_id: str, content_hash: str, operation: str) -> str:
    """Generate cache key for AI operations"""
    return f"ai:{user_id}:{operation}:{content_hash}"

def validate_model_compatibility(model: str, operation: str) -> bool:
    """Validate if model is compatible with operation"""
    compatible_models = {
        "analysis": ["gpt-4", "gpt-3.5-turbo"],
        "generation": ["gpt-4", "gpt-3.5-turbo"],
        "enhancement": ["gpt-4", "gpt-3.5-turbo"],
        "personalization": ["gpt-4", "gpt-3.5-turbo"]
    }

    return model in compatible_models.get(operation, [])

def log_ai_metrics(user_id: str, operation: str, tokens: int, cost: float, duration: float) -> None:
    """Log AI usage metrics"""
    logger.info("AI metrics", extra={
        "user_id": user_id,
        "operation": operation,
        "tokens": tokens,
        "cost": cost,
        "duration_seconds": duration,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

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