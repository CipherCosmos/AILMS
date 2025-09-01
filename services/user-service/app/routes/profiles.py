"""
User profile management routes for User Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional

from shared.common.auth import get_current_user, require_admin
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

from ..services.user_service import user_service
from ..models import UserProfileUpdate

logger = get_logger("user-service")
router = APIRouter()


@router.get("/profile")
async def get_user_profile(user: dict = Depends(get_current_user)):
    """
    Get current user's profile.

    Returns the user's profile information including bio, avatar, location, etc.
    """
    try:
        profile = await user_service.get_user_profile(user["id"])
        return profile.dict()

    except NotFoundError:
        # Create default profile if not found
        from ..models import UserProfileCreate
        profile_data = UserProfileCreate(user_id=user["id"])
        profile = await user_service.create_user_profile(profile_data)
        return profile.dict()

    except Exception as e:
        logger.error("Failed to get user profile", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve user profile")

@router.put("/profile")
async def update_user_profile(profile_data: UserProfileUpdate, user: dict = Depends(get_current_user)):
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
        updated_profile = await user_service.update_user_profile(user["id"], profile_data)

        logger.info("User profile updated", extra={
            "user_id": user["id"]
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
async def get_public_profile(user_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get public profile information for a user.

    - **user_id**: Target user ID
    """
    try:
        profile = await user_service.get_user_profile(user_id)

        # Check privacy settings
        privacy_settings = profile.privacy_settings or {}
        if not privacy_settings.get("show_profile", True):
            raise AuthorizationError("This user's profile is private")

        # Return only public information
        public_profile = {
            "user_id": profile.user_id,
            "bio": profile.bio,
            "avatar_url": profile.avatar_url,
            "location": profile.location,
            "website": profile.website,
            "skills": profile.skills,
            "interests": profile.interests,
            "preferred_learning_style": profile.preferred_learning_style,
            "timezone": profile.timezone,
            "language": profile.language
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
async def get_profile_stats(user: dict = Depends(get_current_user)):
    """
    Get statistics about the user's profile completeness.
    """
    try:
        from ..utils.user_utils import calculate_profile_completeness

        try:
            profile = await user_service.get_user_profile(user["id"])
            profile_dict = profile.dict()
        except NotFoundError:
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

        return calculate_profile_completeness(profile_dict)

    except Exception as e:
        logger.error("Failed to get profile stats", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve profile statistics")

@router.put("/profile/privacy")
async def update_privacy_settings(privacy_data: dict, user: dict = Depends(get_current_user)):
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

        # Create update object
        from ..models import UserProfileUpdate
        profile_update = UserProfileUpdate(privacy_settings=privacy_updates)

        # Update profile
        await user_service.update_user_profile(user["id"], profile_update)

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