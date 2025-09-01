"""
Auth Service Business Logic
"""
import jwt
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from passlib.hash import bcrypt

from shared.common.logging import get_logger
from shared.common.cache import cache_manager
from shared.common.monitoring import metrics_collector
# Import error classes (will be implemented)
from typing import Optional

class AuthenticationError(Exception):
    def __init__(self, message: str, error_code: str = "AUTH_ERROR", details: Optional[dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(Exception):
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR", details: Optional[dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
from shared.config.config import settings

from ..config import auth_settings, JWT_ALGORITHM, JWT_ACCESS_EXPIRE_MINUTES, JWT_REFRESH_EXPIRE_DAYS
from ..database import auth_db
from ..models import (
    UserCreate, UserUpdate, LoginRequest, TokenPair,
    UserPublic, UserPrivate, AccountLockInfo
)

logger = get_logger("auth-service")


class AuthService:
    """Authentication service business logic"""

    @staticmethod
    async def register_user(user_data: UserCreate) -> UserPublic:
        """Register a new user"""
        try:
            # Hash password
            hashed_password = bcrypt.hash(user_data.password)

            # Prepare user data
            user_dict = user_data.dict()
            user_dict["password_hash"] = hashed_password
            user_dict.pop("password")  # Remove plain password

            # Create user
            created_user = await auth_db.create_user(user_dict)

            # Log audit event
            await auth_db.log_audit_event(
                "user_registered",
                created_user["_id"],
                {"email": created_user["email"], "role": created_user["role"]}
            )

            # Update metrics
            await metrics_collector.increment_counter("users_registered")

            # Convert to public model
            return UserPublic(
                id=created_user["_id"],
                email=created_user["email"],
                name=created_user["name"],
                role=created_user["role"]
            )

        except Exception as e:
            logger.error("User registration failed", extra={"error": str(e), "email": user_data.email})
            raise ValidationError(
                error_code="REGISTRATION_FAILED",
                message="Failed to register user",
                details={"original_error": str(e)}
            )

    @staticmethod
    async def authenticate_user(login_data: LoginRequest, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> TokenPair:
        """Authenticate user and return tokens"""
        try:
            # Get user by email
            user = await auth_db.get_user_by_email(login_data.email)
            if not user:
                # Record failed attempt for unknown email
                await auth_db.record_login_attempt(login_data.email, False)
                await metrics_collector.increment_counter("login_attempts", tags={"result": "user_not_found"})
                raise AuthenticationError(
                    error_code="INVALID_CREDENTIALS",
                    message="Invalid email or password"
                )

            # Check if account is locked
            if await auth_db.is_account_locked(user["_id"]):
                lock_info = await auth_db.record_login_attempt(login_data.email, False)
                await metrics_collector.increment_counter("login_attempts", tags={"result": "account_locked"})
                raise AuthenticationError(
                    error_code="ACCOUNT_LOCKED",
                    message="Account is temporarily locked due to too many failed login attempts",
                    details={
                        "locked_until": lock_info["locked_until"],
                        "attempts_remaining": lock_info["attempts_remaining"]
                    }
                )

            # Verify password
            if not bcrypt.verify(login_data.password, user.get("password_hash", "")):
                # Record failed attempt
                lock_info = await auth_db.record_login_attempt(login_data.email, False)
                await metrics_collector.increment_counter("login_attempts", tags={"result": "invalid_password"})

                if lock_info["locked"]:
                    raise AuthenticationError(
                        error_code="ACCOUNT_LOCKED",
                        message="Account is temporarily locked due to too many failed login attempts",
                        details={
                            "locked_until": lock_info["locked_until"],
                            "attempts_remaining": lock_info["attempts_remaining"]
                        }
                    )
                else:
                    raise AuthenticationError(
                        error_code="INVALID_CREDENTIALS",
                        message="Invalid email or password"
                    )

            # Successful login
            await auth_db.record_login_attempt(login_data.email, True)

            # Update last login
            await auth_db.update_user(user["_id"], {"last_login": datetime.now(timezone.utc)})

            # Create session
            session_id = await auth_db.create_session(
                user["_id"],
                user_agent=user_agent,
                ip_address=ip_address
            )

            # Generate tokens
            tokens = await AuthService._create_tokens(user, session_id)

            # Log audit event
            await auth_db.log_audit_event(
                "user_login",
                user["_id"],
                {
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "session_id": session_id
                }
            )

            # Update metrics
            await metrics_collector.increment_counter("login_attempts", tags={"result": "success"})

            return tokens

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Authentication failed", extra={
                "error": str(e),
                "email": login_data.email,
                "ip_address": ip_address
            })
            await metrics_collector.increment_counter("login_attempts", tags={"result": "error"})
            raise AuthenticationError(
                error_code="AUTHENTICATION_ERROR",
                message="Authentication failed due to system error"
            )

    @staticmethod
    async def refresh_access_token(refresh_token: str, ip_address: Optional[str] = None) -> TokenPair:
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            payload = jwt.decode(refresh_token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])

            if payload.get("type") != "refresh":
                raise AuthenticationError(
                    error_code="INVALID_TOKEN_TYPE",
                    message="Invalid token type"
                )

            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError(
                    error_code="INVALID_TOKEN",
                    message="Invalid token payload"
                )

            # Get user
            user = await auth_db.get_user_by_id(user_id)
            if not user:
                raise AuthenticationError(
                    error_code="USER_NOT_FOUND",
                    message="User not found"
                )

            # Check if account is locked
            if await auth_db.is_account_locked(user_id):
                raise AuthenticationError(
                    error_code="ACCOUNT_LOCKED",
                    message="Account is locked"
                )

            # Generate new tokens
            tokens = await AuthService._create_tokens(user)

            # Log audit event
            await auth_db.log_audit_event(
                "token_refresh",
                user_id,
                {"ip_address": ip_address}
            )

            # Update metrics
            await metrics_collector.increment_counter("token_refreshes")

            return tokens

        except jwt.ExpiredSignatureError:
            raise AuthenticationError(
                error_code="TOKEN_EXPIRED",
                message="Refresh token has expired"
            )
        except jwt.InvalidTokenError:
            raise AuthenticationError(
                error_code="INVALID_TOKEN",
                message="Invalid refresh token"
            )
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Token refresh failed", extra={"error": str(e), "ip_address": ip_address})
            raise AuthenticationError(
                error_code="TOKEN_REFRESH_ERROR",
                message="Failed to refresh token"
            )

    @staticmethod
    async def get_current_user(token: str) -> UserPrivate:
        """Get current authenticated user from token"""
        try:
            # Decode token
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])

            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError(
                    error_code="INVALID_TOKEN",
                    message="Invalid token payload"
                )

            # Get user
            user = await auth_db.get_user_by_id(user_id)
            if not user:
                raise AuthenticationError(
                    error_code="USER_NOT_FOUND",
                    message="User not found"
                )

            # Update session activity if session tracking is enabled
            session_id = payload.get("session_id")
            if session_id and auth_settings.enable_session_tracking:
                await auth_db.update_session_activity(session_id)

            # Convert to private model
            return UserPrivate(
                id=user["_id"],
                email=user["email"],
                name=user["name"],
                role=user["role"],
                is_active=user.get("is_active", True),
                created_at=user["created_at"],
                updated_at=user["updated_at"],
                last_login=user.get("last_login"),
                login_attempts=user.get("login_attempts", 0),
                locked_until=user.get("locked_until")
            )

        except jwt.ExpiredSignatureError:
            raise AuthenticationError(
                error_code="TOKEN_EXPIRED",
                message="Access token has expired"
            )
        except jwt.InvalidTokenError:
            raise AuthenticationError(
                error_code="INVALID_TOKEN",
                message="Invalid access token"
            )
        except Exception as e:
            logger.error("Failed to get current user", extra={"error": str(e)})
            raise AuthenticationError(
                error_code="USER_RETRIEVAL_ERROR",
                message="Failed to retrieve user information"
            )

    @staticmethod
    async def update_user_profile(user_id: str, updates: UserUpdate) -> UserPublic:
        """Update user profile"""
        try:
            # Validate current user has permission
            current_user = await auth_db.get_user_by_id(user_id)
            if not current_user:
                raise ValidationError(
                    error_code="USER_NOT_FOUND",
                    message="User not found"
                )

            # Prepare update data
            update_data = {}
            if updates.name is not None:
                update_data["name"] = updates.name
            if updates.email is not None:
                # Check if email is already taken
                existing = await auth_db.get_user_by_email(updates.email)
                if existing and existing["_id"] != user_id:
                    raise ValidationError(
                        error_code="EMAIL_TAKEN",
                        message="Email address is already in use"
                    )
                update_data["email"] = updates.email
            if updates.password is not None:
                update_data["password_hash"] = bcrypt.hash(updates.password)
            if updates.role is not None:
                # Only admins can change roles
                # This would be checked by the route handler
                update_data["role"] = updates.role

            # Update user
            success = await auth_db.update_user(user_id, update_data)
            if not success:
                raise ValidationError(
                    error_code="UPDATE_FAILED",
                    message="Failed to update user profile"
                )

            # Get updated user
            updated_user = await auth_db.get_user_by_id(user_id)
            if not updated_user:
                raise ValidationError(
                    error_code="USER_NOT_FOUND",
                    message="User not found after update"
                )

            # Log audit event
            await auth_db.log_audit_event(
                "user_profile_updated",
                user_id,
                {"updated_fields": list(update_data.keys())}
            )

            return UserPublic(
                id=updated_user["_id"],
                email=updated_user["email"],
                name=updated_user["name"],
                role=updated_user["role"]
            )

        except ValidationError:
            raise
        except Exception as e:
            logger.error("Profile update failed", extra={"error": str(e), "user_id": user_id})
            raise ValidationError(
                error_code="PROFILE_UPDATE_ERROR",
                message="Failed to update user profile"
            )

    @staticmethod
    async def logout_user(token: str):
        """Logout user by invalidating session"""
        try:
            # Decode token to get session info
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
            session_id = payload.get("session_id")

            if session_id and auth_settings.enable_session_tracking:
                await auth_db.invalidate_session(session_id)

            user_id = payload.get("sub")
            if user_id:
                await auth_db.log_audit_event("user_logout", user_id)

            await metrics_collector.increment_counter("user_logouts")

        except Exception as e:
            logger.warning("Logout processing failed", extra={"error": str(e)})

    @staticmethod
    async def get_account_lock_info(email: str) -> AccountLockInfo:
        """Get account lock information"""
        user = await auth_db.get_user_by_email(email)
        if not user:
            return AccountLockInfo(
                is_locked=False,
                attempts_remaining=auth_settings.max_login_attempts
            )

        lock_info = await auth_db.record_login_attempt(email, False)  # This doesn't count as an actual attempt

        return AccountLockInfo(
            is_locked=lock_info["locked"],
            attempts_remaining=lock_info["attempts_remaining"],
            locked_until=lock_info["locked_until"]
        )

    @staticmethod
    async def _create_tokens(user: Dict[str, Any], session_id: Optional[str] = None) -> TokenPair:
        """Create access and refresh tokens"""
        now = datetime.now(timezone.utc)

        # Create access token
        access_payload = {
            "sub": user["_id"],
            "role": user["role"],
            "type": "access",
            "exp": now + timedelta(minutes=JWT_ACCESS_EXPIRE_MINUTES),
            "iat": now,
            "iss": "lms-auth-service"
        }

        if session_id:
            access_payload["session_id"] = session_id

        access_token = jwt.encode(access_payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)

        # Create refresh token
        refresh_payload = {
            "sub": user["_id"],
            "type": "refresh",
            "exp": now + timedelta(days=JWT_REFRESH_EXPIRE_DAYS),
            "iat": now,
            "iss": "lms-auth-service"
        }

        refresh_token = jwt.encode(refresh_payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=JWT_ACCESS_EXPIRE_MINUTES * 60
        )

    @staticmethod
    async def validate_token_permissions(user: UserPrivate, required_roles: Optional[list] = None) -> bool:
        """Validate user has required permissions"""
        if not required_roles:
            return True

        return user.role in required_roles

    @staticmethod
    async def get_auth_metrics() -> Dict[str, Any]:
        """Get authentication metrics"""
        # This would aggregate metrics from the database
        # For now, return basic structure
        return {
            "total_users": 0,  # Would be calculated from DB
            "active_users_today": 0,
            "login_attempts_today": 0,
            "failed_login_attempts_today": 0,
            "locked_accounts": 0,
            "password_resets_today": 0,
            "average_session_duration": 0.0
        }