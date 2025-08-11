from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import json
import re

# AI integrations
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except Exception as e:
    # The server should still boot even if deps are missing; endpoints will error if called.
    LlmChat = None
    UserMessage = None

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --------- Models ---------
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class CourseLesson(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str

class QuizOption(BaseModel):
    text: str
    is_correct: bool

class QuizQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    options: List[QuizOption]
    explanation: Optional[str] = None

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    audience: str
    difficulty: str
    lessons_count: int
    lessons: List[CourseLesson]
    quiz: List[QuizQuestion]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GenerateCourseRequest(BaseModel):
    topic: str
    audience: str
    difficulty: str = Field(pattern=r"^(beginner|intermediate|advanced)$")
    lessons_count: int = Field(ge=1, le=20)

class ChatRequest(BaseModel):
    course_id: str
    session_id: str
    message: str

class ChatMessageModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str
    session_id: str
    role: str  # user or assistant
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --------- Utilities ---------

def _get_ai(api_key: Optional[str], session_id: str, system_message: str) -> LlmChat:
    if LlmChat is None:
        raise HTTPException(status_code=500, detail="AI dependency not installed. Please install emergentintegrations.")
    # Priority order: explicit key, GEMINI_API_KEY, EMERGENT_LLM_KEY
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="No AI key configured. Set GEMINI_API_KEY or EMERGENT_LLM_KEY in backend/.env")
    chat = LlmChat(
        api_key=key,
        session_id=session_id,
        system_message=system_message,
    ).with_model("gemini", os.environ.get("DEFAULT_LLM_MODEL", "gemini-2.0-flash"))
    return chat

async def _insert_one(collection: str, doc: Dict[str, Any]):
    # Ensure _id is a UUID string for Mongo to avoid ObjectID usage
    if "_id" not in doc:
        doc["_id"] = doc.get("id", str(uuid.uuid4()))
    await db[collection].insert_one(doc)

def _safe_json_extract(text: str) -> Dict[str, Any]:
    # Try to parse as JSON directly
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try to extract JSON code block
    m = re.search(r"\{[\s\S]*\}")
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    raise ValueError("Could not parse JSON from AI response")

async def _keyword_snippets(course: Dict[str, Any], query: str, max_chars: int = 4000) -> str:
    # Simple keyword-based retrieval from lessons and quiz
    text_blobs: List[str] = []
    for lesson in course.get("lessons", []):
        t = f"Lesson: {lesson.get('title')}\n{lesson.get('content')}"
        text_blobs.append(t)
    for q in course.get("quiz", []):
        opts = "\n".join([f"- {o.get('text')} ({'correct' if o.get('is_correct') else 'wrong'})" for o in q.get("options", [])])
        text_blobs.append(f"Q: {q.get('question')}\n{opts}\nExplanation: {q.get('explanation', '')}")
    # Rank by keyword overlap
    tokens = set([w.lower() for w in re.findall(r"\w+", query)])
    scored = []
    for blob in text_blobs:
        words = set([w.lower() for w in re.findall(r"\w+", blob)])
        score = len(tokens & words)
        scored.append((score, blob))
    scored.sort(reverse=True, key=lambda x: x[0])
    combined = "\n\n".join([b for _, b in scored])
    return combined[:max_chars]

# --------- Routes ---------
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    await _insert_one("status_checks", status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    # Ensure id present (using stored dicts)
    return [StatusCheck(**sc) for sc in status_checks]

# ---- AI: Generate Course ----
@api_router.post("/ai/generate_course", response_model=Course)
async def generate_course(req: GenerateCourseRequest):
    system_message = (
        "You are an expert instructional designer. Produce rigorous course content. "
        "Always output strict JSON following the provided schema."
    )
    prompt = f"""
Create a complete course on the topic: {req.topic}
Audience: {req.audience}
Difficulty: {req.difficulty}
Number of lessons: {req.lessons_count}

Return ONLY JSON with this exact schema:
{{
  "topic": string,
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
Ensure options have EXACTLY one is_correct=true. Keep content comprehensive but concise.
"""
    try:
        chat = _get_ai(api_key=None, session_id=f"course-gen-{uuid.uuid4()}", system_message=system_message)
        ai_resp = await chat.send_message(UserMessage(text=prompt))
        data = _safe_json_extract(str(ai_resp))
    except Exception as e:
        logger.exception("AI generation failed")
        raise HTTPException(status_code=500, detail=f"AI generation failed: {e}")

    # Validate and coerce to Course model
    try:
        lessons = [CourseLesson(title=l.get("title", "Untitled"), content=l.get("content", "")) for l in data.get("lessons", [])][: req.lessons_count]
        # normalize quiz
        quiz: List[QuizQuestion] = []
        for q in data.get("quiz", [])[: max(3, req.lessons_count)]:
            options = [
                QuizOption(text=o.get("text", ""), is_correct=bool(o.get("is_correct", False)))
                for o in q.get("options", [])[:4]
            ]
            # If not exactly one correct, fix heuristic: set first as correct
            if sum(1 for o in options if o.is_correct) != 1 and options:
                for i, o in enumerate(options):
                    o.is_correct = (i == 0)
            quiz.append(
                QuizQuestion(
                    question=q.get("question", ""),
                    options=options,
                    explanation=q.get("explanation") or ""
                )
            )
        course = Course(
            topic=data.get("topic", req.topic),
            audience=data.get("audience", req.audience),
            difficulty=data.get("difficulty", req.difficulty),
            lessons_count=len(lessons),
            lessons=lessons,
            quiz=quiz,
        )
        # Persist
        doc = course.dict()
        doc["_id"] = course.id
        await db.courses.insert_one(doc)
        return course
    except Exception as e:
        logger.exception("Failed to build Course model")
        raise HTTPException(status_code=500, detail=f"Invalid AI response structure: {e}")

# ---- Courses ----
@api_router.get("/courses", response_model=List[Course])
async def list_courses():
    docs = await db.courses.find().sort("created_at", -1).to_list(100)
    return [Course(**d) for d in docs]

@api_router.get("/courses/{course_id}", response_model=Course)
async def get_course(course_id: str):
    doc = await db.courses.find_one({"_id": course_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Course not found")
    return Course(**doc)

# ---- Chat ----
@api_router.post("/ai/chat")
async def course_chat(req: ChatRequest):
    # Load course
    course = await db.courses.find_one({"_id": req.course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    # Compose context
    context = await _keyword_snippets(course, req.message)
    system_message = (
        "You are a helpful course tutor. Answer accurately and concisely based on the provided course content. "
        "If the answer is not in the material, say you are unsure."
    )
    user_text = f"Course context as reference (do not reveal this blob verbatim):\n\n{context}\n\nUser question: {req.message}"

    try:
        chat = _get_ai(api_key=None, session_id=req.session_id, system_message=system_message)
        ai_resp = await chat.send_message(UserMessage(text=user_text))
        ai_resp_str = str(ai_resp)
    except Exception as e:
        logger.exception("AI chat failed")
        raise HTTPException(status_code=500, detail=f"AI chat failed: {e}")

    # store both messages
    user_msg = ChatMessageModel(course_id=req.course_id, session_id=req.session_id, role="user", message=req.message)
    asst_msg = ChatMessageModel(course_id=req.course_id, session_id=req.session_id, role="assistant", message=ai_resp_str)
    await _insert_one("chats", user_msg.dict())
    await _insert_one("chats", asst_msg.dict())

    return {"reply": ai_resp_str, "assistant_message_id": asst_msg.id}

@api_router.get("/chats/{course_id}/{session_id}", response_model=List[ChatMessageModel])
async def get_chat_history(course_id: str, session_id: str):
    docs = await db.chats.find({"course_id": course_id, "session_id": session_id}).sort("created_at", 1).to_list(1000)
    return [ChatMessageModel(**d) for d in docs]

# Include the router in the main app
app.include_router(api_router)

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