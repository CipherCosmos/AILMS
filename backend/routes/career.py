from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from database import get_database, _insert_one, _update_one, _find_one
from auth import _current_user, _require_role
from models import (
    CareerGoal, CareerRecommendation, SkillAssessment, InterviewQuestion,
    ResumeTemplate, JobPosting, InternshipProject
)
from config import settings
import json

# AI integrations
try:
    import google.generativeai as genai
except Exception:
    genai = None

def _get_ai():
    if genai is None:
        raise HTTPException(status_code=500, detail="AI dependency not installed.")
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="No AI key configured.")
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(settings.default_llm_model)

career_router = APIRouter()

@career_router.post("/goals")
async def create_career_goal(goal: CareerGoal, user=Depends(_current_user)):
    """Create a career goal for the user."""
    goal.user_id = user["id"]
    doc = goal.dict()
    doc["_id"] = goal.id
    db = get_database()
    await db.career_goals.insert_one(doc)
    return goal

@career_router.get("/goals")
async def get_career_goals(user=Depends(_current_user)):
    """Get user's career goals."""
    db = get_database()
    docs = await db.career_goals.find({"user_id": user["id"]}).to_list(100)
    return [CareerGoal(**d) for d in docs]

@career_router.post("/ai/recommendations")
async def get_ai_career_recommendations(user=Depends(_current_user)):
    """Get AI-powered career recommendations."""
    db = get_database()

    # Get user's profile and goals
    profile = await db.user_profiles.find_one({"user_id": user["id"]})
    goals = await db.career_goals.find({"user_id": user["id"]}).to_list(10)

    if not profile:
        raise HTTPException(400, "Please complete your profile first")

    # Build AI prompt
    prompt = f"""
    Based on this user profile, provide career recommendations:

    User Profile:
    - Skills: {', '.join(profile.get('skills', []))}
    - Interests: {', '.join(profile.get('interests', []))}
    - Learning Goals: {', '.join(profile.get('learning_goals', []))}

    Career Goals:
    {chr(10).join([f"- {g['title']}: {g['description']}" for g in goals])}

    Provide 3 career recommendations with:
    1. Career title
    2. Match score (0-100)
    3. Required skills
    4. Suggested courses
    5. Salary range
    6. Job market trend

    Return as JSON array.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        recommendations = json.loads(response.text.replace("```json", "").replace("```", ""))

        # Save recommendations
        saved_recs = []
        for rec in recommendations[:3]:
            rec_obj = CareerRecommendation(
                user_id=user["id"],
                recommended_career=rec["career"],
                match_score=rec["match_score"],
                required_skills=rec["required_skills"],
                suggested_courses=rec["suggested_courses"],
                salary_range=rec["salary_range"],
                job_market_trend=rec["job_market_trend"]
            )
            doc = rec_obj.dict()
            doc["_id"] = rec_obj.id
            await db.career_recommendations.insert_one(doc)
            saved_recs.append(rec_obj)

        return saved_recs

    except Exception as e:
        raise HTTPException(500, f"AI recommendation failed: {str(e)}")

@career_router.get("/recommendations")
async def get_career_recommendations(user=Depends(_current_user)):
    """Get user's career recommendations."""
    db = get_database()
    docs = await db.career_recommendations.find({"user_id": user["id"]}).sort("generated_at", -1).to_list(10)
    return [CareerRecommendation(**d) for d in docs]

@career_router.post("/ai/resume")
async def generate_ai_resume(user=Depends(_current_user)):
    """Generate AI-powered resume."""
    db = get_database()

    # Get user profile and projects
    profile = await db.user_profiles.find_one({"user_id": user["id"]})
    projects = await db.projects.find({"user_id": user["id"]}).to_list(10)

    if not profile:
        raise HTTPException(400, "Please complete your profile first")

    prompt = f"""
    Generate a professional resume based on this user data:

    Name: {user['name']}
    Bio: {profile.get('bio', '')}
    Skills: {', '.join(profile.get('skills', []))}
    Experience: {profile.get('experience', [])}
    Education: {profile.get('education', [])}

    Projects:
    {chr(10).join([f"- {p['title']}: {p['description']}" for p in projects])}

    Generate a well-structured resume with sections for:
    - Contact Information
    - Professional Summary
    - Skills
    - Experience
    - Education
    - Projects

    Return as JSON with resume sections.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        resume_data = json.loads(response.text.replace("```json", "").replace("```", ""))

        # Save resume data
        await db.user_profiles.update_one(
            {"user_id": user["id"]},
            {"$set": {"resume_data": resume_data}}
        )

        return resume_data

    except Exception as e:
        raise HTTPException(500, f"Resume generation failed: {str(e)}")

@career_router.post("/ai/interview-practice")
async def get_interview_questions(category: str = "technical", user=Depends(_current_user)):
    """Get AI-generated interview questions for practice."""
    prompt = f"""
    Generate 5 interview questions for the category: {category}

    Include:
    1. Question text
    2. Category (technical, behavioral, situational)
    3. Difficulty level
    4. Sample answer
    5. Key evaluation points

    Return as JSON array.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        questions = json.loads(response.text.replace("```json", "").replace("```", ""))

        # Save questions
        db = get_database()
        saved_questions = []
        for q in questions:
            q_obj = InterviewQuestion(
                question=q["question"],
                category=q["category"],
                difficulty=q["difficulty"],
                sample_answer=q["sample_answer"]
            )
            doc = q_obj.dict()
            doc["_id"] = q_obj.id
            await db.interview_questions.insert_one(doc)
            saved_questions.append(q_obj)

        return saved_questions

    except Exception as e:
        raise HTTPException(500, f"Interview questions generation failed: {str(e)}")

@career_router.get("/job-postings")
async def get_job_postings(user=Depends(_current_user)):
    """Get available job postings."""
    db = get_database()
    docs = await db.job_postings.find({"is_active": True}).sort("posted_at", -1).to_list(50)
    return [JobPosting(**d) for d in docs]

@career_router.get("/internships")
async def get_internships(user=Depends(_current_user)):
    """Get available internship opportunities."""
    db = get_database()
    docs = await db.internship_projects.find({"is_active": True}).sort("created_at", -1).to_list(50)
    return [InternshipProject(**d) for d in docs]