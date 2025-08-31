"""
Auth Service - Handles user authentication and authorization
"""
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.hash import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.config.config import settings
from shared.database.database import get_database, _find_one, _update_one
from shared.models.models import (
    UserPublic,
    TokenPair,
    LoginRequest,
    RefreshRequest,
    UserCreate,
    UserUpdate,
    UserBase,
)

app = FastAPI(title='Auth Service', version='1.0.0')

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

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
    user = await _find_one("users", {"_id": uid})
    if not user:
        raise HTTPException(401, "User not found")
    return user

def _require_role(user: Dict[str, Any], allowed: list[str]):
    """Check if user has required role"""
    if user.get("role") not in allowed:
        raise HTTPException(403, "Insufficient permissions")

@app.post("/auth/register", response_model=UserPublic)
async def register(body: UserCreate):
    """Register a new user"""
    existing = await _find_one("users", {"email": str(body.email).lower()})
    if existing:
        raise HTTPException(400, "Email already registered")

    role = body.role or "student"
    # Bootstrap: allow first user to be super_admin if db empty
    db = get_database()
    users_count = await db.users.count_documents({})
    if role == "super_admin" and users_count > 0:
        raise HTTPException(403, "Cannot self-assign super_admin")
    if users_count == 0 and role != "super_admin":
        role = "super_admin"

    user = UserBase(email=str(body.email).lower(), name=body.name, role=role)
    doc = user.dict()
    doc["password_hash"] = bcrypt.hash(body.password)
    doc["_id"] = user.id
    await db.users.insert_one(doc)
    return UserPublic(id=user.id, email=user.email, name=user.name, role=user.role)

@app.post("/auth/login", response_model=TokenPair)
async def login(body: LoginRequest):
    """Authenticate user and return tokens"""
    user = await _find_one("users", {"email": str(body.email).lower()})
    if not user or not bcrypt.verify(body.password, user.get("password_hash", "")):
        raise HTTPException(401, "Invalid credentials")
    return await _create_tokens(user)

@app.post("/auth/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest):
    """Refresh access token"""
    try:
        payload = jwt.decode(
            body.refresh_token, settings.jwt_secret, algorithms=["HS256"]
        )
    except Exception:
        raise HTTPException(401, "Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token type")
    db = get_database()
    user = await db.users.find_one({"_id": payload.get("sub")})
    if not user:
        raise HTTPException(401, "User not found")
    return await _create_tokens(user)

@app.get("/auth/me", response_model=UserPublic)
async def me(user=Depends(_current_user)):
    """Get current user profile"""
    return UserPublic(
        id=user["id"], email=user["email"], name=user["name"], role=user["role"]
    )

@app.put("/auth/me", response_model=UserPublic)
async def update_me(body: dict, user=Depends(_current_user)):
    """Update current user profile"""
    updates = {}
    if "name" in body and body["name"] is not None:
        updates["name"] = body["name"]
    if "email" in body and body["email"] is not None and body["email"] != user["email"]:
        # Basic email validation
        if "@" not in body["email"] or "." not in body["email"]:
            raise HTTPException(400, "Invalid email format")
        existing = await _find_one("users", {"email": str(body["email"]).lower()})
        if existing:
            raise HTTPException(400, "Email already taken")
        updates["email"] = str(body["email"]).lower()
    if "password" in body and body["password"] is not None:
        updates["password_hash"] = bcrypt.hash(body["password"])
    if updates:
        await _update_one("users", {"_id": user["id"]}, updates)
        user.update(updates)
    return UserPublic(id=user["id"], email=user["email"], name=user["name"], role=user["role"])

@app.get("/auth/users", response_model=List[UserPublic])
async def list_users(user=Depends(_current_user)):
    """List all users (admin only)"""
    _require_role(user, ["admin"])
    db = get_database()
    docs = await db.users.find({}).to_list(1000)
    return [UserPublic(id=d["_id"], email=d["email"], name=d["name"], role=d["role"]) for d in docs]

@app.delete("/auth/users/{uid}")
async def delete_user(uid: str, user=Depends(_current_user)):
    """Delete user (admin only)"""
    _require_role(user, ["admin"])
    if uid == user["id"]:
        raise HTTPException(400, "Cannot delete yourself")
    db = get_database()
    result = await db.users.delete_one({"_id": uid})
    if result.deleted_count == 0:
        raise HTTPException(404, "User not found")
    return {"status": "deleted"}

@app.put("/auth/users/{uid}")
async def update_user(uid: str, body: dict, user=Depends(_current_user)):
    """Update user (admin only)"""
    _require_role(user, ["admin"])
    db = get_database()
    updates = {}
    if "name" in body and body["name"] is not None:
        updates["name"] = body["name"]
    if "email" in body and body["email"] is not None:
        # Basic email validation
        if "@" not in body["email"] or "." not in body["email"]:
            raise HTTPException(400, "Invalid email format")
        updates["email"] = str(body["email"]).lower()
    if "password" in body and body["password"] is not None:
        updates["password_hash"] = bcrypt.hash(body["password"])
    if "role" in body and body["role"] is not None:
        updates["role"] = body["role"]
    if updates:
        await _update_one("users", {"_id": uid}, updates)
    return {"status": "updated"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Auth Service", "status": "running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=settings.environment == 'development')