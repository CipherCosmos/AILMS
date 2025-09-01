"""
New File Service main.py - Production-ready structure
This replaces the old monolithic main.py file
"""
import uvicorn
from app.main import create_application

# Create FastAPI application
app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "main_new:app",
        host="0.0.0.0",
        port=8008,
        reload=True,  # Enable reload for development
        log_level="info"
    )