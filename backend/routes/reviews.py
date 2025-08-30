from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional
from database import get_database
from auth import _current_user, _require_role
from models import CourseReview, ReviewVote, CourseDiscussion, DiscussionPost, DiscussionVote
from datetime import datetime
import uuid

reviews_router = APIRouter()


# Course Reviews
@reviews_router.post("/courses/{course_id}/reviews")
async def create_course_review(
    course_id: str,
    review_data: dict,
    user=Depends(_current_user)
):
    """Create a course review"""
    db = get_database()

    # Check if user is enrolled in the course
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(404, "Course not found")

    if user["id"] not in course.get("enrolled_user_ids", []):
        raise HTTPException(403, "Must be enrolled to review course")

    # Check if user already reviewed
    existing_review = await db.course_reviews.find_one({
        "course_id": course_id,
        "user_id": user["id"]
    })
    if existing_review:
        raise HTTPException(400, "Already reviewed this course")

    review = CourseReview(
        course_id=course_id,
        user_id=user["id"],
        rating=review_data["rating"],
        title=review_data["title"],
        content=review_data["content"],
        pros=review_data.get("pros", []),
        cons=review_data.get("cons", [])
    )

    await db.course_reviews.insert_one(review.dict())
    return {"message": "Review created successfully"}


@reviews_router.get("/courses/{course_id}/reviews")
async def get_course_reviews(course_id: str, user=Depends(_current_user)):
    """Get all reviews for a course"""
    db = get_database()

    reviews = await db.course_reviews.find({"course_id": course_id}).to_list(100)

    # Enrich with user data
    for review in reviews:
        user_data = await db.users.find_one({"_id": review["user_id"]})
        if user_data:
            review["user_name"] = user_data["name"]
            review["user_role"] = user_data["role"]

    return reviews


@reviews_router.put("/reviews/{review_id}")
async def update_course_review(
    review_id: str,
    review_data: dict,
    user=Depends(_current_user)
):
    """Update a course review"""
    db = get_database()

    review = await db.course_reviews.find_one({"_id": review_id})
    if not review:
        raise HTTPException(404, "Review not found")

    if review["user_id"] != user["id"]:
        raise HTTPException(403, "Can only edit own reviews")

    await db.course_reviews.update_one(
        {"_id": review_id},
        {"$set": {
            "rating": review_data.get("rating", review["rating"]),
            "title": review_data.get("title", review["title"]),
            "content": review_data.get("content", review["content"]),
            "pros": review_data.get("pros", review["pros"]),
            "cons": review_data.get("cons", review["cons"]),
            "updated_at": datetime.utcnow()
        }}
    )

    return {"message": "Review updated successfully"}


@reviews_router.delete("/reviews/{review_id}")
async def delete_course_review(review_id: str, user=Depends(_current_user)):
    """Delete a course review"""
    db = get_database()

    review = await db.course_reviews.find_one({"_id": review_id})
    if not review:
        raise HTTPException(404, "Review not found")

    if review["user_id"] != user["id"] and user["role"] not in ["admin", "instructor"]:
        raise HTTPException(403, "Can only delete own reviews")

    await db.course_reviews.delete_one({"_id": review_id})
    return {"message": "Review deleted successfully"}


@reviews_router.post("/reviews/{review_id}/vote")
async def vote_on_review(review_id: str, vote_data: dict, user=Depends(_current_user)):
    """Vote on a review (helpful/not helpful)"""
    db = get_database()

    vote_type = vote_data["vote_type"]  # "helpful" or "not_helpful"

    # Check if already voted
    existing_vote = await db.review_votes.find_one({
        "review_id": review_id,
        "user_id": user["id"]
    })

    if existing_vote:
        if existing_vote["vote_type"] == vote_type:
            # Remove vote if same type
            await db.review_votes.delete_one({"_id": existing_vote["_id"]})
            # Update review count
            if vote_type == "helpful":
                await db.course_reviews.update_one(
                    {"_id": review_id},
                    {"$inc": {"helpful_votes": -1}}
                )
        else:
            # Change vote type
            await db.review_votes.update_one(
                {"_id": existing_vote["_id"]},
                {"$set": {"vote_type": vote_type}}
            )
            # Update review count
            if vote_type == "helpful":
                await db.course_reviews.update_one(
                    {"_id": review_id},
                    {"$inc": {"helpful_votes": 1}}
                )
            else:
                await db.course_reviews.update_one(
                    {"_id": review_id},
                    {"$inc": {"helpful_votes": -1}}
                )
    else:
        # New vote
        vote = ReviewVote(
            review_id=review_id,
            user_id=user["id"],
            vote_type=vote_type
        )
        await db.review_votes.insert_one(vote.dict())

        if vote_type == "helpful":
            await db.course_reviews.update_one(
                {"_id": review_id},
                {"$inc": {"helpful_votes": 1}}
            )

    return {"message": "Vote recorded"}


# Course Discussions/Q&A
@reviews_router.post("/courses/{course_id}/discussions")
async def create_discussion(
    course_id: str,
    discussion_data: dict,
    user=Depends(_current_user)
):
    """Create a new discussion thread"""
    db = get_database()

    # Check if user is enrolled or is instructor
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(404, "Course not found")

    if user["role"] not in ["admin", "instructor"] and user["id"] not in course.get("enrolled_user_ids", []):
        raise HTTPException(403, "Must be enrolled to create discussions")

    discussion = CourseDiscussion(
        course_id=course_id,
        user_id=user["id"],
        title=discussion_data["title"],
        content=discussion_data["content"],
        discussion_type=discussion_data.get("discussion_type", "question"),
        tags=discussion_data.get("tags", [])
    )

    result = await db.course_discussions.insert_one(discussion.dict())
    return {"message": "Discussion created", "discussion_id": str(result.inserted_id)}


@reviews_router.get("/courses/{course_id}/discussions")
async def get_course_discussions(
    course_id: str,
    discussion_type: Optional[str] = None,
    user=Depends(_current_user)
):
    """Get all discussions for a course"""
    db = get_database()

    query = {"course_id": course_id}
    if discussion_type:
        query["discussion_type"] = discussion_type

    discussions = await db.course_discussions.find(query).sort("created_at", -1).to_list(100)

    # Enrich with user data and reply counts
    for discussion in discussions:
        user_data = await db.users.find_one({"_id": discussion["user_id"]})
        if user_data:
            discussion["user_name"] = user_data["name"]
            discussion["user_role"] = user_data["role"]

        # Get reply count
        reply_count = await db.discussion_posts.count_documents({"discussion_id": discussion["_id"]})
        discussion["reply_count"] = reply_count

    return discussions


@reviews_router.get("/discussions/{discussion_id}")
async def get_discussion_details(discussion_id: str, user=Depends(_current_user)):
    """Get discussion details with all replies"""
    db = get_database()

    discussion = await db.course_discussions.find_one({"_id": discussion_id})
    if not discussion:
        raise HTTPException(404, "Discussion not found")

    # Increment view count
    await db.course_discussions.update_one(
        {"_id": discussion_id},
        {"$inc": {"view_count": 1}}
    )

    # Get all replies
    replies = await db.discussion_posts.find({"discussion_id": discussion_id}).sort("created_at", 1).to_list(200)

    # Enrich with user data
    user_data = await db.users.find_one({"_id": discussion["user_id"]})
    if user_data:
        discussion["user_name"] = user_data["name"]
        discussion["user_role"] = user_data["role"]

    for reply in replies:
        user_data = await db.users.find_one({"_id": reply["user_id"]})
        if user_data:
            reply["user_name"] = user_data["name"]
            reply["user_role"] = user_data["role"]

    return {
        "discussion": discussion,
        "replies": replies
    }


@reviews_router.post("/discussions/{discussion_id}/replies")
async def create_discussion_reply(
    discussion_id: str,
    reply_data: dict,
    user=Depends(_current_user)
):
    """Create a reply to a discussion"""
    db = get_database()

    discussion = await db.course_discussions.find_one({"_id": discussion_id})
    if not discussion:
        raise HTTPException(404, "Discussion not found")

    # Check if user can reply (enrolled or instructor)
    course = await db.courses.find_one({"_id": discussion["course_id"]})
    if user["role"] not in ["admin", "instructor"] and user["id"] not in course.get("enrolled_user_ids", []):
        raise HTTPException(403, "Must be enrolled to reply")

    reply = DiscussionPost(
        discussion_id=discussion_id,
        user_id=user["id"],
        content=reply_data["content"],
        is_instructor_reply=user["role"] in ["admin", "instructor"]
    )

    result = await db.discussion_posts.insert_one(reply.dict())

    # Update discussion reply count and last reply time
    await db.course_discussions.update_one(
        {"_id": discussion_id},
        {
            "$inc": {"reply_count": 1},
            "$set": {"last_reply_at": datetime.utcnow()}
        }
    )

    return {"message": "Reply created", "reply_id": str(result.inserted_id)}


@reviews_router.put("/discussions/{discussion_id}")
async def update_discussion(
    discussion_id: str,
    discussion_data: dict,
    user=Depends(_current_user)
):
    """Update a discussion (author or instructor only)"""
    db = get_database()

    discussion = await db.course_discussions.find_one({"_id": discussion_id})
    if not discussion:
        raise HTTPException(404, "Discussion not found")

    if discussion["user_id"] != user["id"] and user["role"] not in ["admin", "instructor"]:
        raise HTTPException(403, "Can only edit own discussions")

    await db.course_discussions.update_one(
        {"_id": discussion_id},
        {"$set": {
            "title": discussion_data.get("title", discussion["title"]),
            "content": discussion_data.get("content", discussion["content"]),
            "tags": discussion_data.get("tags", discussion["tags"]),
            "updated_at": datetime.utcnow()
        }}
    )

    return {"message": "Discussion updated"}


@reviews_router.delete("/discussions/{discussion_id}")
async def delete_discussion(discussion_id: str, user=Depends(_current_user)):
    """Delete a discussion (author or instructor only)"""
    db = get_database()

    discussion = await db.course_discussions.find_one({"_id": discussion_id})
    if not discussion:
        raise HTTPException(404, "Discussion not found")

    if discussion["user_id"] != user["id"] and user["role"] not in ["admin", "instructor"]:
        raise HTTPException(403, "Can only delete own discussions")

    # Delete discussion and all replies
    await db.course_discussions.delete_one({"_id": discussion_id})
    await db.discussion_posts.delete_many({"discussion_id": discussion_id})

    return {"message": "Discussion deleted"}


# Instructor Controls
@reviews_router.put("/discussions/{discussion_id}/pin")
async def pin_discussion(discussion_id: str, user=Depends(_current_user)):
    """Pin/unpin a discussion (instructor only)"""
    _require_role(user, ["admin", "instructor"])

    db = get_database()
    discussion = await db.course_discussions.find_one({"_id": discussion_id})
    if not discussion:
        raise HTTPException(404, "Discussion not found")

    current_pinned = discussion.get("is_pinned", False)
    await db.course_discussions.update_one(
        {"_id": discussion_id},
        {"$set": {"is_pinned": not current_pinned}}
    )

    return {"message": f"Discussion {'pinned' if not current_pinned else 'unpinned'}"}


@reviews_router.put("/discussions/{discussion_id}/lock")
async def lock_discussion(discussion_id: str, user=Depends(_current_user)):
    """Lock/unlock a discussion (instructor only)"""
    _require_role(user, ["admin", "instructor"])

    db = get_database()
    discussion = await db.course_discussions.find_one({"_id": discussion_id})
    if not discussion:
        raise HTTPException(404, "Discussion not found")

    current_locked = discussion.get("is_locked", False)
    await db.course_discussions.update_one(
        {"_id": discussion_id},
        {"$set": {"is_locked": not current_locked}}
    )

    return {"message": f"Discussion {'locked' if not current_locked else 'unlocked'}"}


@reviews_router.put("/replies/{reply_id}/solution")
async def mark_reply_as_solution(reply_id: str, user=Depends(_current_user)):
    """Mark a reply as the solution (instructor only)"""
    _require_role(user, ["admin", "instructor"])

    db = get_database()
    reply = await db.discussion_posts.find_one({"_id": reply_id})
    if not reply:
        raise HTTPException(404, "Reply not found")

    current_solution = reply.get("is_solution", False)
    await db.discussion_posts.update_one(
        {"_id": reply_id},
        {"$set": {"is_solution": not current_solution}}
    )

    return {"message": f"Reply {'marked as solution' if not current_solution else 'unmarked as solution'}"}