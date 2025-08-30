from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from database import get_database, get_fs_bucket, _uuid
from auth import _current_user
from models import (
    QuestionBank, QuestionItem, QuizTemplate, ProctoringSession,
    AcademicIntegrityReport, BlockchainCredential
)
from config import settings

# AI integrations
try:
    import google.generativeai as genai
except Exception:
    genai = None

assessment_router = APIRouter()

def _get_ai():
    if genai is None:
        raise HTTPException(status_code=500, detail="AI dependency not installed")
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="No AI key configured")
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
        import re
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    raise ValueError("Could not parse JSON from AI response")


# Question Bank Management
@assessment_router.post("/question-banks")
async def create_question_bank(bank_data: dict, user=Depends(_current_user)):
    """Create a new question bank"""
    db = get_database()

    # Check permissions
    if not await _can_manage_question_banks(user["id"], bank_data.get("tenant_id")):
        raise HTTPException(403, "Insufficient permissions")

    bank = QuestionBank(
        tenant_id=bank_data["tenant_id"],
        name=bank_data["name"],
        description=bank_data.get("description"),
        subject=bank_data["subject"],
        grade_level=bank_data.get("grade_level"),
        tags=bank_data.get("tags", []),
        created_by=user["id"]
    )

    doc = bank.dict()
    doc["_id"] = bank.id
    await db.question_banks.insert_one(doc)

    return bank


@assessment_router.get("/question-banks")
async def list_question_banks(tenant_id: str, user=Depends(_current_user)):
    """List question banks for a tenant"""
    db = get_database()

    if not await _has_tenant_access(user["id"], tenant_id):
        raise HTTPException(403, "Access denied")

    banks = await db.question_banks.find({
        "$or": [
            {"tenant_id": tenant_id},
            {"is_public": True}
        ]
    }).to_list(100)

    return banks


@assessment_router.get("/question-banks/{bank_id}/questions")
async def get_questions_for_bank(bank_id: str, user=Depends(_current_user)):
    """Get all questions for a specific question bank"""
    db = get_database()

    # Check if bank exists and user has access
    bank = await db.question_banks.find_one({"_id": bank_id})
    if not bank:
        raise HTTPException(404, "Question bank not found")

    if not await _can_access_bank(user["id"], bank):
        raise HTTPException(403, "Access denied")

    questions = await db.question_items.find({"bank_id": bank_id}).to_list(1000)

    return questions


@assessment_router.get("/quiz-templates")
async def list_quiz_templates(tenant_id: str, user=Depends(_current_user)):
    """List quiz templates for a tenant"""
    db = get_database()

    if not await _has_tenant_access(user["id"], tenant_id):
        raise HTTPException(403, "Access denied")

    templates = await db.quiz_templates.find({
        "$or": [
            {"tenant_id": tenant_id},
            {"is_public": True}
        ]
    }).to_list(100)

    return templates


@assessment_router.post("/question-banks/{bank_id}/questions")
async def create_question(bank_id: str, question_data: dict, user=Depends(_current_user)):
    """Create a new question in a bank"""
    db = get_database()

    # Check if bank exists and user has access
    bank = await db.question_banks.find_one({"_id": bank_id})
    if not bank:
        raise HTTPException(404, "Question bank not found")

    if not await _can_access_bank(user["id"], bank):
        raise HTTPException(403, "Access denied")

    question = QuestionItem(
        bank_id=bank_id,
        type=question_data["type"],
        difficulty=question_data.get("difficulty", "medium"),
        points=question_data.get("points", 1.0),
        question_text=question_data["question_text"],
        question_data=question_data.get("question_data", {}),
        explanation=question_data.get("explanation"),
        tags=question_data.get("tags", []),
        learning_objectives=question_data.get("learning_objectives", []),
        created_by=user["id"],
        ai_generated=question_data.get("ai_generated", False)
    )

    doc = question.dict()
    doc["_id"] = question.id
    await db.question_items.insert_one(doc)

    return question


@assessment_router.post("/ai/generate-questions")
async def generate_questions_ai(request: dict, user=Depends(_current_user)):
    """Generate questions using AI"""
    db = get_database()

    # Check permissions
    if not await _can_manage_question_banks(user["id"], request.get("tenant_id")):
        raise HTTPException(403, "Insufficient permissions")

    prompt = f"""
    Generate {request.get('count', 5)} high-quality assessment questions for:
    Subject: {request.get('subject')}
    Topic: {request.get('topic')}
    Difficulty: {request.get('difficulty', 'medium')}
    Grade Level: {request.get('grade_level', 'general')}
    Learning Objectives: {', '.join(request.get('learning_objectives', []))}

    Generate questions in these formats:
    - Multiple Choice (4 options, 1 correct)
    - True/False
    - Short Answer
    - Essay
    - Code (if programming related)

    For each question, provide:
    - question_text
    - type (multiple_choice, true_false, short_answer, essay, code)
    - question_data (options for MC, correct answer, etc.)
    - explanation
    - difficulty
    - points
    - tags
    - learning_objectives

    Return as JSON array of question objects.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        questions_data = _safe_json_extract(response.text)

        # Create questions in database
        created_questions = []
        for q_data in questions_data:
            question = QuestionItem(
                bank_id=request["bank_id"],
                type=q_data["type"],
                difficulty=q_data.get("difficulty", "medium"),
                points=q_data.get("points", 1.0),
                question_text=q_data["question_text"],
                question_data=q_data.get("question_data", {}),
                explanation=q_data.get("explanation"),
                tags=q_data.get("tags", []),
                learning_objectives=q_data.get("learning_objectives", []),
                created_by=user["id"],
                ai_generated=True
            )

            doc = question.dict()
            doc["_id"] = question.id
            await db.question_items.insert_one(doc)
            created_questions.append(question)

        return {"questions": created_questions, "count": len(created_questions)}

    except Exception as e:
        raise HTTPException(500, f"AI generation failed: {str(e)}")


@assessment_router.post("/quiz-templates")
async def create_quiz_template(template_data: dict, user=Depends(_current_user)):
    """Create a quiz template"""
    db = get_database()

    if not await _can_manage_question_banks(user["id"], template_data.get("tenant_id")):
        raise HTTPException(403, "Insufficient permissions")

    template = QuizTemplate(
        tenant_id=template_data["tenant_id"],
        name=template_data["name"],
        description=template_data.get("description"),
        settings=template_data.get("settings", {}),
        question_pools=template_data.get("question_pools", []),
        created_by=user["id"]
    )

    doc = template.dict()
    doc["_id"] = template.id
    await db.quiz_templates.insert_one(doc)

    return template


@assessment_router.post("/quizzes/{quiz_id}/attempts")
async def start_quiz_attempt(quiz_id: str, attempt_data: dict, user=Depends(_current_user)):
    """Start a quiz attempt"""
    db = get_database()

    # Check if quiz exists and user has access
    quiz = await db.quizzes.find_one({"_id": quiz_id})
    if not quiz:
        raise HTTPException(404, "Quiz not found")

    # Check enrollment
    enrollment = await db.enrollments.find_one({
        "user_id": user["id"],
        "section_id": quiz.get("section_id")
    })
    if not enrollment:
        raise HTTPException(403, "Not enrolled in this course section")

    # Check attempt limits
    existing_attempts = await db.quiz_attempts.count_documents({
        "quiz_id": quiz_id,
        "user_id": user["id"]
    })

    max_attempts = quiz.get("settings", {}).get("attempts_allowed", 1)
    if existing_attempts >= max_attempts:
        raise HTTPException(400, "Maximum attempts reached")

    # Create attempt
    attempt = {
        "_id": _uuid(),
        "quiz_id": quiz_id,
        "user_id": user["id"],
        "started_at": datetime.utcnow(),
        "answers": {},
        "time_remaining": quiz.get("settings", {}).get("time_limit"),
        "status": "in_progress"
    }

    await db.quiz_attempts.insert_one(attempt)

    # Start proctoring if enabled
    if quiz.get("settings", {}).get("proctoring_enabled"):
        await _start_proctoring_session(attempt["_id"], user["id"])

    return attempt


@assessment_router.put("/quiz-attempts/{attempt_id}/answers")
async def update_quiz_answers(attempt_id: str, answers: dict, user=Depends(_current_user)):
    """Update answers for a quiz attempt"""
    db = get_database()

    attempt = await db.quiz_attempts.find_one({"_id": attempt_id, "user_id": user["id"]})
    if not attempt:
        raise HTTPException(404, "Attempt not found")

    if attempt["status"] != "in_progress":
        raise HTTPException(400, "Attempt is not in progress")

    # Update answers
    await db.quiz_attempts.update_one(
        {"_id": attempt_id},
        {"$set": {"answers": answers}}
    )

    return {"status": "updated"}


@assessment_router.post("/quiz-attempts/{attempt_id}/finish")
async def finish_quiz_attempt(attempt_id: str, user=Depends(_current_user)):
    """Finish a quiz attempt and calculate score"""
    db = get_database()

    attempt = await db.quiz_attempts.find_one({"_id": attempt_id, "user_id": user["id"]})
    if not attempt:
        raise HTTPException(404, "Attempt not found")

    if attempt["status"] != "in_progress":
        raise HTTPException(400, "Attempt is not in progress")

    # Get quiz and questions
    quiz = await db.quizzes.find_one({"_id": attempt["quiz_id"]})
    questions = []
    for item in quiz.get("items", []):
        question = await db.question_items.find_one({"_id": item["question_id"]})
        if question:
            questions.append(question)

    # Calculate score
    total_score = 0
    max_score = sum(q["points"] for q in questions)

    for i, question in enumerate(questions):
        answer = attempt["answers"].get(str(i))
        if answer:
            # Simple scoring logic - in production, this would be more sophisticated
            if question["type"] == "multiple_choice":
                correct_answer = question["question_data"].get("correct_answer")
                if answer == correct_answer:
                    total_score += question["points"]
            elif question["type"] == "true_false":
                correct_answer = question["question_data"].get("correct_answer")
                if str(answer).lower() == str(correct_answer).lower():
                    total_score += question["points"]
            # Add more question type scoring logic here

    # Update attempt
    await db.quiz_attempts.update_one(
        {"_id": attempt_id},
        {
            "$set": {
                "finished_at": datetime.utcnow(),
                "score": total_score,
                "max_score": max_score,
                "percentage": (total_score / max_score * 100) if max_score > 0 else 0,
                "status": "completed"
            }
        }
    )

    # Stop proctoring
    await _stop_proctoring_session(attempt_id)

    return {
        "score": total_score,
        "max_score": max_score,
        "percentage": (total_score / max_score * 100) if max_score > 0 else 0
    }


@assessment_router.post("/proctoring/sessions")
async def start_proctoring_session(session_data: dict, user=Depends(_current_user)):
    """Start a proctoring session"""
    db = get_database()

    session = ProctoringSession(
        quiz_attempt_id=session_data["quiz_attempt_id"],
        proctor_id=user["id"],
        session_start=datetime.utcnow(),
        ai_monitoring_enabled=session_data.get("ai_monitoring", True)
    )

    doc = session.dict()
    doc["_id"] = session.id
    await db.proctoring_sessions.insert_one(doc)

    return session


@assessment_router.post("/proctoring/incidents")
async def report_proctoring_incident(incident_data: dict, user=Depends(_current_user)):
    """Report a proctoring incident"""
    db = get_database()

    # Find active session
    session = await db.proctoring_sessions.find_one({
        "quiz_attempt_id": incident_data["quiz_attempt_id"],
        "status": "active"
    })

    if not session:
        raise HTTPException(404, "Active proctoring session not found")

    incident = {
        "timestamp": datetime.utcnow(),
        "type": incident_data["type"],
        "description": incident_data["description"],
        "severity": incident_data.get("severity", "medium"),
        "evidence": incident_data.get("evidence", []),
        "reported_by": user["id"]
    }

    await db.proctoring_sessions.update_one(
        {"_id": session["_id"]},
        {"$push": {"incidents": incident}}
    )

    return {"status": "reported", "incident": incident}


@assessment_router.post("/academic-integrity/reports")
async def create_integrity_report(report_data: dict, user=Depends(_current_user)):
    """Create an academic integrity report"""
    db = get_database()

    # Check permissions
    if not await _can_manage_integrity_reports(user["id"], report_data.get("tenant_id")):
        raise HTTPException(403, "Insufficient permissions")

    report = AcademicIntegrityReport(
        submission_id=report_data["submission_id"],
        report_type=report_data["report_type"],
        vendor=report_data.get("vendor", "manual"),
        score=report_data.get("score", 0.0),
        matches=report_data.get("matches", []),
        ai_probability=report_data.get("ai_probability"),
        flagged_content=report_data.get("flagged_content", []),
        reviewed_by=user["id"] if report_data.get("auto_review") else None
    )

    doc = report.dict()
    doc["_id"] = report.id
    await db.academic_integrity_reports.insert_one(doc)

    return report


@assessment_router.post("/credentials/issue")
async def issue_blockchain_credential(credential_data: dict, user=Depends(_current_user)):
    """Issue a blockchain-verifiable credential"""
    db = get_database()

    # Check permissions
    if not await _can_issue_credentials(user["id"], credential_data.get("tenant_id")):
        raise HTTPException(403, "Insufficient permissions")

    # Verify completion
    if credential_data["credential_type"] == "certificate":
        progress = await db.course_progress.find_one({
            "user_id": credential_data["user_id"],
            "course_id": credential_data["course_id"],
            "completed": True
        })
        if not progress:
            raise HTTPException(400, "Course not completed")

    credential = BlockchainCredential(
        user_id=credential_data["user_id"],
        credential_type=credential_data["credential_type"],
        credential_id=credential_data["credential_id"],
        issuer_did=credential_data.get("issuer_did"),
        subject_did=credential_data.get("subject_did"),
        expiration_date=credential_data.get("expiration_date"),
        credential_data=credential_data["credential_data"],
        verification_url=credential_data.get("verification_url")
    )

    doc = credential.dict()
    doc["_id"] = credential.id
    await db.blockchain_credentials.insert_one(doc)

    return credential


@assessment_router.get("/credentials/verify/{credential_id}")
async def verify_credential(credential_id: str):
    """Verify a blockchain credential"""
    db = get_database()

    credential = await db.blockchain_credentials.find_one({"credential_id": credential_id})
    if not credential:
        raise HTTPException(404, "Credential not found")

    # Check expiration
    if credential.get("expiration_date"):
        if datetime.utcnow() > credential["expiration_date"]:
            return {"valid": False, "reason": "expired"}

    # Check revocation
    if credential.get("status") == "revoked":
        return {"valid": False, "reason": "revoked"}

    return {
        "valid": True,
        "credential": credential,
        "verified_at": datetime.utcnow()
    }


# Helper functions
async def _can_manage_question_banks(user_id: str, tenant_id: str) -> bool:
    """Check if user can manage question banks"""
    from routes.rbac import check_permission
    return await check_permission(user_id, "question_banks:manage", tenant_id)


async def _has_tenant_access(user_id: str, tenant_id: str) -> bool:
    """Check if user has access to tenant"""
    from routes.rbac import check_permission
    return await check_permission(user_id, "tenant:access", tenant_id)


async def _can_access_bank(user_id: str, bank: dict) -> bool:
    """Check if user can access a question bank"""
    if bank.get("is_public"):
        return True
    if bank.get("created_by") == user_id:
        return True
    # Check tenant permissions
    return await _has_tenant_access(user_id, bank["tenant_id"])


async def _can_manage_integrity_reports(user_id: str, tenant_id: str) -> bool:
    """Check if user can manage integrity reports"""
    from routes.rbac import check_permission
    return await check_permission(user_id, "integrity:manage", tenant_id)


async def _can_issue_credentials(user_id: str, tenant_id: str) -> bool:
    """Check if user can issue credentials"""
    from routes.rbac import check_permission
    return await check_permission(user_id, "credentials:issue", tenant_id)


async def _start_proctoring_session(attempt_id: str, user_id: str):
    """Start proctoring for a quiz attempt"""
    # Implementation for proctoring session start
    pass


async def _stop_proctoring_session(attempt_id: str):
    """Stop proctoring for a quiz attempt"""
    # Implementation for proctoring session stop
    pass