"""
User management routes for Auth Service
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List

from shared.common.auth import get_current_user, require_admin
from shared.common.errors import ValidationError, AuthorizationError, NotFoundError
from shared.common.logging import get_logger
from shared.database.database import get_database, _find_one, _update_one
from shared.models.models import UserPublic

logger = get_logger("auth-service")
router = APIRouter()

async def _current_user(token: str = None):
    """Get current authenticated user"""
    if not token:
        raise HTTPException(401, "No authentication token provided")

    try:
        import jwt
        from shared.config.config import settings

        # Decode and validate JWT token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        # Verify token hasn't expired
        from datetime import datetime, timezone
        if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(401, "Token has expired")

        # Get user from database
        db = get_database()
        user = await db.users.find_one({"_id": payload.get("sub")})
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

@router.get("/users", response_model=List[UserPublic])
async def list_users(user=Depends(_current_user)):
    """
    List all users (admin only).

    Returns a list of all registered users with their basic information.
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "super_admin"])

        db = get_database()
        docs = await db.users.find({}).sort("created_at", -1).to_list(1000)

        users = [UserPublic(id=d["_id"], email=d["email"], name=d["name"], role=d["role"]) for d in docs]

        logger.info("Users list retrieved", extra={
            "requested_by": user["id"],
            "total_users": len(users)
        })

        return users

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to list users", extra={
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve users")

@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user(user_id: str, user=Depends(_current_user)):
    """
    Get a specific user by ID.

    - **user_id**: The ID of the user to retrieve
    """
    try:
        # Check permissions (admin or self)
        if user["id"] != user_id and user["role"] not in ["admin", "super_admin"]:
            raise AuthorizationError("Not authorized to view this user")

        # Get user from database
        db = get_database()
        user_doc = await db.users.find_one({"_id": user_id})
        if not user_doc:
            raise NotFoundError("User not found", "user_id")

        result = UserPublic(
            id=user_doc["_id"],
            email=user_doc["email"],
            name=user_doc["name"],
            role=user_doc["role"]
        )

        logger.info("User retrieved", extra={
            "target_user_id": user_id,
            "requested_by": user["id"]
        })

        return result

    except (AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        logger.error("Failed to get user", extra={
            "target_user_id": user_id,
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve user")

@router.put("/users/{user_id}", response_model=UserPublic)
async def update_user(user_id: str, body: dict, user=Depends(_current_user)):
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
        _require_role(user, ["admin", "super_admin"])

        # Get existing user
        db = get_database()
        existing_user = await db.users.find_one({"_id": user_id})
        if not existing_user:
            raise NotFoundError("User not found", "user_id")

        updates = {}

        # Validate and prepare updates
        if "name" in body and body["name"] is not None:
            updates["name"] = body["name"]

        if "email" in body and body["email"] is not None:
            # Basic email validation
            if "@" not in body["email"] or "." not in body["email"]:
                raise ValidationError("Invalid email format", "email")

            # Check if email is already taken by another user
            existing_email = await db.users.find_one({
                "email": str(body["email"]).lower(),
                "_id": {"$ne": user_id}
            })
            if existing_email:
                raise ValidationError("Email already taken", "email")

            updates["email"] = str(body["email"]).lower()

        if "password" in body and body["password"] is not None:
            from passlib.hash import bcrypt
            updates["password_hash"] = bcrypt.hash(body["password"])

        if "role" in body and body["role"] is not None:
            # Validate role
            valid_roles = [
                "super_admin", "org_admin", "dept_admin",
                "instructor", "teaching_assistant", "content_author",
                "student", "auditor", "parent_guardian", "proctor", "support_moderator"
            ]
            if body["role"] not in valid_roles:
                raise ValidationError("Invalid role", "role")

            updates["role"] = body["role"]

        if not updates:
            raise ValidationError("No valid updates provided", "updates")

        # Apply updates
        await _update_one("users", {"_id": user_id}, updates)

        # Get updated user
        updated_user = await db.users.find_one({"_id": user_id})

        result = UserPublic(
            id=updated_user["_id"],
            email=updated_user["email"],
            name=updated_user["name"],
            role=updated_user["role"]
        )

        logger.info("User updated", extra={
            "target_user_id": user_id,
            "updated_by": user["id"],
            "updated_fields": list(updates.keys())
        })

        return result

    except (ValidationError, AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        logger.error("Failed to update user", extra={
            "target_user_id": user_id,
            "updated_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to update user")

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, user=Depends(_current_user)):
    """
    Delete a user (admin only).

    - **user_id**: The ID of the user to delete
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "super_admin"])

        # Prevent self-deletion
        if user_id == user["id"]:
            raise AuthorizationError("Cannot delete yourself")

        # Get user to verify existence
        db = get_database()
        existing_user = await db.users.find_one({"_id": user_id})
        if not existing_user:
            raise NotFoundError("User not found", "user_id")

        # Delete user
        result = await db.users.delete_one({"_id": user_id})
        if result.deleted_count == 0:
            raise NotFoundError("User not found", "user_id")

        logger.info("User deleted", extra={
            "target_user_id": user_id,
            "deleted_by": user["id"],
            "user_email": existing_user.get("email", "unknown")
        })

        return {"status": "deleted", "user_id": user_id}

    except (AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        logger.error("Failed to delete user", extra={
            "target_user_id": user_id,
            "deleted_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to delete user")

@router.get("/users/search")
async def search_users(
    query: str = "",
    role: str = None,
    limit: int = 50,
    user=Depends(_current_user)
):
    """
    Search users by name or email (admin only).

    - **query**: Search query (name or email)
    - **role**: Filter by role (optional)
    - **limit**: Maximum number of results (default: 50)
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "super_admin"])

        db = get_database()

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

        users = [UserPublic(id=d["_id"], email=d["email"], name=d["name"], role=d["role"]) for d in docs]

        logger.info("User search completed", extra={
            "query": query,
            "role_filter": role,
            "results_count": len(users),
            "requested_by": user["id"]
        })

        return {
            "users": users,
            "total": len(users),
            "query": query,
            "role_filter": role
        }

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("User search failed", extra={
            "query": query,
            "role_filter": role,
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "User search failed")

@router.get("/users/stats")
async def get_user_stats(user=Depends(_current_user)):
    """
    Get user statistics (admin only).
    """
    try:
        # Check permissions
        _require_role(user, ["admin", "super_admin"])

        db = get_database()

        # Get user statistics
        total_users = await db.users.count_documents({})

        # Count users by role
        role_stats = {}
        pipeline = [
            {"$group": {"_id": "$role", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        role_results = await db.users.aggregate(pipeline).to_list(None)

        for result in role_results:
            role_stats[result["_id"]] = result["count"]

        stats = {
            "total_users": total_users,
            "users_by_role": role_stats,
            "active_users": total_users,  # Would need to track active users
            "new_users_today": 0,  # Would need to track creation dates
            "timestamp": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow()
        }

        logger.info("User stats retrieved", extra={
            "total_users": total_users,
            "requested_by": user["id"]
        })

        return stats

    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Failed to get user stats", extra={
            "requested_by": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve user statistics")