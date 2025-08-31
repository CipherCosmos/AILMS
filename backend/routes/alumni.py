from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from database import get_database, _uuid
from auth import _current_user
from models import UserProfile, CareerProfile

alumni_router = APIRouter()

@alumni_router.get("/directory")
async def get_alumni_directory(search: Optional[str] = None, industry: Optional[str] = None,
                             graduation_year: Optional[int] = None, location: Optional[str] = None,
                             skills: Optional[str] = None, user=Depends(_current_user)):
    """Get alumni directory with filtering"""
    db = get_database()

    # Check if user has alumni access
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["alumni", "student", "instructor", "admin"]:
        raise HTTPException(403, "Access denied")

    # Build query
    query = {"role": "alumni"}

    if industry:
        query["career_profile.target_industries"] = {"$in": [industry]}

    if graduation_year:
        query["student_profile.graduation_year"] = graduation_year

    if location:
        query["user_profile.location"] = {"$regex": location, "$options": "i"}

    if skills:
        query["user_profile.skills"] = {"$in": [skills]}

    # Get alumni users
    alumni_users = await db.users.find(query).to_list(100)

    # Enrich with profile data
    enriched_alumni = []
    for alumni_user in alumni_users:
        # Get user profile
        user_profile = await db.user_profiles.find_one({"user_id": alumni_user["_id"]})

        # Get career profile
        career_profile = await db.career_profiles.find_one({"user_id": alumni_user["_id"]})

        # Get student profile for graduation info
        student_profile = await db.student_profiles.find_one({"user_id": alumni_user["_id"]})

        alumni_data = {
            "id": alumni_user["_id"],
            "name": alumni_user["name"],
            "email": alumni_user["email"],
            "current_position": career_profile.get("current_position") if career_profile else None,
            "company": career_profile.get("company") if career_profile else None,
            "industry": career_profile.get("target_industries", []) if career_profile else [],
            "graduation_year": student_profile.get("graduation_year") if student_profile else None,
            "location": user_profile.get("location") if user_profile else None,
            "skills": user_profile.get("skills", []) if user_profile else [],
            "bio": user_profile.get("bio") if user_profile else None,
            "available_for_mentoring": career_profile.get("available_for_mentoring", False) if career_profile else False,
            "linkedin_profile": career_profile.get("linkedin_profile") if career_profile else None
        }

        # Apply search filter
        if search:
            search_lower = search.lower()
            if (search_lower in alumni_data["name"].lower() or
                (alumni_data["current_position"] and search_lower in alumni_data["current_position"].lower()) or
                (alumni_data["company"] and search_lower in alumni_data["company"].lower()) or
                any(search_lower in skill.lower() for skill in alumni_data["skills"])):
                enriched_alumni.append(alumni_data)
        else:
            enriched_alumni.append(alumni_data)

    return enriched_alumni

@alumni_router.post("/mentorship/request/{mentor_id}")
async def request_mentorship(mentor_id: str, request_data: dict, user=Depends(_current_user)):
    """Request mentorship from an alumni"""
    db = get_database()

    # Check if mentor exists and is alumni
    mentor = await db.users.find_one({"_id": mentor_id, "role": "alumni"})
    if not mentor:
        raise HTTPException(404, "Mentor not found")

    # Check if user is not requesting mentorship from themselves
    if user["id"] == mentor_id:
        raise HTTPException(400, "Cannot request mentorship from yourself")

    # Check if request already exists
    existing_request = await db.mentorship_requests.find_one({
        "mentee_id": user["id"],
        "mentor_id": mentor_id,
        "status": {"$in": ["pending", "accepted"]}
    })

    if existing_request:
        raise HTTPException(400, "Mentorship request already exists")

    # Create mentorship request
    mentorship_request = {
        "_id": _uuid(),
        "mentee_id": user["id"],
        "mentor_id": mentor_id,
        "message": request_data.get("message", ""),
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    await db.mentorship_requests.insert_one(mentorship_request)

    return {"status": "request_sent", "request_id": mentorship_request["_id"]}

@alumni_router.get("/mentorship/requests")
async def get_mentorship_requests(user=Depends(_current_user)):
    """Get mentorship requests for the current user"""
    db = get_database()

    # Get requests where user is the mentor
    mentor_requests = await db.mentorship_requests.find({
        "mentor_id": user["id"]
    }).to_list(50)

    # Get requests where user is the mentee
    mentee_requests = await db.mentorship_requests.find({
        "mentee_id": user["id"]
    }).to_list(50)

    # Enrich mentor requests with mentee info
    enriched_mentor_requests = []
    for request in mentor_requests:
        mentee = await db.users.find_one({"_id": request["mentee_id"]})
        if mentee:
            enriched_request = {
                "id": request["_id"],
                "mentee_name": mentee["name"],
                "mentee_email": mentee["email"],
                "message": request["message"],
                "status": request["status"],
                "created_at": request["created_at"],
                "updated_at": request["updated_at"]
            }
            enriched_mentor_requests.append(enriched_request)

    # Enrich mentee requests with mentor info
    enriched_mentee_requests = []
    for request in mentee_requests:
        mentor = await db.users.find_one({"_id": request["mentor_id"]})
        if mentor:
            enriched_request = {
                "id": request["_id"],
                "mentor_name": mentor["name"],
                "mentor_email": mentor["email"],
                "message": request["message"],
                "status": request["status"],
                "created_at": request["created_at"],
                "updated_at": request["updated_at"]
            }
            enriched_mentee_requests.append(enriched_request)

    return {
        "as_mentor": enriched_mentor_requests,
        "as_mentee": enriched_mentee_requests
    }

@alumni_router.post("/mentorship/respond/{request_id}")
async def respond_to_mentorship_request(request_id: str, response: dict, user=Depends(_current_user)):
    """Respond to a mentorship request"""
    db = get_database()

    # Find the request
    request = await db.mentorship_requests.find_one({"_id": request_id})
    if not request:
        raise HTTPException(404, "Request not found")

    # Check if user is the mentor
    if request["mentor_id"] != user["id"]:
        raise HTTPException(403, "Not authorized to respond to this request")

    # Update request status
    new_status = response.get("status", "accepted")
    if new_status not in ["accepted", "declined"]:
        raise HTTPException(400, "Invalid status")

    await db.mentorship_requests.update_one(
        {"_id": request_id},
        {
            "$set": {
                "status": new_status,
                "updated_at": datetime.utcnow()
            }
        }
    )

    # If accepted, create mentorship relationship
    if new_status == "accepted":
        mentorship = {
            "_id": _uuid(),
            "mentor_id": request["mentor_id"],
            "mentee_id": request["mentee_id"],
            "started_at": datetime.utcnow(),
            "status": "active"
        }
        await db.mentorships.insert_one(mentorship)

    return {"status": "response_recorded"}

@alumni_router.get("/events")
async def get_alumni_events(user=Depends(_current_user)):
    """Get alumni events"""
    db = get_database()

    # Check if user has access to alumni events
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["alumni", "student", "instructor", "admin"]:
        raise HTTPException(403, "Access denied")

    events = await db.alumni_events.find({}).to_list(50)

    # Enrich with registration status
    enriched_events = []
    for event in events:
        registration = await db.event_registrations.find_one({
            "event_id": event["_id"],
            "user_id": user["id"]
        })

        enriched_event = {
            "id": event["_id"],
            "title": event["title"],
            "description": event["description"],
            "date": event["date"],
            "time": event["time"],
            "location": event.get("location"),
            "type": event.get("type", "in_person"),
            "attendee_count": event.get("attendee_count", 0),
            "max_attendees": event.get("max_attendees"),
            "is_registered": registration is not None,
            "created_at": event["created_at"]
        }
        enriched_events.append(enriched_event)

    return enriched_events

@alumni_router.post("/events/{event_id}/join")
async def join_alumni_event(event_id: str, user=Depends(_current_user)):
    """Join an alumni event"""
    db = get_database()

    # Check if event exists
    event = await db.alumni_events.find_one({"_id": event_id})
    if not event:
        raise HTTPException(404, "Event not found")

    # Check if user is already registered
    existing_registration = await db.event_registrations.find_one({
        "event_id": event_id,
        "user_id": user["id"]
    })

    if existing_registration:
        raise HTTPException(400, "Already registered for this event")

    # Check capacity
    current_count = await db.event_registrations.count_documents({"event_id": event_id})
    if event.get("max_attendees") and current_count >= event["max_attendees"]:
        raise HTTPException(400, "Event is at capacity")

    # Create registration
    registration = {
        "_id": _uuid(),
        "event_id": event_id,
        "user_id": user["id"],
        "registered_at": datetime.utcnow(),
        "status": "confirmed"
    }

    await db.event_registrations.insert_one(registration)

    # Update attendee count
    await db.alumni_events.update_one(
        {"_id": event_id},
        {"$inc": {"attendee_count": 1}}
    )

    return {"status": "registered"}

@alumni_router.get("/opportunities")
async def get_alumni_opportunities(user=Depends(_current_user)):
    """Get career opportunities shared by alumni"""
    db = get_database()

    # Check if user has access
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["alumni", "student", "instructor", "admin"]:
        raise HTTPException(403, "Access denied")

    opportunities = await db.alumni_opportunities.find({
        "is_active": True
    }).to_list(50)

    # Enrich with poster information
    enriched_opportunities = []
    for opp in opportunities:
        poster = await db.users.find_one({"_id": opp["posted_by"]})
        if poster:
            enriched_opp = {
                "id": opp["_id"],
                "title": opp["title"],
                "company": opp["company"],
                "description": opp["description"],
                "location": opp["location"],
                "salary_range": opp.get("salary_range"),
                "job_type": opp["job_type"],
                "requirements": opp.get("requirements", []),
                "skills_required": opp.get("skills_required", []),
                "posted_by_name": poster["name"],
                "posted_by_graduation": None,  # Would need to get from student profile
                "posted_at": opp["created_at"],
                "application_deadline": opp.get("application_deadline")
            }
            enriched_opportunities.append(enriched_opp)

    return enriched_opportunities

@alumni_router.post("/opportunities")
async def post_alumni_opportunity(opportunity_data: dict, user=Depends(_current_user)):
    """Post a career opportunity (alumni only)"""
    db = get_database()

    # Check if user is alumni
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "alumni":
        raise HTTPException(403, "Only alumni can post opportunities")

    opportunity = {
        "_id": _uuid(),
        "title": opportunity_data["title"],
        "company": opportunity_data["company"],
        "description": opportunity_data["description"],
        "location": opportunity_data["location"],
        "salary_range": opportunity_data.get("salary_range"),
        "job_type": opportunity_data.get("job_type", "full_time"),
        "requirements": opportunity_data.get("requirements", []),
        "skills_required": opportunity_data.get("skills_required", []),
        "posted_by": user["id"],
        "is_active": True,
        "created_at": datetime.utcnow(),
        "application_deadline": opportunity_data.get("application_deadline")
    }

    await db.alumni_opportunities.insert_one(opportunity)

    return {"status": "posted", "opportunity_id": opportunity["_id"]}

@alumni_router.get("/network/stats")
async def get_alumni_network_stats(user=Depends(_current_user)):
    """Get alumni network statistics"""
    db = get_database()

    # Check if user has access
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["alumni", "student", "instructor", "admin"]:
        raise HTTPException(403, "Access denied")

    # Get basic stats
    total_alumni = await db.users.count_documents({"role": "alumni"})
    active_mentors = await db.users.count_documents({
        "role": "alumni",
        "career_profile.available_for_mentoring": True
    })
    total_events = await db.alumni_events.count_documents({})
    total_opportunities = await db.alumni_opportunities.count_documents({"is_active": True})

    # Get user's network stats
    user_mentorships = await db.mentorships.count_documents({
        "$or": [
            {"mentor_id": user["id"]},
            {"mentee_id": user["id"]}
        ]
    })

    user_event_registrations = await db.event_registrations.count_documents({
        "user_id": user["id"]
    })

    return {
        "network_stats": {
            "total_alumni": total_alumni,
            "active_mentors": active_mentors,
            "total_events": total_events,
            "total_opportunities": total_opportunities
        },
        "user_stats": {
            "mentorships": user_mentorships,
            "event_registrations": user_event_registrations
        }
    }