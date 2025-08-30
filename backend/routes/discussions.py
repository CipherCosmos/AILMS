from fastapi import APIRouter, HTTPException, Depends
from typing import List
from database import db, _insert_one, _require
from auth import _current_user
from models import Thread, ThreadCreate, Post, PostCreate

discussions_router = APIRouter()

@discussions_router.post("/courses/{cid}/threads", response_model=Thread)
async def create_thread(cid: str, body: ThreadCreate, user=Depends(_current_user)):
    await _require("courses", {"_id": cid}, "Course not found")
    t = Thread(course_id=cid, user_id=user["id"], title=body.title, body=body.body)
    doc = t.dict(); doc["_id"] = t.id
    await db.threads.insert_one(doc)
    return t

@discussions_router.get("/courses/{cid}/threads", response_model=List[Thread])
async def list_threads(cid: str, user=Depends(_current_user)):
    await _require("courses", {"_id": cid}, "Course not found")
    docs = await db.threads.find({"course_id": cid}).sort("created_at", -1).to_list(500)
    return [Thread(**d) for d in docs]

@discussions_router.post("/threads/{tid}/posts", response_model=Post)
async def add_post(tid: str, body: PostCreate, user=Depends(_current_user)):
    await _require("threads", {"_id": tid}, "Thread not found")
    p = Post(thread_id=tid, user_id=user["id"], body=body.body)
    doc = p.dict(); doc["_id"] = p.id
    await db.posts.insert_one(doc)
    return p

@discussions_router.get("/threads/{tid}/posts", response_model=List[Post])
async def list_posts(tid: str, user=Depends(_current_user)):
    await _require("threads", {"_id": tid}, "Thread not found")
    docs = await db.posts.find({"thread_id": tid}).sort("created_at", 1).to_list(1000)
    return [Post(**d) for d in docs]


# Instructor Controls for Discussions
@discussions_router.put("/threads/{tid}/pin")
async def pin_thread(tid: str, user=Depends(_current_user)):
    thread = await _require("threads", {"_id": tid}, "Thread not found")
    course = await _require("courses", {"_id": thread["course_id"]}, "Course not found")

    # Check if user is instructor of the course
    if course.get("owner_id") != user["id"] and user["role"] not in ["admin"]:
        raise HTTPException(403, "Not authorized")

    await db.threads.update_one({"_id": tid}, {"$set": {"pinned": True}})
    return {"status": "pinned"}


@discussions_router.put("/threads/{tid}/unpin")
async def unpin_thread(tid: str, user=Depends(_current_user)):
    thread = await _require("threads", {"_id": tid}, "Thread not found")
    course = await _require("courses", {"_id": thread["course_id"]}, "Course not found")

    if course.get("owner_id") != user["id"] and user["role"] not in ["admin"]:
        raise HTTPException(403, "Not authorized")

    await db.threads.update_one({"_id": tid}, {"$set": {"pinned": False}})
    return {"status": "unpinned"}


@discussions_router.put("/threads/{tid}/lock")
async def lock_thread(tid: str, user=Depends(_current_user)):
    thread = await _require("threads", {"_id": tid}, "Thread not found")
    course = await _require("courses", {"_id": thread["course_id"]}, "Course not found")

    if course.get("owner_id") != user["id"] and user["role"] not in ["admin"]:
        raise HTTPException(403, "Not authorized")

    await db.threads.update_one({"_id": tid}, {"$set": {"locked": True}})
    return {"status": "locked"}


@discussions_router.put("/threads/{tid}/unlock")
async def unlock_thread(tid: str, user=Depends(_current_user)):
    thread = await _require("threads", {"_id": tid}, "Thread not found")
    course = await _require("courses", {"_id": thread["course_id"]}, "Course not found")

    if course.get("owner_id") != user["id"] and user["role"] not in ["admin"]:
        raise HTTPException(403, "Not authorized")

    await db.threads.update_one({"_id": tid}, {"$set": {"locked": False}})
    return {"status": "unlocked"}


@discussions_router.delete("/threads/{tid}")
async def delete_thread(tid: str, user=Depends(_current_user)):
    thread = await _require("threads", {"_id": tid}, "Thread not found")
    course = await _require("courses", {"_id": thread["course_id"]}, "Course not found")

    if course.get("owner_id") != user["id"] and user["role"] not in ["admin"]:
        raise HTTPException(403, "Not authorized")

    # Delete thread and all its posts
    await db.threads.delete_one({"_id": tid})
    await db.posts.delete_many({"thread_id": tid})
    return {"status": "deleted"}


@discussions_router.put("/posts/{pid}/solution")
async def mark_post_as_solution(pid: str, user=Depends(_current_user)):
    post = await _require("posts", {"_id": pid}, "Post not found")
    thread = await _require("threads", {"_id": post["thread_id"]}, "Thread not found")
    course = await _require("courses", {"_id": thread["course_id"]}, "Course not found")

    if course.get("owner_id") != user["id"] and user["role"] not in ["admin"]:
        raise HTTPException(403, "Not authorized")

    # Mark this post as solution and unmark others in the same thread
    await db.posts.update_many({"thread_id": post["thread_id"]}, {"$set": {"is_solution": False}})
    await db.posts.update_one({"_id": pid}, {"$set": {"is_solution": True}})
    return {"status": "marked_as_solution"}


@discussions_router.delete("/posts/{pid}")
async def delete_post(pid: str, user=Depends(_current_user)):
    post = await _require("posts", {"_id": pid}, "Post not found")
    thread = await _require("threads", {"_id": post["thread_id"]}, "Thread not found")
    course = await _require("courses", {"_id": thread["course_id"]}, "Course not found")

    # Allow deletion by post author, thread author, or course instructor
    if (post["user_id"] != user["id"] and
        thread["user_id"] != user["id"] and
        course.get("owner_id") != user["id"] and
        user["role"] not in ["admin"]):
        raise HTTPException(403, "Not authorized")

    await db.posts.delete_one({"_id": pid})
    return {"status": "deleted"}


@discussions_router.put("/threads/{tid}/featured")
async def feature_thread(tid: str, user=Depends(_current_user)):
    thread = await _require("threads", {"_id": tid}, "Thread not found")
    course = await _require("courses", {"_id": thread["course_id"]}, "Course not found")

    if course.get("owner_id") != user["id"] and user["role"] not in ["admin"]:
        raise HTTPException(403, "Not authorized")

    await db.threads.update_one({"_id": tid}, {"$set": {"featured": True}})
    return {"status": "featured"}


@discussions_router.put("/threads/{tid}/unfeature")
async def unfeature_thread(tid: str, user=Depends(_current_user)):
    thread = await _require("threads", {"_id": tid}, "Thread not found")
    course = await _require("courses", {"_id": thread["course_id"]}, "Course not found")

    if course.get("owner_id") != user["id"] and user["role"] not in ["admin"]:
        raise HTTPException(403, "Not authorized")

    await db.threads.update_one({"_id": tid}, {"$set": {"featured": False}})
    return {"status": "unfeatured"}