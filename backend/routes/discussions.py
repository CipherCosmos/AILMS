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