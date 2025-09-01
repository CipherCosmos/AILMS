"""
Authentication routes for Auth Service
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional

from shared.common.logging import get_logger
from shared.common.errors import ValidationError, AuthenticationError
from ..services.auth_service import AuthService
from ..models import (
    UserPublic,
    UserPrivate,
    TokenPair,
    LoginRequest,
    RefreshRequest,
    UserCreate,
    UserUpdate,
    AccountLockInfo
)

logger = get_logger("auth-service")
router = APIRouter()

# Service instance
auth_service = AuthService()

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from service"""
    return await AuthService.get_current_user(credentials.credentials)

def require_role(user, allowed: list[str]):
    """Check if user has required role"""
    return AuthService.validate_token_permissions(user, allowed)

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
        return await AuthService.register_user(body)
    except ValidationError as e:
        logger.warning("Registration validation failed", extra={
            "email": body.email,
            "error": str(e)
        })
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("User registration failed", extra={
            "email": body.email,
            "error": str(e)
        })
        raise HTTPException(500, "Registration failed")

@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, request: Request):
    """
    Authenticate user and return tokens.

    - **email**: User's email address
    - **password**: User's password
    """
    try:
        # Extract client info for logging
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")

        return await AuthService.authenticate_user(body, ip_address, user_agent)
    except AuthenticationError as e:
        logger.warning("Login failed", extra={
            "email": body.email,
            "error": str(e)
        })
        raise HTTPException(401, str(e))
    except Exception as e:
        logger.error("Login failed", extra={
            "email": body.email,
            "error": str(e)
        })
        raise HTTPException(500, "Login failed")

@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, request: Request):
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token
    """
    try:
        ip_address = request.client.host if request.client else None
        return await AuthService.refresh_access_token(body.refresh_token, ip_address)
    except AuthenticationError as e:
        logger.warning("Token refresh failed", extra={"error": str(e)})
        raise HTTPException(401, str(e))
    except Exception as e:
        logger.error("Token refresh failed", extra={"error": str(e)})
        raise HTTPException(500, "Token refresh failed")

@router.get("/me", response_model=UserPublic)
async def me(user: UserPrivate = Depends(get_current_user)):
    """
    Get current user profile information.
    """
    try:
        return UserPublic(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role
        )
    except Exception as e:
        logger.error("Failed to get user profile", extra={
            "user_id": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to get user profile")

@router.put("/me", response_model=UserPublic)
async def update_me(body: UserUpdate, user: UserPrivate = Depends(get_current_user)):
    """
    Update current user profile.

    - **name**: New name (optional)
    - **email**: New email (optional)
    - **password**: New password (optional)
    """
    try:
        return await AuthService.update_user_profile(user.id, body)
    except ValidationError as e:
        logger.warning("Profile update validation failed", extra={
            "user_id": user.id,
            "error": str(e)
        })
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("User profile update failed", extra={
            "user_id": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Profile update failed")

@router.post("/logout")
async def logout(user: UserPrivate = Depends(get_current_user)):
    """
    Logout user (client should discard tokens).
    In a production system, you might want to implement token blacklisting.
    """
    try:
        # For logout, we don't need to do anything special with the token
        # The client should discard the tokens
        logger.info("User logout", extra={"user_id": user.id})
        return {"status": "logged_out", "message": "Successfully logged out"}
    except Exception as e:
        logger.error("Logout failed", extra={
            "user_id": user.id,
            "error": str(e)
        })
        raise HTTPException(500, "Logout failed")

@router.get("/account-status")
async def get_account_status(email: str):
    """
    Get account lock status for an email.
    Useful for login forms to show appropriate messages.
    """
    try:
        status = await AuthService.get_account_lock_info(email)
        return {
            "email": email,
            "is_locked": status.is_locked,
            "attempts_remaining": status.attempts_remaining,
            "locked_until": status.locked_until.isoformat() if status.locked_until else None
        }
    except Exception as e:
        logger.error("Failed to get account status", extra={
            "email": email,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to get account status")