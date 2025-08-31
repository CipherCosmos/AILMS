from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from database import get_database, _uuid
from auth import _current_user
from models import ProctoringSession, AcademicIntegrityReport

proctoring_router = APIRouter()

@proctoring_router.post("/sessions")
async def start_proctoring_session(session_data: dict, user=Depends(_current_user)):
    """Start a new proctoring session"""
    db = get_database()

    # Check if user is a proctor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "proctor":
        raise HTTPException(403, "Proctor access required")

    session = ProctoringSession(
        quiz_attempt_id=session_data["quiz_attempt_id"],
        proctor_id=user["id"],
        session_start=datetime.utcnow(),
        ai_monitoring_enabled=session_data.get("ai_monitoring_enabled", True)
    )

    doc = session.dict()
    doc["_id"] = session.id
    await db.proctoring_sessions.insert_one(doc)

    return session

@proctoring_router.get("/sessions")
async def get_proctoring_sessions(user=Depends(_current_user)):
    """Get proctoring sessions for the current proctor"""
    db = get_database()

    # Check if user is a proctor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "proctor":
        raise HTTPException(403, "Proctor access required")

    sessions = await db.proctoring_sessions.find({
        "proctor_id": user["id"]
    }).to_list(100)

    # Enrich with student and quiz information
    enriched_sessions = []
    for session in sessions:
        # Get quiz attempt details
        quiz_attempt = await db.quiz_attempts.find_one({"_id": session["quiz_attempt_id"]})
        if quiz_attempt:
            # Get student details
            student = await db.users.find_one({"_id": quiz_attempt["user_id"]})
            # Get quiz details
            quiz = await db.quizzes.find_one({"_id": quiz_attempt["quiz_id"]})

            enriched_session = {
                "id": session["_id"],
                "student_name": student["name"] if student else "Unknown",
                "exam_title": quiz["title"] if quiz else "Unknown Quiz",
                "start_time": session["session_start"],
                "duration_minutes": session.get("duration_minutes", 60),
                "status": session.get("status", "active"),
                "ai_monitoring": session.get("ai_monitoring_enabled", True),
                "behavioral_flags": session.get("behavioral_flags", [])
            }
            enriched_sessions.append(enriched_session)

    return enriched_sessions

@proctoring_router.post("/sessions/{session_id}/pause")
async def pause_session(session_id: str, user=Depends(_current_user)):
    """Pause a proctoring session"""
    db = get_database()

    # Check if user is a proctor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "proctor":
        raise HTTPException(403, "Proctor access required")

    session = await db.proctoring_sessions.find_one({"_id": session_id})
    if not session:
        raise HTTPException(404, "Session not found")

    if session["proctor_id"] != user["id"]:
        raise HTTPException(403, "Not authorized for this session")

    await db.proctoring_sessions.update_one(
        {"_id": session_id},
        {"$set": {"status": "paused"}}
    )

    return {"status": "paused"}

@proctoring_router.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str, user=Depends(_current_user)):
    """Resume a proctoring session"""
    db = get_database()

    # Check if user is a proctor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "proctor":
        raise HTTPException(403, "Proctor access required")

    session = await db.proctoring_sessions.find_one({"_id": session_id})
    if not session:
        raise HTTPException(404, "Session not found")

    if session["proctor_id"] != user["id"]:
        raise HTTPException(403, "Not authorized for this session")

    await db.proctoring_sessions.update_one(
        {"_id": session_id},
        {"$set": {"status": "active"}}
    )

    return {"status": "resumed"}

@proctoring_router.post("/sessions/{session_id}/terminate")
async def terminate_session(session_id: str, user=Depends(_current_user)):
    """Terminate a proctoring session"""
    db = get_database()

    # Check if user is a proctor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "proctor":
        raise HTTPException(403, "Proctor access required")

    session = await db.proctoring_sessions.find_one({"_id": session_id})
    if not session:
        raise HTTPException(404, "Session not found")

    if session["proctor_id"] != user["id"]:
        raise HTTPException(403, "Not authorized for this session")

    await db.proctoring_sessions.update_one(
        {"_id": session_id},
        {
            "$set": {
                "status": "terminated",
                "session_end": datetime.utcnow()
            }
        }
    )

    return {"status": "terminated"}

@proctoring_router.post("/incidents")
async def report_incident(incident_data: dict, user=Depends(_current_user)):
    """Report an academic integrity incident"""
    db = get_database()

    # Check if user is a proctor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "proctor":
        raise HTTPException(403, "Proctor access required")

    # Get session details
    session = await db.proctoring_sessions.find_one({"_id": incident_data["session_id"]})
    if not session:
        raise HTTPException(404, "Session not found")

    # Get student details
    quiz_attempt = await db.quiz_attempts.find_one({"_id": session["quiz_attempt_id"]})
    student = await db.users.find_one({"_id": quiz_attempt["user_id"]}) if quiz_attempt else None

    incident = AcademicIntegrityReport(
        submission_id=incident_data["session_id"],  # Using session_id as submission_id for now
        report_type=incident_data["incident_type"],
        vendor="ai_proctoring",
        score=incident_data.get("severity_score", 0.5),
        flagged_content=[incident_data["description"]],
        reviewed_by=user["id"]
    )

    doc = incident.dict()
    doc["_id"] = incident.id
    await db.academic_integrity_reports.insert_one(doc)

    # Add incident to session
    await db.proctoring_sessions.update_one(
        {"_id": incident_data["session_id"]},
        {
            "$push": {
                "incidents": {
                    "type": incident_data["incident_type"],
                    "description": incident_data["description"],
                    "timestamp": datetime.utcnow(),
                    "severity": incident_data.get("severity", "medium")
                }
            }
        }
    )

    return incident

@proctoring_router.get("/incidents")
async def get_incidents(user=Depends(_current_user)):
    """Get incidents reported by the current proctor"""
    db = get_database()

    # Check if user is a proctor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "proctor":
        raise HTTPException(403, "Proctor access required")

    incidents = await db.academic_integrity_reports.find({
        "reviewed_by": user["id"]
    }).to_list(100)

    # Enrich with student information
    enriched_incidents = []
    for incident in incidents:
        # Get session details
        session = await db.proctoring_sessions.find_one({"_id": incident["submission_id"]})
        if session:
            quiz_attempt = await db.quiz_attempts.find_one({"_id": session["quiz_attempt_id"]})
            student = await db.users.find_one({"_id": quiz_attempt["user_id"]}) if quiz_attempt else None

            enriched_incident = {
                "id": incident["_id"],
                "incident_type": incident["report_type"],
                "description": incident["flagged_content"][0] if incident["flagged_content"] else "",
                "severity": "high" if incident["score"] > 0.7 else "medium" if incident["score"] > 0.4 else "low",
                "student_name": student["name"] if student else "Unknown",
                "timestamp": incident["created_at"] if "created_at" in incident else datetime.utcnow(),
                "status": incident.get("status", "pending")
            }
            enriched_incidents.append(enriched_incident)

    return enriched_incidents

@proctoring_router.get("/analytics")
async def get_proctoring_analytics(user=Depends(_current_user)):
    """Get proctoring analytics for the current proctor"""
    db = get_database()

    # Check if user is a proctor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "proctor":
        raise HTTPException(403, "Proctor access required")

    # Get session statistics
    total_sessions = await db.proctoring_sessions.count_documents({"proctor_id": user["id"]})
    active_sessions = await db.proctoring_sessions.count_documents({
        "proctor_id": user["id"],
        "status": "active"
    })

    # Get incident statistics
    total_incidents = await db.academic_integrity_reports.count_documents({
        "reviewed_by": user["id"]
    })

    # Calculate average session time (simplified)
    sessions = await db.proctoring_sessions.find({
        "proctor_id": user["id"],
        "session_end": {"$exists": True}
    }).to_list(100)

    avg_session_time = 0
    if sessions:
        total_time = sum(
            (session["session_end"] - session["session_start"]).total_seconds() / 60
            for session in sessions
            if "session_end" in session
        )
        avg_session_time = total_time / len(sessions) if sessions else 0

    # AI detection statistics
    ai_detections = await db.proctoring_sessions.count_documents({
        "proctor_id": user["id"],
        "behavioral_flags": {"$exists": True, "$ne": []}
    })

    return {
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "total_incidents": total_incidents,
        "avg_session_time": round(avg_session_time, 1),
        "ai_detections": ai_detections
    }

@proctoring_router.post("/sessions/{session_id}/flag")
async def flag_behavioral_issue(session_id: str, flag_data: dict, user=Depends(_current_user)):
    """Flag a behavioral issue during proctoring"""
    db = get_database()

    # Check if user is a proctor
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "proctor":
        raise HTTPException(403, "Proctor access required")

    session = await db.proctoring_sessions.find_one({"_id": session_id})
    if not session:
        raise HTTPException(404, "Session not found")

    if session["proctor_id"] != user["id"]:
        raise HTTPException(403, "Not authorized for this session")

    # Add behavioral flag
    flag = {
        "type": flag_data["flag_type"],
        "description": flag_data["description"],
        "timestamp": datetime.utcnow(),
        "severity": flag_data.get("severity", "medium")
    }

    await db.proctoring_sessions.update_one(
        {"_id": session_id},
        {"$push": {"behavioral_flags": flag}}
    )

    return {"status": "flagged", "flag": flag}