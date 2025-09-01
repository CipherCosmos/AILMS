"""
Authentication routes for Auth Service
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.hash import bcrypt
import jwt
from typing import Dict, Any

from shared.config.config import settings
from shared.common.auth import get_current_user, require_admin
from shared.common.errors import ValidationError, AuthorizationError
from shared.common.logging import get_logger
from shared.database import get_database, DatabaseOperations
from shared.models.models import (
    UserPublic,
    TokenPair,
    LoginRequest,
    RefreshRequest,
    UserCreate,
    UserBase,
)

logger = get_logger("auth-service")
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Initialize database operations
users_db = DatabaseOperations("users")

async def _create_tokens(user: Dict[str, Any]) -> TokenPair:
    """Create access and refresh tokens"""
    now = datetime.now(timezone.utc)
    access = jwt.encode(
        {
            "sub": user["id"],
            "role": user["role"],
            "exp": now + timedelta(minutes=settings.access_expire_min),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    refresh = jwt.encode(
        {
            "sub": user["id"],
            "type": "refresh",
            "exp": now + timedelta(days=settings.refresh_expire_days),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    return TokenPair(access_token=access, refresh_token=refresh)

async def _current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Get current authenticated user"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(401, "Invalid token payload")
    user = await users_db.find_one({"_id": uid})
    if not user:
        raise HTTPException(401, "User not found")
    return user

def _require_role(user: Dict[str, Any], allowed: list[str]):
    """Check if user has required role"""
    if user.get("role") not in allowed:
        raise HTTPException(403, "Insufficient permissions")

@router.post("/register", response_model=UserPublic)
async def register(body: UserCreate):
    """
    Register a new user.

    - **email**: User's email address
    - **name**: User's full name
    - **password**: User's password
    - **role**: User's role (optional, defaults to student)
    """
    try:
        # Check if email already exists
        existing = await users_db.find_one({"email": str(body.email).lower()})
        if existing:
            raise ValidationError("Email already registered", "email")

        role = body.role or "student"

        # Bootstrap: allow first user to be super_admin if db empty
        users_count = await users_db.count_documents({})
        if role == "super_admin" and users_count > 0:
            raise AuthorizationError("Cannot self-assign super_admin role")
        if users_count == 0 and role != "super_admin":
            role = "super_admin"

        # Create user
        user = UserBase(email=str(body.email).lower(), name=body.name, role=role)
        doc = user.dict()
        doc["password_hash"] = bcrypt.hash(body.password)
        doc["_id"] = user.id

        await users_db.insert_one(doc)

        logger.info("User registered successfully", extra={
            "user_id": user.id,
            "email": user.email,
            "role": user.role
        })

        return UserPublic(id=user.id, email=user.email, name=user.name, role=user.role)

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("User registration failed", extra={
            "email": body.email,
            "error": str(e)
        })
        raise HTTPException(500, "Registration failed")

@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest):
    """
    Authenticate user and return tokens.

    - **email**: User's email address
    - **password**: User's password
    """
    try:
        # Find user by email
        user = await users_db.find_one({"email": str(body.email).lower()})
        if not user or not bcrypt.verify(body.password, user.get("password_hash", "")):
            raise AuthorizationError("Invalid credentials")

        # Create tokens
        tokens = await _create_tokens(user)

        logger.info("User login successful", extra={
            "user_id": user["id"],
            "email": user["email"],
            "role": user["role"]
        })

        return tokens

    except AuthorizationError:
        logger.warning("Login failed - invalid credentials", extra={
            "email": body.email
        })
        raise
    except Exception as e:
        logger.error("Login failed", extra={
            "email": body.email,
            "error": str(e)
        })
        raise HTTPException(500, "Login failed")

@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest):
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token
    """
    try:
        # Decode and validate refresh token
        payload = jwt.decode(
            body.refresh_token, settings.jwt_secret, algorithms=["HS256"]
        )

        if payload.get("type") != "refresh":
            raise AuthorizationError("Invalid refresh token type")

        # Get user
        user = await users_db.find_one({"_id": payload.get("sub")})
        if not user:
            raise AuthorizationError("User not found")

        # Create new tokens
        tokens = await _create_tokens(user)

        logger.info("Token refresh successful", extra={
            "user_id": user["_id"]
        })

        return tokens

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise AuthorizationError("Invalid or expired refresh token")
    except AuthorizationError:
        raise
    except Exception as e:
        logger.error("Token refresh failed", extra={"error": str(e)})
        raise HTTPException(500, "Token refresh failed")

@router.get("/me", response_model=UserPublic)
async def me(user=Depends(_current_user)):
    """
    Get current user profile information.
    """
    try:
        return UserPublic(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"]
        )

    except Exception as e:
        logger.error("Failed to get user profile", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to get user profile")

@router.put("/me", response_model=UserPublic)
async def update_me(body: dict, user=Depends(_current_user)):
    """
    Update current user profile.

    - **name**: New name (optional)
    - **email**: New email (optional)
    - **password**: New password (optional)
    """
    try:
        updates = {}

        # Validate and prepare updates
        if "name" in body and body["name"] is not None:
            updates["name"] = body["name"]

        if "email" in body and body["email"] is not None and body["email"] != user["email"]:
            # Basic email validation
            if "@" not in body["email"] or "." not in body["email"]:
                raise ValidationError("Invalid email format", "email")

            # Check if email is already taken
            existing = await users_db.find_one({"email": str(body["email"]).lower()})
            if existing:
                raise ValidationError("Email already taken", "email")

            updates["email"] = str(body["email"]).lower()

        if "password" in body and body["password"] is not None:
            updates["password_hash"] = bcrypt.hash(body["password"])

        if updates:
            await users_db.update_one({"_id": user["id"]}, updates)
            user.update(updates)

        logger.info("User profile updated", extra={
            "user_id": user["id"],
            "updated_fields": list(updates.keys())
        })

        return UserPublic(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"]
        )

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("User profile update failed", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Profile update failed")

@router.post("/logout")
async def logout(user=Depends(_current_user)):
    """
    Logout user (client should discard tokens).
    In a production system, you might want to implement token blacklisting.
    """
    try:
        logger.info("User logout", extra={
            "user_id": user["id"]
        })

        return {"status": "logged_out", "message": "Successfully logged out"}

    except Exception as e:
        logger.error("Logout failed", extra={
            "user_id": user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Logout failed")