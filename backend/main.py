import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from config import settings
from routes.courses import courses_router
from routes.assignments import assignments_router
from routes.files import files_router
from routes.chat import chat_router
from routes.discussions import discussions_router
from routes.analytics import analytics_router
from routes.notifications import notifications_router
from routes.profile import profile_router
from routes.rbac import rbac_router
from routes.assessment import assessment_router
from routes.marketplace import marketplace_router
from routes.wellbeing import wellbeing_router
from routes.course_content import course_content_router
from routes.career import career_router
from routes.reviews import reviews_router
from routes.proctoring import proctoring_router
from routes.alumni import alumni_router
from routes.student import student_router
from routes.instructor import instructor_router
from routes.admin import admin_router
from routes.parent import parent_router
from routes.reviewer import reviewer_router
from routes.integrations import integrations_router
from routes.ai_ethics import ai_ethics_router
from auth import auth_router
import json
from bson import ObjectId
from utils import serialize_mongo_doc

# Custom JSON encoder for MongoDB ObjectId
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)

# WebSocket support for real-time updates
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup logic - initialize database
    from database import init_database
    init_database()
    yield
    # shutdown logic
    from database import client
    if client:
        client.close()

# Create the main app with custom JSON encoder
app = FastAPI(lifespan=lifespan, json_encoder=MongoJSONEncoder)

# Create a router with the /api prefix
from fastapi import APIRouter
api = APIRouter(prefix="/api")

# Include routers
api.include_router(auth_router, prefix="/auth", tags=["auth"])
api.include_router(courses_router, prefix="/courses", tags=["courses"])
api.include_router(assignments_router, tags=["assignments"])
api.include_router(files_router, prefix="/files", tags=["files"])
api.include_router(chat_router, tags=["chat"])
api.include_router(discussions_router, tags=["discussions"])
api.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api.include_router(reviews_router, tags=["reviews"])
api.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api.include_router(profile_router, prefix="/profile", tags=["profile"])
api.include_router(rbac_router, prefix="/rbac", tags=["rbac"])
api.include_router(assessment_router, prefix="/assessment", tags=["assessment"])
api.include_router(marketplace_router, prefix="/marketplace", tags=["marketplace"])
api.include_router(wellbeing_router, prefix="/wellbeing", tags=["wellbeing"])
api.include_router(course_content_router, prefix="/content", tags=["course_content"])
api.include_router(career_router, prefix="/career", tags=["career"])
api.include_router(proctoring_router, prefix="/proctoring", tags=["proctoring"])
api.include_router(alumni_router, prefix="/alumni", tags=["alumni"])
api.include_router(student_router, prefix="/student", tags=["student"])
api.include_router(instructor_router, prefix="/instructor", tags=["instructor"])
api.include_router(admin_router, prefix="/admin", tags=["admin"])
api.include_router(parent_router, prefix="/parent", tags=["parent"])
api.include_router(reviewer_router, prefix="/reviewer", tags=["reviewer"])
api.include_router(integrations_router, prefix="/integrations", tags=["integrations"])
api.include_router(ai_ethics_router, prefix="/ai-ethics", tags=["ai-ethics"])

# API health check
@api.get("/")
async def api_root():
    return {"message": "Hello World"}

# Root health check (must be before router inclusion)
@app.get("/")
async def root():
    return {"message": "AI LMS Backend", "status": "running", "api_docs": "/docs", "websocket_endpoint": "/ws/{user_id}"}

# WebSocket test endpoint (must be before router inclusion)
@app.get("/ws-test")
async def websocket_test():
    return {
        "message": "WebSocket endpoint available",
        "endpoint": "/ws/{user_id}",
        "instructions": "Connect using WebSocket protocol to receive real-time updates"
    }

# Add CORS middleware first
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],  # Allow frontend origins and all for development
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# WebSocket endpoint for real-time updates (must be before router inclusion)
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    logger.info(f"WebSocket connection attempt for user: {user_id}")
    try:
        await manager.connect(websocket)
        logger.info(f"WebSocket connected successfully for user: {user_id}")
        await manager.send_personal_message(f"Connected to LMS WebSocket for user {user_id}", websocket)

        while True:
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message from user {user_id}: {data}")

            # Handle different message types
            try:
                message_data = json.loads(data)
                message_type = message_data.get('type', 'unknown')

                if message_type == 'ping':
                    await manager.send_personal_message(json.dumps({"type": "pong", "timestamp": str(datetime.utcnow())}), websocket)
                elif message_type == 'subscribe':
                    await manager.send_personal_message(json.dumps({"type": "subscribed", "user_id": user_id, "timestamp": str(datetime.utcnow())}), websocket)
                else:
                    # Echo back for unknown message types
                    await manager.send_personal_message(json.dumps({
                        "type": "echo",
                        "message": data,
                        "user_id": user_id,
                        "timestamp": str(datetime.utcnow())
                    }), websocket)
            except json.JSONDecodeError:
                # If not JSON, echo back as JSON
                await manager.send_personal_message(json.dumps({
                    "type": "echo_error",
                    "message": f"Echo: {data}",
                    "timestamp": str(datetime.utcnow())
                }), websocket)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {user_id}")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket)

# Include router after WebSocket endpoint
app.include_router(api)

# Helper function to send real-time notifications
async def send_realtime_notification(user_id: str, notification_type: str, data: dict):
    """Send real-time notification to specific user"""
    message = json.dumps({
        "type": "notification",
        "notification_type": notification_type,
        "data": data,
        "timestamp": str(datetime.utcnow())
    })

    # In production, you'd send to specific user's WebSocket connection
    # For now, we'll broadcast to all connected clients
    await manager.broadcast(message)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)