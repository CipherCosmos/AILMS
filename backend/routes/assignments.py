from fastapi import APIRouter, HTTPException, Depends
from typing import List
import math
import re
from database import get_database, _insert_one, _update_one, _find_one, _require
from auth import _current_user, _require_role
from models import Assignment, AssignmentCreate, Submission, SubmissionCreate, AIDescriptor
from config import settings

# AI integrations
try:
    import google.generativeai as genai
except Exception:
    genai = None

def _get_ai():
    if genai is None:
        raise HTTPException(status_code=500, detail="AI dependency not installed. Please install google-generativeai.")
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="No AI key configured. Set GEMINI_API_KEY in backend/.env")
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(settings.default_llm_model)

def _safe_json_extract(text: str):
    import json
    if not isinstance(text, str):
        text = str(text)
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    raise ValueError("Could not parse JSON from AI response")

assignments_router = APIRouter()

@assignments_router.get("/courses/{cid}/assignments/{aid}/submissions", response_model=List[Submission])
async def list_submissions(aid: str, user=Depends(_current_user)):
    assignment = await _require("assignments", {"_id": aid}, "Assignment not found")
    course = await _require("courses", {"_id": assignment["course_id"]}, "Course not found")
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    db = get_database()
    docs = await db.submissions.find({"assignment_id": aid}).sort("created_at", -1).to_list(1000)
    return [Submission(**d) for d in docs]

@assignments_router.post("/courses/{cid}/assignments", response_model=Assignment)
async def create_assignment(cid: str, body: AssignmentCreate, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    a = Assignment(course_id=cid, title=body.title, description=body.description, due_at=body.due_at, rubric=body.rubric)
    doc = a.dict(); doc["_id"] = a.id
    db = get_database()
    await db.assignments.insert_one(doc)
    return a

@assignments_router.get("/courses/{cid}/assignments", response_model=List[Assignment])
async def list_assignments(cid: str, user=Depends(_current_user)):
    await _require("courses", {"_id": cid}, "Course not found")
    db = get_database()
    docs = await db.assignments.find({"course_id": cid}).sort("created_at", -1).to_list(200)
    return [Assignment(**d) for d in docs]

@assignments_router.post("/{aid}/submit", response_model=Submission)
async def submit_assignment(aid: str, body: SubmissionCreate, user=Depends(_current_user)):
    await _require("assignments", {"_id": aid}, "Assignment not found")
    sub = Submission(assignment_id=aid, user_id=user["id"], text_answer=body.text_answer, file_ids=body.file_ids)
    # plagiarism check vs other submissions (TF-IDF cosine)
    db = get_database()
    existing = await db.submissions.find({"assignment_id": aid}).to_list(1000)
    def _tf(text):
        words = re.findall(r"\w+", (text or "").lower())
        tf = {}
        for w in words:
            tf[w] = tf.get(w, 0) + 1
        n = max(1, len(words))
        return {k: v / n for k, v in tf.items()}
    def _cos(a, b):
        keys = set(a) | set(b)
        dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
        na = math.sqrt(sum(v*v for v in a.values()))
        nb = math.sqrt(sum(v*v for v in b.values()))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)
    target_tf = _tf(sub.text_answer or "")
    max_sim = 0.0
    most_like = None
    for e in existing:
        sim = _cos(target_tf, _tf(e.get("text_answer", "")))
        if sim > max_sim:
            max_sim = sim; most_like = e.get("id")
    sub.plagiarism = {"max_similarity": round(max_sim, 4), "similar_to_submission_id": most_like}
    doc = sub.dict(); doc["_id"] = sub.id
    await db.submissions.insert_one(doc)
    return sub

@assignments_router.post("/{aid}/grade/ai")
async def ai_grade(aid: str, body: AIDescriptor, user=Depends(_current_user)):
    a = await _require("assignments", {"_id": aid}, "Assignment not found")
    # Only instructor/admin who owns course can grade
    course = await _require("courses", {"_id": a["course_id"]}, "Course not found")
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    db = get_database()
    subs = await db.submissions.find({"assignment_id": aid}).to_list(1000)
    if not subs:
        return {"status": "no_submissions"}
    system_message = "You are a strict grader. Score each submission 0-100 with justification per rubric item; output strict JSON."
    for s in subs:
        if s.get("ai_grade"):
            continue
        rubric = a.get("rubric", [])
        prompt = f"Rubric: {rubric}\nSubmission Text: {s.get('text_answer','')}\n{body.additional_instructions or ''}\nReturn ONLY JSON like {{'score': number, 'feedback': string, 'rubric_scores': [{{'criterion': string, 'score': number}}]}}"
        model = _get_ai()
        try:
            response = model.generate_content(prompt)
            data = _safe_json_extract(response.text.replace("'", '"'))
        except Exception as e:
            data = {"score": 0, "feedback": f"AI grading failed: {e}", "rubric_scores": []}
        await db.submissions.update_one({"_id": s["_id"]}, {"$set": {"ai_grade": data}})
    return {"status": "graded", "count": len(subs)}


# Instructor: View all submissions for assignment
@assignments_router.get("/courses/{cid}/assignments/{aid}/all_submissions")
async def get_all_submissions(aid: str, user=Depends(_current_user)):
    assignment = await _require("assignments", {"_id": aid}, "Assignment not found")
    course = await _require("courses", {"_id": assignment["course_id"]}, "Course not found")
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    db = get_database()
    subs = await db.submissions.find({"assignment_id": aid}).to_list(1000)
    # Include user info
    user_ids = [s["user_id"] for s in subs]
    users = await db.users.find({"_id": {"$in": user_ids}}).to_list(100)
    user_map = {u["_id"]: {"name": u["name"], "email": u["email"]} for u in users}
    for s in subs:
        s["user_info"] = user_map.get(s["user_id"], {})
    return subs


# Instructor: Delete student submission
@assignments_router.delete("/{aid}/submissions/{sid}")
async def delete_submission(aid: str, sid: str, user=Depends(_current_user)):
    assignment = await _require("assignments", {"_id": aid}, "Assignment not found")
    course = await _require("courses", {"_id": assignment["course_id"]}, "Course not found")
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    db = get_database()
    result = await db.submissions.delete_one({"_id": sid, "assignment_id": aid})
    if result.deleted_count == 0:
        raise HTTPException(404, "Submission not found")
    return {"status": "deleted"}


# Student: View their own submissions
@assignments_router.get("/my_submissions")
async def get_my_submissions(user=Depends(_current_user)):
    db = get_database()
    subs = await db.submissions.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)
    # Include assignment and course info
    assignment_ids = [s["assignment_id"] for s in subs]
    assignments = await db.assignments.find({"_id": {"$in": assignment_ids}}).to_list(100)
    assignment_map = {a["_id"]: {"title": a["title"], "course_id": a["course_id"]} for a in assignments}
    course_ids = list(set(a["course_id"] for a in assignments if a.get("course_id")))
    courses = await db.courses.find({"_id": {"$in": course_ids}}).to_list(100)
    course_map = {c["_id"]: c["title"] for c in courses}
    for s in subs:
        assign = assignment_map.get(s["assignment_id"], {})
        s["assignment_title"] = assign.get("title", "")
        s["course_title"] = course_map.get(assign.get("course_id"), "")
        # Convert _id to id for frontend compatibility
        if "_id" in s and "id" not in s:
            s["id"] = str(s["_id"])
        if "_id" in s:
            del s["_id"]
    return subs


# Student: Delete their own submission
@assignments_router.delete("/my_submissions/{sid}")
async def delete_my_submission(sid: str, user=Depends(_current_user)):
    db = get_database()
    result = await db.submissions.delete_one({"_id": sid, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Submission not found")
    return {"status": "deleted"}