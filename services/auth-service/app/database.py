"""
Auth Service Database Operations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from shared.common.database import get_database
from shared.common.logging import get_logger
from shared.common.cache import cache_manager
from .config import auth_settings

logger = get_logger("auth-service-db")


class AuthDatabase:
    """Database operations for authentication service"""

    def __init__(self):
        self.db = None

    async def get_db(self):
        """Get database instance"""
        if self.db is None:
            self.db = await get_database()
        return self.db

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        db = await self.get_db()

        # Check if user already exists
        existing = await db.users.find_one({"email": user_data["email"]})
        if existing:
            raise ValueError("User with this email already exists")

        # Add timestamps
        user_data["created_at"] = datetime.now(timezone.utc)
        user_data["updated_at"] = datetime.now(timezone.utc)
        user_data["is_active"] = True
        user_data["login_attempts"] = 0
        user_data["last_login_attempt"] = None
        user_data["locked_until"] = None

        result = await db.users.insert_one(user_data)
        user_data["_id"] = result.inserted_id

        # Cache user data
        await cache_manager.set(f"user:{user_data['_id']}", user_data, ttl=3600)

        logger.info("User created", extra={"user_id": str(user_data["_id"]), "email": user_data["email"]})
        return user_data

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        # Try cache first
        cache_key = f"user:email:{email}"
        cached_user = await cache_manager.get(cache_key)
        if cached_user:
            return cached_user

        # Query database
        db = await self.get_db()
        user = await db.users.find_one({"email": email})

        # Cache result
        if user:
            await cache_manager.set(cache_key, user, ttl=3600)
            await cache_manager.set(f"user:{user['_id']}", user, ttl=3600)

        return user

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        # Try cache first
        cache_key = f"user:{user_id}"
        cached_user = await cache_manager.get(cache_key)
        if cached_user:
            return cached_user

        # Query database
        db = await self.get_db()
        user = await db.users.find_one({"_id": user_id})

        # Cache result
        if user:
            await cache_manager.set(cache_key, user, ttl=3600)
            await cache_manager.set(f"user:email:{user['email']}", user, ttl=3600)

        return user

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user data"""
        updates["updated_at"] = datetime.now(timezone.utc)

        db = await self.get_db()
        result = await db.users.update_one({"_id": user_id}, {"$set": updates})
        success = result.modified_count > 0

        if success:
            # Invalidate cache
            await cache_manager.invalidate_pattern(f"user:{user_id}")
            user = await self.get_user_by_id(user_id)
            if user:
                await cache_manager.invalidate_pattern(f"user:email:{user['email']}")

        return success

    async def delete_user(self, user_id: str) -> bool:
        """Delete user"""
        db = await self.get_db()
        result = await db.users.delete_one({"_id": user_id})

        if result.deleted_count > 0:
            # Invalidate cache
            await cache_manager.invalidate_pattern(f"user:{user_id}")
            logger.info("User deleted", extra={"user_id": user_id})
            return True

        return False

    async def record_login_attempt(self, email: str, success: bool) -> Dict[str, Any]:
        """Record login attempt and handle account lockout"""
        user = await self.get_user_by_email(email)
        if not user:
            return {"locked": False, "attempts_remaining": auth_settings.max_login_attempts}

        updates = {}

        if success:
            # Successful login
            updates["login_attempts"] = 0
            updates["last_login_attempt"] = None
            updates["locked_until"] = None
            updates["last_login"] = datetime.now(timezone.utc)
        else:
            # Failed login
            attempts = user.get("login_attempts", 0) + 1
            updates["login_attempts"] = attempts
            updates["last_login_attempt"] = datetime.now(timezone.utc)

            # Check if account should be locked
            if auth_settings.enable_account_lockout and attempts >= auth_settings.max_login_attempts:
                lockout_until = datetime.now(timezone.utc) + timedelta(minutes=auth_settings.lockout_duration_minutes)
                updates["locked_until"] = lockout_until

        await self.update_user(user["_id"], updates)

        # Check if account is currently locked
        locked_until = user.get("locked_until")
        is_locked = locked_until and locked_until > datetime.now(timezone.utc)

        attempts_remaining = max(0, auth_settings.max_login_attempts - updates["login_attempts"])

        return {
            "locked": is_locked,
            "attempts_remaining": attempts_remaining,
            "locked_until": locked_until.isoformat() if locked_until else None
        }

    async def is_account_locked(self, user_id: str) -> bool:
        """Check if user account is locked"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        locked_until = user.get("locked_until")
        if locked_until and isinstance(locked_until, datetime):
            return locked_until > datetime.now(timezone.utc)
        return False

    async def create_session(self, user_id: str, user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> str:
        """Create a new user session"""
        if not auth_settings.enable_session_tracking:
            return ""

        db = await self.get_db()

        session_data = {
            "_id": f"session_{user_id}_{datetime.now(timezone.utc).timestamp()}",
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=auth_settings.session_timeout_minutes),
            "user_agent": user_agent,
            "ip_address": ip_address,
            "is_active": True
        }

        await db.user_sessions.insert_one(session_data)

        # Cache session
        await cache_manager.set(f"session:{session_data['_id']}", session_data, ttl=auth_settings.session_timeout_minutes * 60)

        return session_data["_id"]

    async def update_session_activity(self, session_id: str):
        """Update session last activity"""
        if not auth_settings.enable_session_tracking:
            return

        db = await self.get_db()
        now = datetime.now(timezone.utc)

        await db.user_sessions.update_one(
            {"_id": session_id, "is_active": True},
            {
                "$set": {
                    "last_activity": now,
                    "expires_at": now + timedelta(minutes=auth_settings.session_timeout_minutes)
                }
            }
        )

        # Update cache
        cached_session = await cache_manager.get(f"session:{session_id}")
        if cached_session:
            cached_session["last_activity"] = now
            cached_session["expires_at"] = now + timedelta(minutes=auth_settings.session_timeout_minutes)
            await cache_manager.set(f"session:{session_id}", cached_session, ttl=auth_settings.session_timeout_minutes * 60)

    async def invalidate_session(self, session_id: str):
        """Invalidate a user session"""
        if not auth_settings.enable_session_tracking:
            return

        db = await self.get_db()

        await db.user_sessions.update_one(
            {"_id": session_id},
            {"$set": {"is_active": False, "invalidated_at": datetime.now(timezone.utc)}}
        )

        # Remove from cache
        await cache_manager.delete(f"session:{session_id}")

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        if not auth_settings.enable_session_tracking:
            return

        db = await self.get_db()
        now = datetime.now(timezone.utc)

        # Update database
        result = await db.user_sessions.update_many(
            {"expires_at": {"$lt": now}, "is_active": True},
            {"$set": {"is_active": False, "expired_at": now}}
        )

        if result.modified_count > 0:
            logger.info("Cleaned up expired sessions", extra={"count": result.modified_count})

    async def log_audit_event(self, event_type: str, user_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Log audit event"""
        if not auth_settings.enable_audit_logging:
            return

        db = await self.get_db()

        audit_data = {
            "_id": f"audit_{datetime.now(timezone.utc).timestamp()}",
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc),
            "details": details or {},
            "ip_address": details.get("ip_address") if details else None,
            "user_agent": details.get("user_agent") if details else None
        }

        await db.audit_logs.insert_one(audit_data)

        # Clean up old audit logs
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=auth_settings.audit_log_retention_days)
        await db.audit_logs.delete_many({"timestamp": {"$lt": cutoff_date}})

    async def get_audit_logs(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit logs"""
        db = await self.get_db()

        query = {}
        if user_id:
            query["user_id"] = user_id

        logs = await db.audit_logs.find(query).sort("timestamp", -1).limit(limit).to_list(length=None)
        return logs


# Global database instance
auth_db = AuthDatabase()


# Convenience functions
async def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new user"""
    return await auth_db.create_user(user_data)


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email"""
    return await auth_db.get_user_by_email(email)


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    return await auth_db.get_user_by_id(user_id)


async def update_user(user_id: str, updates: Dict[str, Any]) -> bool:
    """Update user data"""
    return await auth_db.update_user(user_id, updates)


async def record_login_attempt(email: str, success: bool) -> Dict[str, Any]:
    """Record login attempt"""
    return await auth_db.record_login_attempt(email, success)


async def is_account_locked(user_id: str) -> bool:
    """Check if account is locked"""
    return await auth_db.is_account_locked(user_id)