"""
User profile management routes for User Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations, _uuid
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("user-service")
router = APIRouter()
user_profiles_db = DatabaseOperations("user_profiles")

async def _current_user(token: Optional[str] = None):
    """Get current authenticated user"""
    if not token:
        raise HTTPException(401, "No authentication token provided")

    try:
        import jwt
        from shared.config.config import settings

        # Decode and validate JWT token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        # Verify token hasn't expired
        if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(401, "Token has expired")

        # Get user from database
        users_db = DatabaseOperations("users")
        user = await users_db.find_one({"_id": payload.get("sub")})
        if not user:
            raise HTTPException(401, "User not found")

        return {
            "id": user["_id"],
            "role": user.get("role", "student"),
            "email": user.get("email", ""),
            "name": user.get("name", "")
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    except Exception as e:
        raise HTTPException(401, f"Authentication failed: {str(e)}")

def _require_role(user, allowed: list[str]):
    """Check if user has required role"""
    if user.get("role") not in allowed:
        raise HTTPException(403, "Insufficient permissions")

@router.get("/profile")
async def get_user_profile(user=Depends(_current_user)):
    """
    Get current user's profile.

    Returns the user's profile information including bio, avatar, location, etc.
    """
    try:
        # Get user profile
        profile = await user_profiles_db.find_one({"user_id": user["id"]})

        if not profile:
            # Create default profile
            profile = {
                "_id": _uuid(),
                "user_id": user["id"],
                "bio": "",
                "avatar_url": "",
                "location": "",
                "website": "",
                "social_links": {},
                "skills": [],
                "interests": [],
                "learning_goals": [],
                "preferred_learning_style": "visual",
                "timezone": "UTC",
                "language": "en",
                "notifications_enabled": True,
                "privacy_settings": {
                    "show_profile": True,
                    "show_progress": True,
                    "show_achievements": True,
                    "allow_messages": True
                },
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            await user_profiles_db.insert_one(profile)

            logger.info("Created default user profile", extra={
                "user_id": user["id"],
                "profile_id": profile["_id"]
            })

        return profile

    except Exception as e:
        logger.error("Failed to get user profile", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve user profile")

@router.put("/profile")
async def update_user_profile(profile_data: dict, user=Depends(_current_user)):
    """
    Update current user's profile.

    - **bio**: User's biography
    - **avatar_url**: Profile picture URL
    - **location**: User's location
    - **website**: Personal website URL
    - **social_links**: Social media links
    - **skills**: List of user skills
    - **interests**: Areas of interest
    - **learning_goals**: Learning objectives
    - **preferred_learning_style**: Visual, auditory, kinesthetic, etc.
    - **timezone**: User's timezone
    - **language**: Preferred language
    - **notifications_enabled**: Enable/disable notifications
    - **privacy_settings**: Privacy preferences
    """
    try:
        # Validate and sanitize input
        allowed_fields = [
            "bio", "avatar_url", "location", "website", "social_links",
            "skills", "interests", "learning_goals", "preferred_learning_style",
            "timezone", "language", "notifications_enabled", "privacy_settings"
        ]

        updates = {k: v for k, v in profile_data.items() if k in allowed_fields}
        if not updates:
            raise ValidationError("No valid fields provided for update", "profile_data")

        updates["updated_at"] = datetime.now(timezone.utc)

        # Update profile
        await user_profiles_db.update_one(
            {"user_id": user["id"]},
            {"$set": updates},
            upsert=True
        )

        logger.info("User profile updated", extra={
            "user_id": user["id"],
            "updated_fields": list(updates.keys())
        })

        return {"status": "updated", "message": "Profile updated successfully"}

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.error("Failed to update user profile", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to update user profile")

@router.get("/profile/public/{user_id}")
async def get_public_profile(user_id: str, current_user=Depends(_current_user)):
    """
    Get public profile information for a user.

    - **user_id**: Target user ID
    """
    try:
        # Get user profile
        profile = await user_profiles_db.find_one({"user_id": user_id})

        if not profile:
            raise NotFoundError("User profile", user_id)

        # Check privacy settings
        privacy_settings = profile.get("privacy_settings", {})
        if not privacy_settings.get("show_profile", True):
            raise AuthorizationError("This user's profile is private")

        # Return only public information
        public_profile = {
            "user_id": profile["user_id"],
            "bio": profile.get("bio", ""),
            "avatar_url": profile.get("avatar_url", ""),
            "location": profile.get("location", ""),
            "website": profile.get("website", ""),
            "skills": profile.get("skills", []),
            "interests": profile.get("interests", []),
            "preferred_learning_style": profile.get("preferred_learning_style", "visual"),
            "timezone": profile.get("timezone", "UTC"),
            "language": profile.get("language", "en")
        }

        return public_profile

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get public profile", extra={
            "target_user_id": user_id,
            "requesting_user_id": current_user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve public profile")

@router.get("/profile/stats")
async def get_profile_stats(user=Depends(_current_user)):
    """
    Get statistics about the user's profile completeness.
    """
    try:
        # Get user profile
        profile = await user_profiles_db.find_one({"user_id": user["id"]})

        if not profile:
            return {
                "completeness_score": 0,
                "completed_fields": 0,
                "total_fields": 12,
                "missing_fields": [
                    "bio", "avatar_url", "location", "website",
                    "social_links", "skills", "interests", "learning_goals",
                    "preferred_learning_style", "timezone", "language",
                    "privacy_settings"
                ],
                "message": "Profile not found"
            }

        # Calculate completeness
        fields_to_check = [
            "bio", "avatar_url", "location", "website",
            "social_links", "skills", "interests", "learning_goals",
            "preferred_learning_style", "timezone", "language",
            "privacy_settings"
        ]

        completed_fields = 0
        missing_fields = []

        for field in fields_to_check:
            value = profile.get(field)
            if value is not None and value != "" and value != [] and value != {}:
                completed_fields += 1
            else:
                missing_fields.append(field)

        completeness_score = int((completed_fields / len(fields_to_check)) * 100)

        return {
            "completeness_score": completeness_score,
            "completed_fields": completed_fields,
            "total_fields": len(fields_to_check),
            "missing_fields": missing_fields,
            "profile_quality": "Excellent" if completeness_score > 80 else "Good" if completeness_score > 60 else "Needs Improvement"
        }

    except Exception as e:
        logger.error("Failed to get profile stats", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve profile statistics")

@router.put("/profile/privacy")
async def update_privacy_settings(privacy_data: dict, user=Depends(_current_user)):
    """
    Update privacy settings for the user profile.

    - **show_profile**: Whether profile is publicly visible
    - **show_progress**: Whether learning progress is visible
    - **show_achievements**: Whether achievements are visible
    - **allow_messages**: Whether to allow direct messages
    """
    try:
        # Validate privacy settings
        allowed_privacy_fields = [
            "show_profile", "show_progress", "show_achievements", "allow_messages"
        ]

        privacy_updates = {k: v for k, v in privacy_data.items() if k in allowed_privacy_fields}
        if not privacy_updates:
            raise ValidationError("No valid privacy fields provided", "privacy_data")

        # Update privacy settings
        await user_profiles_db.update_one(
            {"user_id": user["id"]},
            {"$set": {"privacy_settings": privacy_updates, "updated_at": datetime.now(timezone.utc)}},
            upsert=True
        )

        logger.info("Privacy settings updated", extra={
            "user_id": user["id"],
            "updated_privacy_fields": list(privacy_updates.keys())
        })

        return {"status": "updated", "message": "Privacy settings updated successfully"}

    except ValidationError:
        raise
    except Exception as e:
        logger.error("Failed to update privacy settings", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to update privacy settings")