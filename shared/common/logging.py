"""
Structured logging utilities for LMS microservices
"""
import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

from shared.config.config import settings

class StructuredLogger:
    """Structured logger with correlation IDs and service context"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self._setup_logger()

    def _setup_logger(self):
        """Setup logger with structured formatting"""
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Set log level
        log_level = getattr(logging, settings.environment.upper() if hasattr(settings, 'environment') else 'INFO', logging.INFO)
        self.logger.setLevel(log_level)

        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)

        # Create structured formatter
        formatter = StructuredFormatter(service_name=self.service_name)
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)
        self.logger.propagate = False

    def _log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None):
        """Internal logging method"""
        log_data = {
            "message": message,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
        }

        if extra:
            log_data.update(extra)

        getattr(self.logger, level)(message, extra={"structured_data": log_data})

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None):
        """Log info message"""
        self._log("info", message, extra, correlation_id)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None):
        """Log error message"""
        self._log("error", message, extra, correlation_id)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None):
        """Log warning message"""
        self._log("warning", message, extra, correlation_id)

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None):
        """Log debug message"""
        self._log("debug", message, extra, correlation_id)

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None):
        """Log critical message"""
        self._log("critical", message, extra, correlation_id)

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record):
        """Format log record as JSON"""
        if hasattr(record, 'structured_data'):
            return json.dumps(record.structured_data, default=str)
        else:
            # Fallback for non-structured logs
            return super().format(record)

# Global logger instances
_loggers = {}

def get_logger(service_name: str) -> StructuredLogger:
    """Get or create logger for service"""
    if service_name not in _loggers:
        _loggers[service_name] = StructuredLogger(service_name)
    return _loggers[service_name]

# FastAPI middleware for correlation ID
class CorrelationIdMiddleware:
    """Middleware to add correlation ID to requests"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate correlation ID
        correlation_id = str(uuid.uuid4())

        # Add to scope for later retrieval
        scope["correlation_id"] = correlation_id

        # Add correlation ID to request headers for downstream services
        original_send = send

        async def send_with_correlation_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append([b"x-correlation-id", correlation_id.encode()])
                message["headers"] = headers
            await original_send(message)

        await self.app(scope, receive, send_with_correlation_id)

# Helper function to get correlation ID from FastAPI request
def get_correlation_id(request) -> str:
    """Extract correlation ID from request"""
    return getattr(request.state, 'correlation_id', str(uuid.uuid4()))