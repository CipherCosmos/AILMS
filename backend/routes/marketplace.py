from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from database import get_database, get_fs_bucket, _uuid
from auth import _current_user
from models import (
    CourseMarketplace, CoursePurchase, JobPosting, InternshipProject,
    CareerProfile, Badge, UserBadge, Leaderboard
)
from config import settings

marketplace_router = APIRouter()

# Course Marketplace
@marketplace_router.post("/courses/marketplace")
async def list_course_on_marketplace(listing_data: dict, user=Depends(_current_user)):
    """List a course on the marketplace"""
    db = get_database()

    # Verify course ownership
    course = await db.courses.find_one({"_id": listing_data["course_id"]})
    if not course:
        raise HTTPException(404, "Course not found")

    if course["owner_id"] != user["id"]:
        raise HTTPException(403, "Not authorized to list this course")

    # Check if already listed
    existing = await db.course_marketplace.find_one({"course_id": listing_data["course_id"]})
    if existing:
        raise HTTPException(400, "Course already listed on marketplace")

    listing = CourseMarketplace(
        course_id=listing_data["course_id"],
        seller_tenant_id=listing_data["seller_tenant_id"],
        price=listing_data["price"],
        currency=listing_data.get("currency", "USD"),
        license_type=listing_data.get("license_type", "single_use"),
        description=listing_data.get("description", ""),
        tags=listing_data.get("tags", []),
        is_active=True
    )

    doc = listing.dict()
    doc["_id"] = listing.id
    await db.course_marketplace.insert_one(doc)

    return listing


@marketplace_router.get("/courses/marketplace")
async def browse_marketplace(search: Optional[str] = None, category: Optional[str] = None,
                           min_price: Optional[float] = None, max_price: Optional[float] = None,
                           sort_by: str = "rating", user=Depends(_current_user)):
    """Browse courses on the marketplace"""
    db = get_database()

    query = {"is_active": True}

    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}}
        ]

    if category:
        query["tags"] = {"$in": [category]}

    if min_price is not None or max_price is not None:
        price_query = {}
        if min_price is not None:
            price_query["$gte"] = min_price
        if max_price is not None:
            price_query["$lte"] = max_price
        query["price"] = price_query

    # Get marketplace listings with course details
    pipeline = [
        {"$match": query},
        {
            "$lookup": {
                "from": "courses",
                "localField": "course_id",
                "foreignField": "_id",
                "as": "course"
            }
        },
        {"$unwind": "$course"},
        {"$match": {"course.published": True}},  # Only published courses
        {"$sort": {sort_by: -1}},
        {"$limit": 50}
    ]

    listings = await db.course_marketplace.aggregate(pipeline).to_list(50)

    return listings


@marketplace_router.post("/courses/marketplace/{listing_id}/purchase")
async def purchase_course(listing_id: str, payment_data: dict, user=Depends(_current_user)):
    """Purchase a course from the marketplace"""
    db = get_database()

    # Get listing
    listing = await db.course_marketplace.find_one({"_id": listing_id})
    if not listing:
        raise HTTPException(404, "Listing not found")

    if not listing["is_active"]:
        raise HTTPException(400, "Listing is not active")

    # Check if already purchased
    existing_purchase = await db.course_purchases.find_one({
        "buyer_tenant_id": payment_data["buyer_tenant_id"],
        "marketplace_id": listing_id
    })

    if existing_purchase:
        raise HTTPException(400, "Course already purchased")

    # Process payment (simplified - in production, integrate with payment processor)
    # Here we would integrate with Stripe, PayPal, etc.

    purchase = CoursePurchase(
        buyer_tenant_id=payment_data["buyer_tenant_id"],
        marketplace_id=listing_id,
        purchase_price=listing["price"],
        license_key=_uuid(),
        purchased_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=365) if listing["license_type"] == "single_use" else None
    )

    doc = purchase.dict()
    doc["_id"] = purchase.id
    await db.course_purchases.insert_one(doc)

    # Grant access to the course
    await _grant_course_access(payment_data["buyer_tenant_id"], listing["course_id"])

    return purchase


# Career Services
@marketplace_router.post("/jobs")
async def post_job(job_data: dict, user=Depends(_current_user)):
    """Post a job listing"""
    db = get_database()

    # Check permissions
    if not await _can_post_jobs(user["id"], job_data.get("tenant_id")):
        raise HTTPException(403, "Insufficient permissions")

    job = JobPosting(
        tenant_id=job_data["tenant_id"],
        title=job_data["title"],
        company=job_data["company"],
        description=job_data["description"],
        requirements=job_data.get("requirements", []),
        skills_required=job_data.get("skills_required", []),
        location=job_data["location"],
        salary_range=job_data.get("salary_range"),
        job_type=job_data.get("job_type", "full_time"),
        posted_by=user["id"],
        is_active=True
    )

    doc = job.dict()
    doc["_id"] = job.id
    await db.job_postings.insert_one(doc)

    return job


@marketplace_router.get("/jobs")
async def search_jobs(search: Optional[str] = None, location: Optional[str] = None,
                     job_type: Optional[str] = None, skills: Optional[List[str]] = None,
                     user=Depends(_current_user)):
    """Search job postings"""
    db = get_database()

    query = {"is_active": True}

    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]

    if location:
        query["location"] = {"$regex": location, "$options": "i"}

    if job_type:
        query["job_type"] = job_type

    if skills:
        query["skills_required"] = {"$in": skills}

    jobs = await db.job_postings.find(query).sort("created_at", -1).to_list(50)

    return jobs


@marketplace_router.post("/internships")
async def post_internship(internship_data: dict, user=Depends(_current_user)):
    """Post an internship project"""
    db = get_database()

    if not await _can_post_jobs(user["id"], internship_data.get("tenant_id")):
        raise HTTPException(403, "Insufficient permissions")

    internship = InternshipProject(
        tenant_id=internship_data["tenant_id"],
        title=internship_data["title"],
        company=internship_data["company"],
        description=internship_data["description"],
        skills_developed=internship_data.get("skills_developed", []),
        duration_weeks=internship_data["duration_weeks"],
        compensation=internship_data.get("compensation"),
        remote_allowed=internship_data.get("remote_allowed", True),
        posted_by=user["id"],
        is_active=True
    )

    doc = internship.dict()
    doc["_id"] = internship.id
    await db.internship_projects.insert_one(doc)

    return internship


@marketplace_router.get("/internships")
async def search_internships(search: Optional[str] = None, skills: Optional[List[str]] = None,
                           remote_only: bool = False, user=Depends(_current_user)):
    """Search internship projects"""
    db = get_database()

    query = {"is_active": True}

    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]

    if skills:
        query["skills_developed"] = {"$in": skills}

    if remote_only:
        query["remote_allowed"] = True

    internships = await db.internship_projects.find(query).sort("created_at", -1).to_list(50)

    return internships


# Career Profile Management
@marketplace_router.post("/career/profile")
async def update_career_profile(profile_data: dict, user=Depends(_current_user)):
    """Update user's career profile"""
    db = get_database()

    career_profile = CareerProfile(
        user_id=user["id"],
        career_goals=profile_data.get("career_goals", []),
        target_industries=profile_data.get("target_industries", []),
        target_roles=profile_data.get("target_roles", []),
        skills_to_develop=profile_data.get("skills_to_develop", []),
        resume_data=profile_data.get("resume_data", {}),
        linkedin_profile=profile_data.get("linkedin_profile"),
        portfolio_url=profile_data.get("portfolio_url"),
        mentor_ids=profile_data.get("mentor_ids", [])
    )

    doc = career_profile.dict()
    await db.career_profiles.update_one(
        {"user_id": user["id"]},
        {"$set": doc},
        upsert=True
    )

    return career_profile


@marketplace_router.get("/career/matches")
async def get_career_matches(user=Depends(_current_user)):
    """Get personalized career matches (jobs, internships, courses)"""
    db = get_database()

    # Get user's career profile
    profile = await db.career_profiles.find_one({"user_id": user["id"]})
    if not profile:
        return {"matches": [], "message": "Complete your career profile for better matches"}

    # Find matching jobs
    job_matches = []
    if profile.get("target_roles"):
        jobs = await db.job_postings.find({
            "title": {"$in": profile["target_roles"]},
            "is_active": True
        }).to_list(10)
        job_matches = jobs

    # Find matching internships
    internship_matches = []
    if profile.get("skills_to_develop"):
        internships = await db.internship_projects.find({
            "skills_developed": {"$in": profile["skills_to_develop"]},
            "is_active": True
        }).to_list(10)
        internship_matches = internships

    # Find matching courses
    course_matches = []
    if profile.get("skills_to_develop"):
        # Search for courses that teach the required skills
        courses = await db.courses.find({
            "$or": [
                {"title": {"$regex": "|".join(profile["skills_to_develop"]), "$options": "i"}},
                {"description": {"$regex": "|".join(profile["skills_to_develop"]), "$options": "i"}}
            ],
            "published": True
        }).to_list(10)
        course_matches = courses

    return {
        "job_matches": job_matches,
        "internship_matches": internship_matches,
        "course_matches": course_matches,
        "profile_complete": bool(profile.get("career_goals"))
    }


# Gamification System
@marketplace_router.post("/badges")
async def create_badge(badge_data: dict, user=Depends(_current_user)):
    """Create a new badge"""
    db = get_database()

    if not await _can_manage_badges(user["id"], badge_data.get("tenant_id")):
        raise HTTPException(403, "Insufficient permissions")

    badge = Badge(
        tenant_id=badge_data["tenant_id"],
        name=badge_data["name"],
        description=badge_data["description"],
        icon_url=badge_data["icon_url"],
        category=badge_data["category"],
        criteria=badge_data.get("criteria", {}),
        points_value=badge_data.get("points_value", 0),
        rarity=badge_data.get("rarity", "common")
    )

    doc = badge.dict()
    doc["_id"] = badge.id
    await db.badges.insert_one(doc)

    return badge


@marketplace_router.post("/badges/{badge_id}/award")
async def award_badge(badge_id: str, recipient_id: str, user=Depends(_current_user)):
    """Award a badge to a user"""
    db = get_database()

    # Check if badge exists
    badge = await db.badges.find_one({"_id": badge_id})
    if not badge:
        raise HTTPException(404, "Badge not found")

    # Check permissions
    if not await _can_award_badges(user["id"], badge["tenant_id"]):
        raise HTTPException(403, "Insufficient permissions")

    # Check if already awarded
    existing = await db.user_badges.find_one({
        "user_id": recipient_id,
        "badge_id": badge_id
    })

    if existing:
        raise HTTPException(400, "Badge already awarded")

    user_badge = UserBadge(
        user_id=recipient_id,
        badge_id=badge_id,
        earned_reason=f"Awarded by {user['name']}"
    )

    doc = user_badge.dict()
    doc["_id"] = user_badge.id
    await db.user_badges.insert_one(doc)

    return user_badge


@marketplace_router.get("/leaderboards/{type}")
async def get_leaderboard(type: str, period: str = "all_time", tenant_id: Optional[str] = None,
                         user=Depends(_current_user)):
    """Get leaderboard for specified type and period"""
    db = get_database()

    if tenant_id and not await _has_tenant_access(user["id"], tenant_id):
        raise HTTPException(403, "Access denied")

    # This is a simplified implementation
    # In production, you'd calculate real-time leaderboards
    leaderboard = await db.leaderboards.find_one({
        "type": type,
        "period": period,
        "tenant_id": tenant_id
    })

    if not leaderboard:
        # Generate sample leaderboard
        leaderboard = {
            "_id": _uuid(),
            "type": type,
            "period": period,
            "tenant_id": tenant_id,
            "entries": [
                {"user_id": "sample1", "name": "Alice Johnson", "score": 1250, "rank": 1},
                {"user_id": "sample2", "name": "Bob Smith", "score": 1180, "rank": 2},
                {"user_id": "sample3", "name": "Carol Davis", "score": 1050, "rank": 3}
            ],
            "last_updated": datetime.utcnow()
        }

    return leaderboard


# Payment Processing (Simplified)
@marketplace_router.post("/payments/process")
async def process_payment(payment_data: dict, user=Depends(_current_user)):
    """Process payment for marketplace purchases"""
    # In production, integrate with Stripe, PayPal, etc.
    # This is a simplified implementation

    payment = {
        "_id": _uuid(),
        "user_id": user["id"],
        "amount": payment_data["amount"],
        "currency": payment_data.get("currency", "USD"),
        "description": payment_data["description"],
        "status": "completed",  # In production, this would be pending until confirmed
        "transaction_id": f"txn_{_uuid()}",
        "processed_at": datetime.utcnow()
    }

    db = get_database()
    await db.payments.insert_one(payment)

    return payment


# Helper functions
async def _can_post_jobs(user_id: str, tenant_id: str) -> bool:
    """Check if user can post jobs"""
    from routes.rbac import check_permission
    return await check_permission(user_id, "jobs:post", tenant_id)


async def _has_tenant_access(user_id: str, tenant_id: str) -> bool:
    """Check if user has access to tenant"""
    from routes.rbac import check_permission
    return await check_permission(user_id, "tenant:access", tenant_id)


async def _can_manage_badges(user_id: str, tenant_id: str) -> bool:
    """Check if user can manage badges"""
    from routes.rbac import check_permission
    return await check_permission(user_id, "badges:manage", tenant_id)


async def _can_award_badges(user_id: str, tenant_id: str) -> bool:
    """Check if user can award badges"""
    from routes.rbac import check_permission
    return await check_permission(user_id, "badges:award", tenant_id)


async def _grant_course_access(tenant_id: str, course_id: str):
    """Grant course access to tenant users"""
    # Implementation for granting course access to all users in a tenant
    # This would typically involve bulk enrollment operations
    pass