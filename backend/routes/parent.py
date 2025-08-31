from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
from database import get_database, _uuid
from auth import _current_user
from models import UserProfile, CareerProfile

parent_router = APIRouter()

@parent_router.get("/children")
async def get_children(user=Depends(_current_user)):
    """Get children linked to the parent"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Get children linked to this parent (simplified - in real implementation, this would be a relationship table)
    children = [
        {
            "_id": "student1",
            "name": "Emma Johnson",
            "grade": "10th Grade",
            "avatar": "👩‍🎓",
            "enrolled_courses": 4,
            "average_grade": 92,
            "current_streak": 5,
            "total_points": 1250
        },
        {
            "_id": "student2",
            "name": "Alex Johnson",
            "grade": "8th Grade",
            "avatar": "👨‍🎓",
            "enrolled_courses": 3,
            "average_grade": 88,
            "current_streak": 3,
            "total_points": 980
        }
    ]

    return children

@parent_router.get("/child/{child_id}/progress")
async def get_child_progress(child_id: str, user=Depends(_current_user)):
    """Get detailed progress for a specific child"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Get child progress data
    progress = {
        "overall_progress": 78,
        "completed_courses": 2,
        "active_courses": 3,
        "total_lessons": 45,
        "completed_lessons": 35,
        "average_quiz_score": 87,
        "study_time_this_week": 12.5,
        "achievements": [
            {
                "_id": "ach1",
                "name": "Week Warrior",
                "date": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                "icon": "⚔️"
            },
            {
                "_id": "ach2",
                "name": "Quiz Master",
                "date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "icon": "🧠"
            }
        ]
    }

    return progress

@parent_router.get("/child/{child_id}/courses")
async def get_child_courses(child_id: str, user=Depends(_current_user)):
    """Get courses for a specific child"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Get child courses
    courses = [
        {
            "_id": "course1",
            "title": "Advanced Mathematics",
            "progress": 85,
            "grade": 94,
            "last_activity": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "next_deadline": (datetime.utcnow() + timedelta(days=4)).isoformat(),
            "status": "active"
        },
        {
            "_id": "course2",
            "title": "Physics Fundamentals",
            "progress": 72,
            "grade": 89,
            "last_activity": (datetime.utcnow() - timedelta(days=2)).isoformat(),
            "next_deadline": (datetime.utcnow() + timedelta(days=6)).isoformat(),
            "status": "active"
        },
        {
            "_id": "course3",
            "title": "English Literature",
            "progress": 100,
            "grade": 96,
            "last_activity": (datetime.utcnow() - timedelta(days=5)).isoformat(),
            "next_deadline": None,
            "status": "completed"
        }
    ]

    return courses

@parent_router.get("/communication-history")
async def get_communication_history(child_id: Optional[str] = None, user=Depends(_current_user)):
    """Get communication history with children and teachers"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Get communication history
    communications = [
        {
            "_id": _uuid(),
            "child_id": "student1",
            "type": "message",
            "content": "Great job on your math homework this week!",
            "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "direction": "parent_to_student"
        },
        {
            "_id": _uuid(),
            "child_id": "student1",
            "type": "notification",
            "content": "Emma completed Advanced Mathematics lesson 5",
            "timestamp": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
            "direction": "system"
        },
        {
            "_id": _uuid(),
            "child_id": "student2",
            "type": "message",
            "content": "Remember to review your science notes for tomorrow's quiz",
            "timestamp": (datetime.utcnow() - timedelta(hours=12)).isoformat(),
            "direction": "parent_to_student"
        }
    ]

    if child_id:
        communications = [c for c in communications if c["child_id"] == child_id]

    return communications

@parent_router.post("/send-message")
async def send_message_to_child(message_data: dict, user=Depends(_current_user)):
    """Send a message to a child"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Create message record
    message = {
        "_id": _uuid(),
        "parent_id": user["id"],
        "child_id": message_data.get("child_id"),
        "content": message_data.get("content"),
        "timestamp": datetime.utcnow().isoformat(),
        "type": "message",
        "direction": "parent_to_student"
    }

    # Save message (simplified)
    await db.messages.insert_one(message)

    return {
        "message_id": message["_id"],
        "status": "sent",
        "timestamp": message["timestamp"]
    }

@parent_router.get("/learning-goals")
async def get_learning_goals(child_id: Optional[str] = None, user=Depends(_current_user)):
    """Get learning goals for children"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Get learning goals
    goals = [
        {
            "_id": _uuid(),
            "child_id": "student1",
            "title": "Improve Math Grade to A",
            "description": "Focus on algebra and geometry concepts",
            "target_date": (datetime.utcnow() + timedelta(days=60)).isoformat(),
            "progress": 75,
            "status": "on_track",
            "created_at": (datetime.utcnow() - timedelta(days=30)).isoformat()
        },
        {
            "_id": _uuid(),
            "child_id": "student2",
            "title": "Complete Science Fair Project",
            "description": "Research and build a working model",
            "target_date": (datetime.utcnow() + timedelta(days=25)).isoformat(),
            "progress": 60,
            "status": "on_track",
            "created_at": (datetime.utcnow() - timedelta(days=15)).isoformat()
        }
    ]

    if child_id:
        goals = [g for g in goals if g["child_id"] == child_id]

    return goals

@parent_router.post("/set-goal")
async def set_learning_goal(goal_data: dict, user=Depends(_current_user)):
    """Set a new learning goal for a child"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Create goal record
    goal = {
        "_id": _uuid(),
        "parent_id": user["id"],
        "child_id": goal_data.get("child_id"),
        "title": goal_data.get("title"),
        "description": goal_data.get("description"),
        "target_date": goal_data.get("target_date"),
        "progress": 0,
        "status": "active",
        "created_at": datetime.utcnow().isoformat()
    }

    # Save goal
    await db.learning_goals.insert_one(goal)

    return {
        "goal_id": goal["_id"],
        "status": "created",
        "message": "Learning goal set successfully"
    }

@parent_router.get("/academic-alerts")
async def get_academic_alerts(child_id: Optional[str] = None, user=Depends(_current_user)):
    """Get academic alerts for children"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Get academic alerts
    alerts = [
        {
            "_id": _uuid(),
            "child_id": "student1",
            "type": "warning",
            "title": "Low Engagement in Physics",
            "message": "Emma has not accessed Physics materials for 3 days",
            "severity": "medium",
            "timestamp": (datetime.utcnow() - timedelta(hours=4)).isoformat(),
            "acknowledged": False
        },
        {
            "_id": _uuid(),
            "child_id": "student2",
            "type": "success",
            "title": "Excellent Progress in English",
            "message": "Alex improved his reading comprehension score by 15%",
            "severity": "low",
            "timestamp": (datetime.utcnow() - timedelta(hours=8)).isoformat(),
            "acknowledged": True
        }
    ]

    if child_id:
        alerts = [a for a in alerts if a["child_id"] == child_id]

    return alerts

@parent_router.post("/acknowledge-alert")
async def acknowledge_alert(alert_id: str, user=Depends(_current_user)):
    """Acknowledge an academic alert"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Update alert acknowledgment
    result = await db.alerts.update_one(
        {"_id": alert_id},
        {"$set": {"acknowledged": True, "acknowledged_at": datetime.utcnow().isoformat()}}
    )

    if result.modified_count == 0:
        raise HTTPException(404, "Alert not found")

    return {"status": "acknowledged", "alert_id": alert_id}

@parent_router.get("/parent-resources")
async def get_parent_resources(category: Optional[str] = None, user=Depends(_current_user)):
    """Get resources for parents"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Get parent resources
    resources = [
        {
            "_id": _uuid(),
            "title": "Supporting Your Child's Online Learning",
            "type": "guide",
            "description": "Tips for parents to help their children succeed in online education",
            "download_url": "#",
            "category": "parenting",
            "tags": ["online learning", "parent support", "education"]
        },
        {
            "_id": _uuid(),
            "title": "Understanding Academic Progress Reports",
            "type": "video",
            "description": "Learn how to interpret your child's progress reports",
            "download_url": "#",
            "category": "academic",
            "tags": ["progress reports", "grades", "assessment"]
        },
        {
            "_id": _uuid(),
            "title": "Homework Help Strategies",
            "type": "webinar",
            "description": "Effective strategies for helping with homework",
            "download_url": "#",
            "category": "support",
            "tags": ["homework", "study skills", "parent involvement"]
        },
        {
            "_id": _uuid(),
            "title": "Digital Wellness for Students",
            "type": "guide",
            "description": "Maintaining healthy screen time and online habits",
            "download_url": "#",
            "category": "wellness",
            "tags": ["digital wellness", "screen time", "online safety"]
        }
    ]

    if category:
        resources = [r for r in resources if r["category"] == category]

    return resources

@parent_router.get("/study-plans")
async def get_study_plans(child_id: Optional[str] = None, user=Depends(_current_user)):
    """Get study plans for children"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Get study plans
    plans = [
        {
            "_id": _uuid(),
            "child_id": "student1",
            "title": "Weekly Study Schedule",
            "description": "Balanced study plan for Emma's courses",
            "subjects": ["Math", "Physics", "English"],
            "total_hours": 15,
            "completed_hours": 12,
            "status": "active",
            "created_at": (datetime.utcnow() - timedelta(days=7)).isoformat()
        },
        {
            "_id": _uuid(),
            "child_id": "student2",
            "title": "Exam Preparation Plan",
            "description": "Intensive preparation for mid-term exams",
            "subjects": ["Math", "Science", "History"],
            "total_hours": 20,
            "completed_hours": 8,
            "status": "active",
            "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat()
        }
    ]

    if child_id:
        plans = [p for p in plans if p["child_id"] == child_id]

    return plans

@parent_router.get("/support-tickets")
async def get_support_tickets(child_id: Optional[str] = None, user=Depends(_current_user)):
    """Get support tickets for parent assistance"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Get support tickets
    tickets = [
        {
            "_id": _uuid(),
            "child_id": "student1",
            "title": "Technical Issue with Assignment Submission",
            "description": "Emma is having trouble uploading her math assignment",
            "status": "resolved",
            "priority": "high",
            "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
            "resolved_at": (datetime.utcnow() - timedelta(hours=4)).isoformat()
        },
        {
            "_id": _uuid(),
            "child_id": "student2",
            "title": "Question About Course Content",
            "description": "Alex needs clarification on physics chapter 3",
            "status": "in_progress",
            "priority": "medium",
            "created_at": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
            "resolved_at": None
        }
    ]

    if child_id:
        tickets = [t for t in tickets if t["child_id"] == child_id]

    return tickets

@parent_router.post("/create-support-ticket")
async def create_support_ticket(ticket_data: dict, user=Depends(_current_user)):
    """Create a new support ticket"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Create support ticket
    ticket = {
        "_id": _uuid(),
        "parent_id": user["id"],
        "child_id": ticket_data.get("child_id"),
        "title": ticket_data.get("title"),
        "description": ticket_data.get("description"),
        "category": ticket_data.get("category", "general"),
        "priority": ticket_data.get("priority", "medium"),
        "status": "open",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

    # Save ticket
    await db.support_tickets.insert_one(ticket)

    return {
        "ticket_id": ticket["_id"],
        "status": "created",
        "message": "Support ticket created successfully"
    }

@parent_router.post("/schedule-meeting")
async def schedule_parent_teacher_meeting(meeting_data: dict, user=Depends(_current_user)):
    """Schedule a parent-teacher meeting"""
    db = get_database()

    # Check if user is a parent
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "parent":
        raise HTTPException(403, "Parent access required")

    # Create meeting record
    meeting = {
        "_id": _uuid(),
        "parent_id": user["id"],
        "child_id": meeting_data.get("child_id"),
        "teacher_id": meeting_data.get("teacher_id"),
        "scheduled_date": meeting_data.get("scheduled_date"),
        "duration": meeting_data.get("duration", 30),
        "topic": meeting_data.get("topic"),
        "meeting_type": meeting_data.get("meeting_type", "virtual"),
        "status": "scheduled",
        "created_at": datetime.utcnow().isoformat()
    }

    # Save meeting
    await db.meetings.insert_one(meeting)

    return {
        "meeting_id": meeting["_id"],
        "status": "scheduled",
        "message": "Parent-teacher meeting scheduled successfully"
    }