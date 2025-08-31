"""
Security enhancements for LMS backend.
"""
import re
import hashlib
import secrets
import hmac
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from fastapi import HTTPException, Request
from passlib.hash import bcrypt
import bleach
from config import settings

logger = logging.getLogger(__name__)

class SecurityManager:
    """Comprehensive security manager for LMS."""

    def __init__(self):
        self._suspicious_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS attempts
            r'javascript:',                # JavaScript injection
            r'on\w+\s*=',                  # Event handlers
            r'union\s+select',             # SQL injection patterns
            r';\s*drop\s+table',           # SQL injection
            r'--',                         # SQL comments
            r'/\*\*/',                     # SQL comments
        ]

    def sanitize_input(self, input_data: Any, allow_html: bool = False) -> Any:
        """Sanitize user input to prevent XSS and injection attacks."""
        if isinstance(input_data, str):
            # Remove potentially dangerous patterns
            for pattern in self._suspicious_patterns:
                if re.search(pattern, input_data, re.IGNORECASE):
                    logger.warning(f"Potentially malicious input detected: {pattern}")
                    raise HTTPException(400, "Invalid input detected")

            # Sanitize HTML if not allowed
            if not allow_html:
                input_data = bleach.clean(input_data, strip=True)

            # Limit input length
            if len(input_data) > 10000:
                raise HTTPException(400, "Input too long")

            return input_data

        elif isinstance(input_data, dict):
            return {k: self.sanitize_input(v, allow_html) for k, v in input_data.items()}

        elif isinstance(input_data, list):
            return [self.sanitize_input(item, allow_html) for item in input_data]

        return input_data

    def validate_password_strength(self, password: str) -> bool:
        """Validate password strength requirements."""
        if len(password) < 8:
            return False

        # Check for required character types
        has_upper = re.search(r'[A-Z]', password)
        has_lower = re.search(r'[a-z]', password)
        has_digit = re.search(r'\d', password)
        has_special = re.search(r'[!@#$%^&*(),.?":{}|<>]', password)

        return all([has_upper, has_lower, has_digit, has_special])

    def hash_password(self, password: str) -> str:
        """Securely hash password."""
        return bcrypt.hash(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.verify(password, hashed)

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token."""
        return secrets.token_urlsafe(length)

    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for storage."""
        return hashlib.sha256(data.encode()).hexdigest()

    def validate_email_format(self, email: str) -> bool:
        """Validate email format and prevent email injection."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(email_pattern, email):
            return False

        # Prevent email header injection
        if '\n' in email or '\r' in email:
            return False

        return True

    def rate_limit_check(self, identifier: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
        """Check if request should be rate limited."""
        # This would integrate with the rate limiter
        # For now, return True (allow)
        return True

    def log_security_event(self, event_type: str, details: Dict[str, Any], request: Optional[Request] = None):
        """Log security-related events."""
        log_data = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }

        if request:
            log_data.update({
                "ip_address": getattr(request.client, 'host', 'unknown') if request.client else 'unknown',
                "user_agent": request.headers.get('user-agent', 'unknown'),
                "endpoint": f"{request.method} {request.url.path}"
            })

        logger.warning(f"SECURITY EVENT: {log_data}")

class InputValidator:
    """Input validation utilities."""

    @staticmethod
    def validate_course_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate course creation/update data."""
        required_fields = ['title', 'audience', 'difficulty']
        for field in required_fields:
            if field not in data or not data[field]:
                raise HTTPException(400, f"Missing required field: {field}")

        # Validate title length
        if len(data['title']) > 200:
            raise HTTPException(400, "Course title too long")

        # Validate difficulty
        valid_difficulties = ['beginner', 'intermediate', 'advanced']
        if data['difficulty'] not in valid_difficulties:
            raise HTTPException(400, f"Invalid difficulty. Must be one of: {valid_difficulties}")

        return data

    @staticmethod
    def validate_user_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user creation/update data."""
        security = SecurityManager()

        if 'email' in data:
            if not security.validate_email_format(data['email']):
                raise HTTPException(400, "Invalid email format")

        if 'password' in data:
            if not security.validate_password_strength(data['password']):
                raise HTTPException(400, "Password too weak. Must contain uppercase, lowercase, digit, and special character")

        # Validate role
        if 'role' in data:
            valid_roles = ['student', 'instructor', 'admin', 'parent']
            if data['role'] not in valid_roles:
                raise HTTPException(400, f"Invalid role. Must be one of: {valid_roles}")

        return data

    @staticmethod
    def validate_assignment_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate assignment data."""
        required_fields = ['title', 'description']
        for field in required_fields:
            if field not in data or not data[field]:
                raise HTTPException(400, f"Missing required field: {field}")

        # Validate due date
        if 'due_at' in data:
            try:
                due_date = datetime.fromisoformat(data['due_at'].replace('Z', '+00:00'))
                if due_date < datetime.utcnow():
                    raise HTTPException(400, "Due date cannot be in the past")
            except ValueError:
                raise HTTPException(400, "Invalid due date format")

        return data

class ContentSecurity:
    """Content security and filtering."""

    @staticmethod
    def filter_file_upload(filename: str, content_type: str, file_size: int) -> bool:
        """Filter uploaded files for security."""
        # Check file extension
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.gif']
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            return False

        # Check content type
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'image/jpeg',
            'image/png',
            'image/gif'
        ]
        if content_type not in allowed_types:
            return False

        # Check file size (max 10MB)
        if file_size > 10 * 1024 * 1024:
            return False

        return True

    @staticmethod
    def scan_content_for_malware(content: bytes) -> bool:
        """Scan content for malware signatures (placeholder)."""
        # This would integrate with antivirus software
        # For now, just check for obvious malicious patterns
        malicious_patterns = [
            b'<script',
            b'javascript:',
            b'onload=',
            b'onerror='
        ]

        content_str = content.lower()
        for pattern in malicious_patterns:
            if pattern in content_str:
                return False

        return True

class AuditLogger:
    """Audit logging for compliance and security monitoring."""

    def __init__(self):
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)

        # Create audit log handler
        handler = logging.FileHandler('logs/audit.log')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)

    def log_user_action(self, user_id: str, action: str, resource: str, details: Dict[str, Any] = None):
        """Log user actions for audit trail."""
        log_entry = {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }

        self.logger.info(f"AUDIT: {log_entry}")

    def log_security_incident(self, incident_type: str, details: Dict[str, Any]):
        """Log security incidents."""
        log_entry = {
            "incident_type": incident_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }

        self.logger.warning(f"SECURITY_INCIDENT: {log_entry}")

    def log_system_event(self, event_type: str, details: Dict[str, Any]):
        """Log system-level events."""
        log_entry = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }

        self.logger.info(f"SYSTEM_EVENT: {log_entry}")

# Global instances
security_manager = SecurityManager()
input_validator = InputValidator()
content_security = ContentSecurity()
audit_logger = AuditLogger()

# Security middleware
async def security_middleware(request: Request, call_next):
    """Security middleware for request processing."""
    # Log the request
    logger.info(f"Request: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")

    # Check for suspicious patterns in headers
    suspicious_headers = ['x-forwarded-for', 'x-real-ip']
    for header in suspicious_headers:
        if header in request.headers and len(request.headers.getlist(header)) > 1:
            audit_logger.log_security_incident("header_injection_attempt", {
                "header": header,
                "values": request.headers.getlist(header),
                "ip": request.client.host if request.client else 'unknown'
            })

    # Process the request
    response = await call_next(request)

    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"

    return response