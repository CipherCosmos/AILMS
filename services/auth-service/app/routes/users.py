"""
User management routes for Auth Service
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional

from shared.common.logging import get_logger
from shared.common.errors import ValidationError, AuthenticationError
from ..services.auth_service import AuthService
from ..database import auth_db
from ..models import UserPublic, UserPrivate, UserUpdate

logger = get_logger("auth-service")
router = APIRouter()

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from service"""
    return await AuthService.get_current_user(credentials.credentials)

def require_role(user: UserPrivate, allowed: list[str]):
    """Check if user has required role"""
    return AuthService.validate_token_permissions(user, allowed)

@router.get("/users", response_model=List[UserPublic])
async def list_users(user: UserPrivate = Depends(get_current_user)):
    """
    List all users (admin only).

    Returns a list of all registered users with their basic information.
    """
    try:
        # Check permissions
        if not require_role(user, ["admin", "super_admin"]):
            raise AuthenticationError("Admin access required")

        # Get all users from database
        db = await auth_db.get_db()
        docs = await db.users.find({}).sort("created_at", -1).to_list(1000)

        users = [UserPublic(id=str(d["_id"]), email=d["email"], name=d["name"], role=d["role"]) for d in docs]

        logger.info("Users list retrieved", extra={
            "requested_by": user.id,
            "total_users": len(users)
        })

        return users

    except AuthenticationError:
        raise HTTPException(403, "Admin access required")
    except Exception as e:
        logger.error("Failed to list users", extra={
            "requested_by": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve users")

@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user(user_id: str, user: UserPrivate = Depends(get_current_user)):
    """
    Get a specific user by ID.

    - **user_id**: The ID of the user to retrieve
    """
    try:
        # Check permissions (admin or self)
        if user.id != user_id and not require_role(user, ["admin", "super_admin"]):
            raise AuthenticationError("Not authorized to view this user")

        # Get user from database
        db = await auth_db.get_db()
        user_doc = await db.users.find_one({"_id": user_id})
        if not user_doc:
            raise HTTPException(404, "User not found")

        result = UserPublic(
            id=str(user_doc["_id"]),
            email=user_doc["email"],
            name=user_doc["name"],
            role=user_doc["role"]
        )

        logger.info("User retrieved", extra={
            "target_user_id": user_id,
            "requested_by": user.id
        })

        return result

    except AuthenticationError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error("Failed to get user", extra={
            "target_user_id": user_id,
            "requested_by": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve user")

@router.put("/users/{user_id}", response_model=UserPublic)
async def update_user(user_id: str, body: UserUpdate, user: UserPrivate = Depends(get_current_user)):
    """
    Update a user (admin only).

    - **user_id**: The ID of the user to update
    - **name**: New name (optional)
    - **email**: New email (optional)
    - **password**: New password (optional)
    - **role**: New role (optional)
    """
    try:
        # Check permissions
        if not require_role(user, ["admin", "super_admin"]):
            raise AuthenticationError("Admin access required")

        # Use the service to update user
        return await AuthService.update_user_profile(user_id, body)

    except AuthenticationError as e:
        raise HTTPException(403, str(e))
    except ValidationError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("Failed to update user", extra={
            "target_user_id": user_id,
            "updated_by": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to update user")

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: UserPrivate = Depends(get_current_user)):
    """
    Delete a user (admin only).

    - **user_id**: The ID of the user to delete
    """
    try:
        # Check permissions
        if not require_role(user, ["admin", "super_admin"]):
            raise AuthenticationError("Admin access required")

        # Prevent self-deletion
        if user_id == user.id:
            raise AuthenticationError("Cannot delete yourself")

        # Delete user
        success = await auth_db.delete_user(user_id)
        if not success:
            raise HTTPException(404, "User not found")

        logger.info("User deleted", extra={
            "target_user_id": user_id,
            "deleted_by": user.id
        })

        return {"status": "deleted", "user_id": user_id}

    except AuthenticationError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error("Failed to delete user", extra={
            "target_user_id": user_id,
            "deleted_by": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to delete user")

@router.get("/users/search")
async def search_users(
    query: str = "",
    role: Optional[str] = None,
    limit: int = 50,
    user: UserPrivate = Depends(get_current_user)
):
    """
    Search users by name or email (admin only).

    - **query**: Search query (name or email)
    - **role**: Filter by role (optional)
    - **limit**: Maximum number of results (default: 50)
    """
    try:
        # Check permissions
        if not require_role(user, ["admin", "super_admin"]):
            raise AuthenticationError("Admin access required")

        db = await auth_db.get_db()

        # Build search query
        search_query = {}
        if query:
            search_query["$or"] = [
                {"name": {"$regex": query, "$options": "i"}},
                {"email": {"$regex": query, "$options": "i"}}
            ]

        if role:
            search_query["role"] = role

        # Search users
        docs = await db.users.find(search_query).sort("name", 1).to_list(limit)

        users = [UserPublic(id=str(d["_id"]), email=d["email"], name=d["name"], role=d["role"]) for d in docs]

        logger.info("User search completed", extra={
            "query": query,
            "role_filter": role,
            "results_count": len(users),
            "requested_by": user.id
        })

        return {
            "users": users,
            "total": len(users),
            "query": query,
            "role_filter": role
        }

    except AuthenticationError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error("User search failed", extra={
            "query": query,
            "role_filter": role,
            "requested_by": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "User search failed")

@router.get("/users/stats")
async def get_user_stats(user: UserPrivate = Depends(get_current_user)):
    """
    Get user statistics (admin only).
    """
    try:
        # Check permissions
        if not require_role(user, ["admin", "super_admin"]):
            raise AuthenticationError("Admin access required")

        # Get basic metrics from service
        metrics = await AuthService.get_auth_metrics()

        logger.info("User stats retrieved", extra={
            "requested_by": user.id
        })

        return metrics

    except AuthenticationError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error("Failed to get user stats", extra={
            "requested_by": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve user statistics")