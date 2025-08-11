from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import json
import re
from passlib.hash import bcrypt
import jwt
import math

# AI integrations
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except Exception:
    LlmChat = None
    UserMessage = None

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
fs_bucket = AsyncIOMotorGridFSBucket(db)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Security
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change")
ACCESS_EXPIRE_MIN = int(os.environ.get("ACCESS_EXPIRE_MIN", "30"))
REFRESH_EXPIRE_DAYS = int(os.environ.get("REFRESH_EXPIRE_DAYS", "14"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --------- Utilities ---------

def _uuid() -> str:
    return str(uuid.uuid4())

async def _insert_one(collection: str, doc: Dict[str, Any]):
    if "_id" not in doc:
        doc["_id"] = doc.get("id", _uuid())
    await db[collection].insert_one(doc)

async def _update_one(collection: str, filt: Dict[str, Any], update: Dict[str, Any]):
    await db[collection].update_one(filt, {'$set': update})

async def _find_one(collection: str, filt: Dict[str, Any]):
    return await db[collection].find_one(filt)

async def _require(collection: str, filt: Dict[str, Any], msg: str):
    doc = await _find_one(collection, filt)
    if not doc:
        raise HTTPException(404, msg)
    return doc

def _get_ai(api_key: Optional[str], session_id: str, system_message: str) -> LlmChat:
    if LlmChat is None:
        raise HTTPException(status_code=500, detail="AI dependency not installed. Please install emergentintegrations.")
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="No AI key configured. Set GEMINI_API_KEY or EMERGENT_LLM_KEY in backend/.env")
    model = os.environ.get("DEFAULT_LLM_MODEL", "gemini-2.0-flash")
    return LlmChat(api_key=key, session_id=session_id, system_message=system_message).with_model("gemini", model)

def _safe_json_extract(text: str) -> Dict[str, Any]:
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

# --- Auth helpers ---
class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserBase(BaseModel):
    id: str = Field(default_factory=_uuid)
    email: EmailStr
    name: str
    role: str = Field(pattern=r"^(admin|instructor|student|auditor)$")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: Optional[str] = None

class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

async def _create_tokens(user: Dict[str, Any]) -> TokenPair:
    now = datetime.utcnow()
    access = jwt.encode({"sub": user["id"], "role": user["role"], "exp": now + timedelta(minutes=ACCESS_EXPIRE_MIN)}, JWT_SECRET, algorithm="HS256")
    refresh = jwt.encode({"sub": user["id"], "type": "refresh", "exp": now + timedelta(days=REFRESH_EXPIRE_DAYS)}, JWT_SECRET, algorithm="HS256")
    return TokenPair(access_token=access, refresh_token=refresh)

async def _current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(401, "Invalid token payload")
    user = await _find_one("users", {"_id": uid})
    if not user:
        raise HTTPException(401, "User not found")
    return user

def _require_role(user: Dict[str, Any], allowed: List[str]):
    if user.get("role") not in allowed:
        raise HTTPException(403, "Insufficient permissions")

# --- Domain Models ---
class CourseLesson(BaseModel):
    id: str = Field(default_factory=_uuid)
    title: str
    content: str = ""
    resources: List[str] = []  # file_ids
    transcript_text: Optional[str] = None
    summary: Optional[str] = None

class QuizOption(BaseModel):
    text: str
    is_correct: bool

class QuizQuestion(BaseModel):
    id: str = Field(default_factory=_uuid)
    question: str
    options: List[QuizOption]
    explanation: Optional[str] = None

class Course(BaseModel):
    id: str = Field(default_factory=_uuid)
    owner_id: str
    title: str
    audience: str
    difficulty: str
    lessons: List[CourseLesson] = []
    quiz: List[QuizQuestion] = []
    published: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    enrolled_user_ids: List[str] = []

class CourseCreate(BaseModel):
    title: str
    audience: str
    difficulty: str

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    audience: Optional[str] = None
    difficulty: Optional[str] = None
    published: Optional[bool] = None

class GenerateCourseRequest(BaseModel):
    topic: str
    audience: str
    difficulty: str = Field(pattern=r"^(beginner|intermediate|advanced)$")
    lessons_count: int = Field(ge=1, le=20)

class Assignment(BaseModel):
    id: str = Field(default_factory=_uuid)
    course_id: str
    title: str
    description: str = ""
    due_at: Optional[datetime] = None
    rubric: List[str] = []  # simple textual criteria
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Submission(BaseModel):
    id: str = Field(default_factory=_uuid)
    assignment_id: str
    user_id: str
    text_answer: Optional[str] = None
    file_ids: List[str] = []
    ai_grade: Optional[Dict[str, Any]] = None
    plagiarism: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Thread(BaseModel):
    id: str = Field(default_factory=_uuid)
    course_id: str
    user_id: str
    title: str
    body: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Post(BaseModel):
    id: str = Field(default_factory=_uuid)
    thread_id: str
    user_id: str
    body: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    course_id: str
    session_id: str
    message: str

class ChatMessageModel(BaseModel):
    id: str = Field(default_factory=_uuid)
    course_id: str
    session_id: str
    role: str
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- Routes: health ---
@api.get("/")
async def root():
    return {"message": "Hello World"}

# --- Auth ---
@api.post("/auth/register", response_model=UserPublic)
async def register(body: UserCreate):
    existing = await _find_one("users", {"email": str(body.email).lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    role = body.role or "student"
    # bootstrap: allow first user to be admin if db empty
    users_count = await db.users.count_documents({})
    if role == "admin" and users_count > 0:
        raise HTTPException(403, "Cannot self-assign admin")
    if users_count == 0 and role != "admin":
        role = "admin"
    user = UserBase(email=str(body.email).lower(), name=body.name, role=role)
    doc = user.dict()
    doc["password_hash"] = bcrypt.hash(body.password)
    doc["_id"] = user.id
    await db.users.insert_one(doc)
    return UserPublic(id=user.id, email=user.email, name=user.name, role=user.role)

@api.post("/auth/login", response_model=TokenPair)
async def login(body: LoginRequest):
    user = await _find_one("users", {"email": str(body.email).lower()})
    if not user or not bcrypt.verify(body.password, user.get("password_hash", "")):
        raise HTTPException(401, "Invalid credentials")
    return await _create_tokens(user)

@api.post("/auth/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest):
    try:
        payload = jwt.decode(body.refresh_token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token type")
    user = await _require("users", {"_id": payload.get("sub")}, "User not found")
    return await _create_tokens(user)

@api.get("/auth/me", response_model=UserPublic)
async def me(user=Depends(_current_user)):
    return UserPublic(id=user["id"], email=user["email"], name=user["name"], role=user["role"])

# --- Courses ---
@api.post("/courses", response_model=Course)
async def create_course(body: CourseCreate, user=Depends(_current_user)):
    _require_role(user, ["admin", "instructor"])
    course = Course(owner_id=user["id"], title=body.title, audience=body.audience, difficulty=body.difficulty)
    doc = course.dict(); doc["_id"] = course.id
    await db.courses.insert_one(doc)
    return course

@api.get("/courses", response_model=List[Course])
async def list_courses(user=Depends(_current_user)):
    q = {} if user["role"] in ["admin", "auditor"] else {"$or": [{"published": True}, {"owner_id": user["id"]}, {"enrolled_user_ids": user["id"]}]}
    docs = await db.courses.find(q).sort("created_at", -1).to_list(200)
    return [Course(**d) for d in docs]

@api.get("/courses/{cid}", response_model=Course)
async def get_course(cid: str, user=Depends(_current_user)):
    doc = await _require("courses", {"_id": cid}, "Course not found")
    # visibility
    if not (doc.get("published") or doc.get("owner_id") == user["id"] or user["role"] in ["admin", "auditor"] or user["id"] in doc.get("enrolled_user_ids", [])):
        raise HTTPException(403, "Not authorized to view course")
    return Course(**doc)

@api.put("/courses/{cid}", response_model=Course)
async def update_course(cid: str, body: CourseUpdate, user=Depends(_current_user)):
    doc = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] == "admin" or doc.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    changes = {k: v for k, v in body.dict().items() if v is not None}
    await _update_one("courses", {"_id": cid}, changes)
    doc.update(changes)
    return Course(**doc)

@api.post("/courses/{cid}/enroll")
async def enroll_course(cid: str, user=Depends(_current_user)):
    await _require("courses", {"_id": cid}, "Course not found")
    await db.courses.update_one({"_id": cid}, {"$addToSet": {"enrolled_user_ids": user["id"]}})
    return {"status": "enrolled"}

# Lesson management
class LessonCreate(BaseModel):
    title: str
    content: str = ""

@api.post("/courses/{cid}/lessons", response_model=Course)
async def add_lesson(cid: str, body: LessonCreate, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    lesson = CourseLesson(title=body.title, content=body.content)
    await db.courses.update_one({"_id": cid}, {"$push": {"lessons": lesson.dict()}})
    course["lessons"].append(lesson.dict())
    return Course(**course)

# AI: Course auto-generation
@api.post("/ai/generate_course", response_model=Course)
async def generate_course(req: GenerateCourseRequest, user=Depends(_current_user)):
    _require_role(user, ["admin", "instructor"])  # only creators
    system_message = "You are an expert instructional designer. Output strict JSON."
    prompt = f"""
Create a complete course on the topic: {req.topic}
Audience: {req.audience}
Difficulty: {req.difficulty}
Number of lessons: {req.lessons_count}

Return ONLY JSON with this schema:
{{
  "title": string,
  "audience": string,
  "difficulty": string,
  "lessons": [
    {{"title": string, "content": string}} (exactly {req.lessons_count} items)
  ],
  "quiz": [
    {{
      "question": string,
      "options": [
        {{"text": string, "is_correct": boolean}},
        {{"text": string, "is_correct": boolean}},
        {{"text": string, "is_correct": boolean}},
        {{"text": string, "is_correct": boolean}}
      ],
      "explanation": string
    }}
  ]
}}
Ensure exactly one option is correct per question.
"""
    try:
        chat = _get_ai(api_key=None, session_id=f"course-gen-{_uuid()}", system_message=system_message)
        ai_resp = await chat.send_message(UserMessage(text=prompt))
        data = _safe_json_extract(str(ai_resp))
    except Exception as e:
        logger.exception("AI generation failed")
        raise HTTPException(500, f"AI generation failed: {e}")

    # build model
    lessons = [CourseLesson(title=l.get("title", "Untitled"), content=l.get("content", "")) for l in data.get("lessons", [])][: req.lessons_count]
    quiz: List[QuizQuestion] = []
    for q in data.get("quiz", [])[: max(3, req.lessons_count)]:
        options = [QuizOption(text=o.get("text", ""), is_correct=bool(o.get("is_correct", False))) for o in q.get("options", [])[:4]]
        if sum(1 for o in options if o.is_correct) != 1 and options:
            for i, o in enumerate(options):
                o.is_correct = (i == 0)
        quiz.append(QuizQuestion(question=q.get("question", ""), options=options, explanation=q.get("explanation") or ""))
    course = Course(owner_id=user["id"], title=data.get("title", req.topic), audience=data.get("audience", req.audience), difficulty=data.get("difficulty", req.difficulty), lessons=lessons, quiz=quiz)
    doc = course.dict(); doc["_id"] = course.id
    await db.courses.insert_one(doc)
    return course

# Quizzes: generate for a lesson
@api.post("/lessons/{lesson_id}/quiz/generate", response_model=QuizQuestion)
async def generate_quiz_for_lesson(lesson_id: str, user=Depends(_current_user)):
    course = await db.courses.find_one({"lessons.id": lesson_id})
    if not course:
        raise HTTPException(404, "Lesson not found")
    if not (user["role"] in ["admin"] or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    lesson = next((l for l in course.get("lessons", []) if l.get("id") == lesson_id), None)
    system_message = "Generate a single high quality MCQ based on lesson content in strict JSON."
    schema = "{" + "\"question\": string, \"options\": [{\"text\": string, \"is_correct\": boolean} x4], \"explanation\": string" + "}"
    prompt = f"Create 1 MCQ for lesson titled '{lesson.get('title')}'. Content: {lesson.get('content')}. Return ONLY JSON with schema {schema}."
    chat = _get_ai(None, f"quiz-{lesson_id}", system_message)
    data = _safe_json_extract(str(await chat.send_message(UserMessage(text=prompt))))
    options = [QuizOption(text=o.get("text", ""), is_correct=bool(o.get("is_correct", False))) for o in data.get("options", [])[:4]]
    if sum(1 for o in options if o.is_correct) != 1 and options:
        options[0].is_correct = True
        for i in range(1, len(options)):
            options[i].is_correct = False
    q = QuizQuestion(question=data.get("question", ""), options=options, explanation=data.get("explanation") or "")
    await db.courses.update_one({"_id": course["_id"], "lessons.id": lesson_id}, {"$push": {"quiz": q.dict()}})
    return q

# Quiz submission
class QuizSubmitRequest(BaseModel):
    question_id: str
    selected_index: int

@api.post("/quizzes/{course_id}/submit")
async def submit_quiz(course_id: str, body: QuizSubmitRequest, user=Depends(_current_user)):
    course = await _require("courses", {"_id": course_id}, "Course not found")
    q = next((qq for qq in course.get("quiz", []) if qq.get("id") == body.question_id), None)
    if not q:
        raise HTTPException(404, "Question not found")
    correct = False
    try:
        correct = bool(q.get("options", [])[body.selected_index].get("is_correct"))
    except Exception:
        correct = False
    return {"correct": correct, "explanation": q.get("explanation", "")}

# File upload/download (GridFS)
@api.post("/files/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(_current_user)):
    file_id = _uuid()
    grid_in = fs_bucket.open_upload_stream_with_id(file_id, file.filename, metadata={"user_id": user["id"], "content_type": file.content_type})
    while True:
        chunk = await file.read(1024 * 512)
        if not chunk:
            break
        await grid_in.write(chunk)
    await grid_in.close()
    return {"file_id": file_id, "filename": file.filename}

from fastapi.responses import StreamingResponse
@api.get("/files/{file_id}")
async def download_file(file_id: str, user=Depends(_current_user)):
    try:
        grid_out = await fs_bucket.open_download_stream(file_id)
    except Exception:
        raise HTTPException(404, "File not found")
    headers = {"Content-Disposition": f"attachment; filename={grid_out.filename}"}
    async def file_iterator():
        while True:
            chunk = await grid_out.readchunk()
            if not chunk:
                break
            yield chunk
    return StreamingResponse(file_iterator(), headers=headers, media_type=grid_out.metadata.get("content_type", "application/octet-stream"))

# Assignments
class AssignmentCreate(BaseModel):
    title: str
    description: str = ""
    due_at: Optional[datetime] = None
    rubric: List[str] = []

@api.post("/courses/{cid}/assignments", response_model=Assignment)
async def create_assignment(cid: str, body: AssignmentCreate, user=Depends(_current_user)):
    course = await _require("courses", {"_id": cid}, "Course not found")
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    a = Assignment(course_id=cid, title=body.title, description=body.description, due_at=body.due_at, rubric=body.rubric)
    doc = a.dict(); doc["_id"] = a.id
    await db.assignments.insert_one(doc)
    return a

@api.get("/courses/{cid}/assignments", response_model=List[Assignment])
async def list_assignments(cid: str, user=Depends(_current_user)):
    await _require("courses", {"_id": cid}, "Course not found")
    docs = await db.assignments.find({"course_id": cid}).sort("created_at", -1).to_list(200)
    return [Assignment(**d) for d in docs]

class SubmissionCreate(BaseModel):
    text_answer: Optional[str] = None
    file_ids: List[str] = []

@api.post("/assignments/{aid}/submit", response_model=Submission)
async def submit_assignment(aid: str, body: SubmissionCreate, user=Depends(_current_user)):
    await _require("assignments", {"_id": aid}, "Assignment not found")
    sub = Submission(assignment_id=aid, user_id=user["id"], text_answer=body.text_answer, file_ids=body.file_ids)
    # plagiarism check vs other submissions (TF-IDF cosine)
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

# AI grading
class AIDescriptor(BaseModel):
    additional_instructions: Optional[str] = None

@api.post("/assignments/{aid}/grade/ai")
async def ai_grade(aid: str, body: AIDescriptor, user=Depends(_current_user)):
    a = await _require("assignments", {"_id": aid}, "Assignment not found")
    # Only instructor/admin who owns course can grade
    course = await _require("courses", {"_id": a["course_id"]}, "Course not found")
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    subs = await db.submissions.find({"assignment_id": aid}).to_list(1000)
    if not subs:
        return {"status": "no_submissions"}
    system_message = "You are a strict grader. Score each submission 0-100 with justification per rubric item; output strict JSON."
    for s in subs:
        if s.get("ai_grade"):
            continue
        rubric = a.get("rubric", [])
        prompt = f"Rubric: {rubric}\nSubmission Text: {s.get('text_answer','')}\n{body.additional_instructions or ''}\nReturn ONLY JSON like {{'score': number, 'feedback': string, 'rubric_scores': [{{'criterion': string, 'score': number}}]}}"
        chat = _get_ai(None, f"grade-{s['id']}", system_message)
        try:
            resp = await chat.send_message(UserMessage(text=prompt))
            data = _safe_json_extract(str(resp).replace("'", '"'))
        except Exception as e:
            data = {"score": 0, "feedback": f"AI grading failed: {e}", "rubric_scores": []}
        await db.submissions.update_one({"_id": s["_id"]}, {"$set": {"ai_grade": data}})
    return {"status": "graded", "count": len(subs)}

# Course Q&amp;A Chat
async def _keyword_snippets(course: Dict[str, Any], query: str, max_chars: int = 4000) -> str:
    text_blobs: List[str] = []
    for lesson in course.get("lessons", []):
        t = f"Lesson: {lesson.get('title')}\n{lesson.get('content')}"
        text_blobs.append(t)
    for q in course.get("quiz", []):
        opts = "\n".join([f"- {o.get('text')} ({'correct' if o.get('is_correct') else 'wrong'})" for o in q.get("options", [])])
        text_blobs.append(f"Q: {q.get('question')}\n{opts}\nExplanation: {q.get('explanation', '')}")
    tokens = set([w.lower() for w in re.findall(r"\w+", query)])
    scored = []
    for blob in text_blobs:
        words = set([w.lower() for w in re.findall(r"\w+", blob)])
        score = len(tokens & words)
        scored.append((score, blob))
    scored.sort(reverse=True, key=lambda x: x[0])
    combined = "\n\n".join([b for _, b in scored])
    return combined[:max_chars]

@api.post("/ai/chat")
async def course_chat(req: ChatRequest, user=Depends(_current_user)):
    course = await _require("courses", {"_id": req.course_id}, "Course not found")
    # visibility check
    if not (course.get("published") or course.get("owner_id") == user["id"] or user["role"] in ["admin", "auditor"] or user["id"] in course.get("enrolled_user_ids", [])):
        raise HTTPException(403, "Not authorized to chat for this course")
    context = await _keyword_snippets(course, req.message)
    system_message = "You are a helpful tutor. Answer concisely based on course content; if unclear, say you're unsure."
    user_text = f"Course context (do not reveal verbatim):\n{context}\nQuestion: {req.message}"
    chat = _get_ai(None, req.session_id, system_message)
    ai_resp = str(await chat.send_message(UserMessage(text=user_text)))
    user_msg = ChatMessageModel(course_id=req.course_id, session_id=req.session_id, role="user", message=req.message)
    asst_msg = ChatMessageModel(course_id=req.course_id, session_id=req.session_id, role="assistant", message=ai_resp)
    await _insert_one("chats", user_msg.dict())
    await _insert_one("chats", asst_msg.dict())
    return {"reply": ai_resp, "assistant_message_id": asst_msg.id}

@api.get("/chats/{course_id}/{session_id}", response_model=List[ChatMessageModel])
async def get_chat_history(course_id: str, session_id: str, user=Depends(_current_user)):
    await _require("courses", {"_id": course_id}, "Course not found")
    docs = await db.chats.find({"course_id": course_id, "session_id": session_id}).sort("created_at", 1).to_list(1000)
    return [ChatMessageModel(**d) for d in docs]

# Discussions
class ThreadCreate(BaseModel):
    title: str
    body: str

class PostCreate(BaseModel):
    body: str

@api.post("/courses/{cid}/threads", response_model=Thread)
async def create_thread(cid: str, body: ThreadCreate, user=Depends(_current_user)):
    await _require("courses", {"_id": cid}, "Course not found")
    t = Thread(course_id=cid, user_id=user["id"], title=body.title, body=body.body)
    doc = t.dict(); doc["_id"] = t.id
    await db.threads.insert_one(doc)
    return t

@api.get("/courses/{cid}/threads", response_model=List[Thread])
async def list_threads(cid: str, user=Depends(_current_user)):
    await _require("courses", {"_id": cid}, "Course not found")
    docs = await db.threads.find({"course_id": cid}).sort("created_at", -1).to_list(500)
    return [Thread(**d) for d in docs]

@api.post("/threads/{tid}/posts", response_model=Post)
async def add_post(tid: str, body: PostCreate, user=Depends(_current_user)):
    await _require("threads", {"_id": tid}, "Thread not found")
    p = Post(thread_id=tid, user_id=user["id"], body=body.body)
    doc = p.dict(); doc["_id"] = p.id
    await db.posts.insert_one(doc)
    return p

@api.get("/threads/{tid}/posts", response_model=List[Post])
async def list_posts(tid: str, user=Depends(_current_user)):
    await _require("threads", {"_id": tid}, "Thread not found")
    docs = await db.posts.find({"thread_id": tid}).sort("created_at", 1).to_list(1000)
    return [Post(**d) for d in docs]

# Transcripts and Summaries
class TranscriptBody(BaseModel):
    text: str

@api.post("/lessons/{lesson_id}/transcript")
async def upload_transcript(lesson_id: str, body: TranscriptBody, user=Depends(_current_user)):
    course = await db.courses.find_one({"lessons.id": lesson_id})
    if not course:
        raise HTTPException(404, "Lesson not found")
    if not (user["role"] == "admin" or course.get("owner_id") == user["id"]):
        raise HTTPException(403, "Not authorized")
    await db.courses.update_one({"_id": course["_id"], "lessons.id": lesson_id}, {"$set": {"lessons.$.transcript_text": body.text}})
    return {"status": "uploaded"}

@api.post("/lessons/{lesson_id}/summary")
async def summarize_lesson(lesson_id: str, user=Depends(_current_user)):
    course = await db.courses.find_one({"lessons.id": lesson_id})
    if not course:
        raise HTTPException(404, "Lesson not found")
    lesson = next((l for l in course.get("lessons", []) if l.get("id") == lesson_id), None)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    if not (user["role"] in ["admin", "instructor"] and course.get("owner_id") == user["id"]) and user["role"] not in ["admin", "auditor", "student"]:
        raise HTTPException(403, "Not authorized")
    transcript = lesson.get("transcript_text") or lesson.get("content")
    chat = _get_ai(None, f"sum-{lesson_id}", "You create crisp summaries and bullet highlights as JSON.")
    prompt = f"Summarize this lesson transcript/content into JSON: {{'summary': string, 'highlights': [string]}}. Text: {transcript}"
    try:
        data = _safe_json_extract(str(await chat.send_message(UserMessage(text=prompt))).replace("'", '"'))
    except Exception:
        data = {"summary": "Summary unavailable", "highlights": []}
    await db.courses.update_one({"_id": course["_id"], "lessons.id": lesson_id}, {"$set": {"lessons.$.summary": data.get("summary")}})
    return data

# Analytics
@api.get("/analytics/instructor")
async def instructor_analytics(user=Depends(_current_user)):
    _require_role(user, ["admin", "instructor"])
    q = {"owner_id": user["id"]} if user["role"] == "instructor" else {}
    courses = await db.courses.find(q).to_list(1000)
    total_students = sum(len(c.get("enrolled_user_ids", [])) for c in courses)
    return {"courses": len(courses), "students": total_students}

@api.get("/analytics/admin")
async def admin_analytics(user=Depends(_current_user)):
    _require_role(user, ["admin"])
    users = await db.users.count_documents({})
    courses = await db.courses.count_documents({})
    submissions = await db.submissions.count_documents({})
    return {"users": users, "courses": courses, "submissions": submissions}

@api.get("/analytics/student")
async def student_analytics(user=Depends(_current_user)):
    _require_role(user, ["student"])  # auditor sees via course list
    my_courses = await db.courses.count_documents({"enrolled_user_ids": user["id"]})
    my_subs = await db.submissions.count_documents({"user_id": user["id"]})
    return {"enrolled_courses": my_courses, "submissions": my_subs}

# Include router and CORS
app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()