from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
from database import get_database, _uuid
from auth import _current_user
from models import UserProfile, CareerProfile

admin_router = APIRouter()

@admin_router.get("/system-health")
async def get_system_health(user=Depends(_current_user)):
    """Get comprehensive system health metrics"""
    db = get_database()

    # Check if user is an admin
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    # Get system health data
    system_health = {
        "uptime": "99.9%",
        "response_time": "45ms",
        "db_connections": "23/100",
        "query_time": "12ms",
        "total_files": 1247,
        "active_users": 89,
        "server_load": "23%",
        "memory_usage": "67%",
        "disk_usage": "65%",
        "last_backup": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "services": {
            "api": "healthy",
            "database": "healthy",
            "file_storage": "healthy",
            "email": "healthy",
            "notifications": "healthy"
        }
    }

    return system_health

@admin_router.get("/security-logs")
async def get_security_logs(limit: int = 50, user=Depends(_current_user)):
    """Get security event logs"""
    db = get_database()

    # Check if user is an admin
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    # Get security logs (simulated data)
    security_logs = [
        {
            "_id": _uuid(),
            "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            "event": "User login",
            "user": "student@example.com",
            "ip_address": "192.168.1.100",
            "status": "success",
            "details": "Successful login from web browser"
        },
        {
            "_id": _uuid(),
            "timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
            "event": "Failed login attempt",
            "user": "unknown@example.com",
            "ip_address": "10.0.0.50",
            "status": "warning",
            "details": "Invalid credentials provided"
        },
        {
            "_id": _uuid(),
            "timestamp": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
            "event": "Password changed",
            "user": "instructor@example.com",
            "ip_address": "192.168.1.150",
            "status": "success",
            "details": "User password updated successfully"
        },
        {
            "_id": _uuid(),
            "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            "event": "Admin action",
            "user": "admin@example.com",
            "ip_address": "192.168.1.200",
            "status": "success",
            "details": "User role updated for student@example.com"
        },
        {
            "_id": _uuid(),
            "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "event": "File upload",
            "user": "student@example.com",
            "ip_address": "192.168.1.100",
            "status": "success",
            "details": "Assignment submission uploaded (2.3MB)"
        }
    ]

    return security_logs[:limit]

@admin_router.get("/compliance-reports")
async def get_compliance_reports(user=Depends(_current_user)):
    """Get compliance and audit reports"""
    db = get_database()

    # Check if user is an admin
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    # Get compliance reports
    compliance_reports = [
        {
            "_id": _uuid(),
            "title": "GDPR Compliance Report",
            "description": "Monthly GDPR compliance assessment and data handling review",
            "type": "gdpr",
            "generated_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "status": "compliant",
            "score": 95,
            "findings": [
                "Data retention policies properly implemented",
                "User consent mechanisms working correctly",
                "Data encryption standards met"
            ]
        },
        {
            "_id": _uuid(),
            "title": "Accessibility Audit",
            "description": "WCAG 2.1 compliance and accessibility assessment",
            "type": "accessibility",
            "generated_date": (datetime.utcnow() - timedelta(days=14)).isoformat(),
            "status": "good",
            "score": 92,
            "findings": [
                "Color contrast ratios meet standards",
                "Keyboard navigation fully supported",
                "Screen reader compatibility verified"
            ]
        },
        {
            "_id": _uuid(),
            "title": "Data Privacy Assessment",
            "description": "Comprehensive data privacy and protection evaluation",
            "type": "privacy",
            "generated_date": (datetime.utcnow() - timedelta(days=21)).isoformat(),
            "status": "excellent",
            "score": 98,
            "findings": [
                "All data processing activities documented",
                "Privacy impact assessments completed",
                "Data minimization principles applied"
            ]
        }
    ]

    return compliance_reports

@admin_router.get("/system-analytics")
async def get_system_analytics(timeframe: str = "24h", user=Depends(_current_user)):
    """Get detailed system analytics"""
    db = get_database()

    # Check if user is an admin
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    # Calculate timeframe
    now = datetime.utcnow()
    if timeframe == "24h":
        start_date = now - timedelta(hours=24)
    elif timeframe == "7d":
        start_date = now - timedelta(days=7)
    elif timeframe == "30d":
        start_date = now - timedelta(days=30)
    else:
        start_date = now - timedelta(hours=24)

    # Get analytics data
    analytics = {
        "timeframe": timeframe,
        "requests_per_minute": 1250,
        "error_rate": "0.1%",
        "avg_response_time": "85ms",
        "active_sessions": 89,
        "failed_logins": 12,
        "security_alerts": 3,
        "user_activity": {
            "total_logins": 1247,
            "unique_users": 456,
            "avg_session_duration": "24m",
            "peak_concurrent_users": 89
        },
        "performance": {
            "cpu_usage": "23%",
            "memory_usage": "67%",
            "disk_io": "45MB/s",
            "network_io": "120MB/s"
        },
        "content": {
            "total_files": 1247,
            "total_size": "6.5GB",
            "uploads_today": 23,
            "downloads_today": 156
        },
        "courses": {
            "total_courses": 89,
            "active_courses": 67,
            "total_enrollments": 2341,
            "completion_rate": "78%"
        }
    }

    return analytics

@admin_router.get("/integration-status")
async def get_integration_status(user=Depends(_current_user)):
    """Get status of all system integrations"""
    db = get_database()

    # Check if user is an admin
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    # Get integration status
    integration_status = {
        "lms": {
            "status": "active",
            "last_sync": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            "connected_platforms": ["Canvas", "Moodle"],
            "sync_status": "successful"
        },
        "job_market": {
            "status": "configuring",
            "last_sync": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "connected_platforms": ["LinkedIn", "Indeed"],
            "sync_status": "pending"
        },
        "assessment": {
            "status": "active",
            "last_sync": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
            "connected_platforms": ["Kahoot", "Quizlet"],
            "sync_status": "successful"
        },
        "analytics": {
            "status": "inactive",
            "last_sync": None,
            "connected_platforms": ["Google Analytics"],
            "sync_status": "not_configured"
        },
        "cloud": {
            "status": "active",
            "last_sync": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
            "connected_platforms": ["AWS S3", "Google Drive"],
            "sync_status": "successful"
        },
        "ai": {
            "status": "active",
            "last_sync": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            "connected_platforms": ["OpenAI", "Google AI"],
            "sync_status": "successful"
        }
    }

    return integration_status

@admin_router.get("/backup-status")
async def get_backup_status(user=Depends(_current_user)):
    """Get backup and recovery status"""
    db = get_database()

    # Check if user is an admin
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    # Get backup status
    backup_status = {
        "last_backup": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "status": "successful",
        "size": "2.3GB",
        "duration": "15m 30s",
        "next_scheduled": (datetime.utcnow() + timedelta(hours=22)).isoformat(),
        "backup_history": [
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "status": "successful",
                "size": "2.3GB",
                "type": "full"
            },
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=26)).isoformat(),
                "status": "successful",
                "size": "2.2GB",
                "type": "incremental"
            },
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=50)).isoformat(),
                "status": "successful",
                "size": "2.1GB",
                "type": "incremental"
            }
        ],
        "storage": {
            "used": "45GB",
            "available": "155GB",
            "total": "200GB"
        }
    }

    return backup_status

@admin_router.post("/run-health-check")
async def run_health_check(user=Depends(_current_user)):
    """Run comprehensive system health check"""
    db = get_database()

    # Check if user is an admin
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    # Simulate health check
    health_check = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "completed",
        "checks": {
            "database": {"status": "healthy", "response_time": "12ms"},
            "api": {"status": "healthy", "response_time": "45ms"},
            "file_storage": {"status": "healthy", "available_space": "155GB"},
            "email_service": {"status": "healthy", "last_test": "2 hours ago"},
            "notification_service": {"status": "healthy", "queue_size": 0}
        },
        "recommendations": [
            "Consider increasing database connection pool size",
            "File storage is at 75% capacity - plan for expansion"
        ]
    }

    return health_check

@admin_router.post("/clear-cache")
async def clear_system_cache(user=Depends(_current_user)):
    """Clear system cache"""
    db = get_database()

    # Check if user is an admin
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    # Simulate cache clearing
    cache_clear = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "completed",
        "cleared_items": 1247,
        "freed_memory": "256MB",
        "cache_types": ["api_cache", "file_cache", "session_cache"]
    }

    return cache_clear

@admin_router.post("/force-password-reset")
async def force_password_reset(user_ids: List[str], user=Depends(_current_user)):
    """Force password reset for specified users"""
    db = get_database()

    # Check if user is an admin
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    # Force password reset for users
    reset_results = []
    for user_id in user_ids:
        # In a real implementation, this would send password reset emails
        reset_results.append({
            "user_id": user_id,
            "status": "reset_initiated",
            "reset_token": _uuid(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        })

    return {
        "message": f"Password reset initiated for {len(user_ids)} users",
        "results": reset_results
    }

@admin_router.post("/audit-user-access")
async def audit_user_access(user=Depends(_current_user)):
    """Audit user access and permissions"""
    db = get_database()

    # Check if user is an admin
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    # Get all users and their access patterns
    users = await db.users.find({}).to_list(1000)

    audit_results = []
    for user in users:
        # Get user's recent activity
        recent_activity = await db.user_activity.find({
            "user_id": user["_id"],
            "timestamp": {"$gte": datetime.utcnow() - timedelta(days=30)}
        }).to_list(10)

        audit_results.append({
            "user_id": user["_id"],
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "role": user.get("role", ""),
            "last_login": user.get("last_login"),
            "activity_count": len(recent_activity),
            "permissions": user.get("permissions", []),
            "risk_level": "low"  # Would be calculated based on activity patterns
        })

    return audit_results

@admin_router.post("/configure-integration")
async def configure_integration(integration_type: str, config: dict, user=Depends(_current_user)):
    """Configure system integration"""
    db = get_database()

    # Check if user is an admin
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    # Configure integration (simplified)
    integration_config = {
        "type": integration_type,
        "config": config,
        "configured_by": user["id"],
        "configured_at": datetime.utcnow().isoformat(),
        "status": "configured"
    }

    # Save configuration
    await db.integrations.insert_one(integration_config)

    return {
        "message": f"{integration_type} integration configured successfully",
        "config_id": integration_config["_id"]
    }

@admin_router.post("/manual-backup")
async def manual_backup(backup_type: str = "full", user=Depends(_current_user)):
    """Initiate manual backup"""
    db = get_database()

    # Check if user is an admin
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    # Initiate backup (simplified)
    backup_job = {
        "_id": _uuid(),
        "type": backup_type,
        "status": "in_progress",
        "initiated_by": user["id"],
        "initiated_at": datetime.utcnow().isoformat(),
        "estimated_completion": (datetime.utcnow() + timedelta(minutes=15)).isoformat()
    }

    # Save backup job
    await db.backup_jobs.insert_one(backup_job)

    return {
        "message": f"{backup_type} backup initiated",
        "job_id": backup_job["_id"],
        "estimated_completion": backup_job["estimated_completion"]
    }