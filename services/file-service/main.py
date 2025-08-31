"""
File Service - Handles file uploads, storage, and management
"""
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from typing import List, Optional
from datetime import datetime, timezone
import sys
import os
import aiofiles
import uuid

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.config.config import settings
from shared.database.database import get_database, _uuid

app = FastAPI(title='File Service', version='1.0.0')

# JWT token validation for service-to-service calls
async def _current_user(token: Optional[str] = None):
    """Validate JWT token for service-to-service calls"""
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

        # Get user from database to ensure they still exist
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

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(_current_user)):
    """Upload a file"""
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'application/pdf', 'text/plain']
    if file.content_type not in allowed_types:
        raise HTTPException(400, "File type not allowed")

    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"

    # Save file to disk (in production, use cloud storage)
    file_path = f"uploads/{unique_filename}"
    os.makedirs("uploads", exist_ok=True)

    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    # Save file metadata to database
    db = get_database()
    file_doc = {
        "_id": _uuid(),
        "filename": file.filename,
        "unique_filename": unique_filename,
        "file_path": file_path,
        "content_type": file.content_type,
        "size": len(content),
        "uploaded_by": user["id"],
        "uploaded_at": datetime.now(timezone.utc)
    }

    await db.files.insert_one(file_doc)

    return {
        "file_id": file_doc["_id"],
        "filename": file.filename,
        "size": len(content),
        "content_type": file.content_type
    }

@app.get("/files")
async def list_files(user=Depends(_current_user)):
    """List user's files"""
    db = get_database()
    files = await db.files.find({"uploaded_by": user["id"]}).sort("uploaded_at", -1).to_list(50)
    return files

@app.get("/files/{file_id}")
async def get_file(file_id: str, user=Depends(_current_user)):
    """Get file metadata"""
    db = get_database()
    file_doc = await db.files.find_one({"_id": file_id, "uploaded_by": user["id"]})
    if not file_doc:
        raise HTTPException(404, "File not found")
    return file_doc

@app.delete("/files/{file_id}")
async def delete_file(file_id: str, user=Depends(_current_user)):
    """Delete a file"""
    db = get_database()
    file_doc = await db.files.find_one({"_id": file_id, "uploaded_by": user["id"]})
    if not file_doc:
        raise HTTPException(404, "File not found")

    # Delete file from disk
    if os.path.exists(file_doc["file_path"]):
        os.remove(file_doc["file_path"])

    # Delete from database
    await db.files.delete_one({"_id": file_id})

    return {"status": "deleted"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "file"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "File Service", "status": "running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8008, reload=settings.environment == 'development')