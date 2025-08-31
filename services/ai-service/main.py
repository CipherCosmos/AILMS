"""
AI Service - Handles AI-powered features and content generation
"""
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
import json
import re
from datetime import datetime, timezone
from typing import Optional
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.config.config import settings
from shared.database.database import get_database
from shared.models.models import ContentGenerationRequest, GeneratedContent

app = FastAPI(title='AI Service', version='1.0.0')

# AI integrations
try:
    import google.generativeai as genai
except Exception:
    genai = None

def _get_ai():
    """Get AI model instance"""
    if genai is None:
        raise HTTPException(
            status_code=500,
            detail="AI dependency not installed. Please install google-generativeai.",
        )
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=500,
            detail="No AI key configured. Set GEMINI_API_KEY in backend/.env",
        )
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(settings.default_llm_model)

def _safe_json_extract(text: str) -> dict:
    """Extract JSON from AI response safely"""
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

# Mock user authentication for service-to-service calls
async def _current_user(token: Optional[str] = None):
    """Mock user authentication for service-to-service calls"""
    return {"id": "user_123", "role": "instructor", "email": "user@example.com", "name": "Test User"}

def _require_role(user, allowed: list[str]):
    """Check if user has required role"""
    if user.get("role") not in allowed:
        raise HTTPException(403, "Insufficient permissions")

@app.post("/ai/generate-course")
async def generate_course(request: dict, user=Depends(_current_user)):
    """Generate comprehensive course using AI"""
    _require_role(user, ["admin", "instructor"])

    try:
        topic = request.get("topic", "")
        audience = request.get("audience", "general")
        difficulty = request.get("difficulty", "intermediate")
        lesson_count = min(int(request.get("lesson_count", 10)), 25)

        # Generate course structure
        course_data = await _generate_course_structure(topic, audience, difficulty, lesson_count)

        # Generate detailed content for each lesson
        detailed_lessons = []
        for i, lesson_outline in enumerate(course_data.get("lessons", [])):
            lesson_content = await _generate_detailed_lesson(
                lesson_outline, topic, audience, difficulty, i + 1
            )
            detailed_lessons.append(lesson_content)

        # Generate quizzes
        quizzes = await _generate_course_quizzes(detailed_lessons, topic, difficulty)

        return {
            "title": course_data.get("title", f"AI Generated: {topic}"),
            "description": course_data.get("description", ""),
            "audience": audience,
            "difficulty": difficulty,
            "lessons": detailed_lessons,
            "quiz": quizzes,
            "learning_objectives": course_data.get("learning_objectives", []),
            "prerequisites": course_data.get("prerequisites", []),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "lesson_count": len(detailed_lessons)
        }

    except Exception as e:
        raise HTTPException(500, f"AI course generation failed: {str(e)}")

async def _generate_course_structure(topic: str, audience: str, difficulty: str, lesson_count: int) -> dict:
    """Generate course structure using AI"""
    prompt = f"""
    Create a detailed course structure for: {topic}

    Target Audience: {audience}
    Difficulty Level: {difficulty}
    Number of Lessons: {lesson_count}

    Return JSON with:
    {{
        "title": "Course title",
        "description": "Detailed course description (200-300 words)",
        "learning_objectives": ["objective1", "objective2"],
        "prerequisites": ["prereq1", "prereq2"],
        "lessons": [
            {{
                "id": "lesson_1",
                "title": "Lesson Title",
                "overview": "Brief overview of what will be covered",
                "duration_minutes": 90,
                "key_concepts": ["concept1", "concept2"],
                "learning_outcomes": ["outcome1", "outcome2"]
            }}
        ]
    }}

    Make the course structure comprehensive and well-organized.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return _safe_json_extract(response.text)
    except Exception as e:
        raise HTTPException(500, f"Course structure generation failed: {e}")

async def _generate_detailed_lesson(lesson_outline: dict, topic: str, audience: str, difficulty: str, lesson_number: int) -> dict:
    """Generate detailed lesson content"""
    lesson_title = lesson_outline.get("title", "")
    key_concepts = lesson_outline.get("key_concepts", [])

    prompt = f"""
    Create comprehensive content for Lesson {lesson_number}: {lesson_title}
    Course Topic: {topic}
    Target Audience: {audience}
    Difficulty Level: {difficulty}

    Key Concepts: {', '.join(key_concepts)}

    Provide detailed lesson content including:
    - Step-by-step explanations
    - Real-world examples and case studies
    - Practical exercises and implementations
    - Code examples (if applicable)
    - Common mistakes and solutions
    - Further reading resources

    Make the content engaging, practical, and comprehensive (600-1000 words).
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)

        return {
            "id": lesson_outline.get("id", f"lesson_{lesson_number}"),
            "title": lesson_title,
            "content": response.text,
            "duration_minutes": lesson_outline.get("duration_minutes", 90),
            "key_concepts": key_concepts,
            "learning_outcomes": lesson_outline.get("learning_outcomes", []),
            "order_index": lesson_number - 1
        }
    except Exception as e:
        raise HTTPException(500, f"Detailed lesson generation failed: {e}")

async def _generate_course_quizzes(lessons: list, topic: str, difficulty: str) -> list:
    """Generate quizzes for the course"""
    prompt = f"""
    Create a comprehensive quiz for the course: {topic}
    Difficulty: {difficulty}
    Course has {len(lessons)} lessons

    Generate 20 multiple choice questions covering all major concepts.
    Each question should have 4 options with exactly one correct answer.

    Return format:
    [
        {{
            "question": "Question text",
            "options": [
                {{"text": "Option 1", "is_correct": false}},
                {{"text": "Option 2", "is_correct": true}},
                ...
            ],
            "explanation": "Explanation of correct answer"
        }}
    ]
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        quiz_data = _safe_json_extract(response.text)

        quizzes = []
        for q in quiz_data[:20]:  # Limit to 20 questions
            options = [
                {"text": opt.get("text", ""), "is_correct": bool(opt.get("is_correct", False))}
                for opt in q.get("options", [])[:4]
            ]
            if options:
                quiz_question = {
                    "id": f"quiz_{len(quizzes) + 1}",
                    "question": q.get("question", ""),
                    "options": options,
                    "explanation": q.get("explanation", "")
                }
                quizzes.append(quiz_question)

        return quizzes
    except Exception:
        return []

@app.post("/ai/enhance-content")
async def enhance_content(request: dict, user=Depends(_current_user)):
    """Enhance lesson content using AI"""
    _require_role(user, ["admin", "instructor"])

    content = request.get("content", "")
    enhancement_type = request.get("type", "comprehensive")
    target_audience = request.get("audience", "general")
    difficulty_level = request.get("difficulty", "intermediate")

    prompts = {
        "comprehensive": f"""
        Enhance this lesson content comprehensively:

        Original Content: {content}
        Target Audience: {target_audience}
        Difficulty Level: {difficulty_level}

        Add:
        1. Real-world examples and case studies
        2. Step-by-step explanations
        3. Visual descriptions and analogies
        4. Common misconceptions and clarifications
        5. Practical applications
        6. Assessment questions with answers

        Make the content 2-3 times more detailed while maintaining clarity.
        """,

        "examples": f"""
        Add comprehensive real-world examples to this content:

        Original Content: {content}
        Target Audience: {target_audience}

        Add 4-6 detailed examples including:
        - Industry case studies
        - Historical examples
        - Personal success stories
        - Common problem-solving scenarios
        """,

        "practical": f"""
        Add practical exercises and implementations to this lesson:

        Original Content: {content}
        Difficulty Level: {difficulty_level}

        Add:
        1. Hands-on exercises
        2. Code examples (if applicable)
        3. Step-by-step tutorials
        4. Practice problems with solutions
        5. Project ideas
        6. Implementation checklists
        """
    }

    prompt = prompts.get(enhancement_type, prompts["comprehensive"])

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return {
            "enhanced_content": response.text,
            "original_content": content,
            "enhancement_type": enhancement_type,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"Content enhancement failed: {str(e)}")

@app.post("/ai/generate-quiz")
async def generate_quiz(request: dict, user=Depends(_current_user)):
    """Generate quiz questions using AI"""
    _require_role(user, ["admin", "instructor"])

    topic = request.get("topic", "")
    difficulty = request.get("difficulty", "intermediate")
    question_count = min(int(request.get("question_count", 10)), 20)

    prompt = f"""
    Generate {question_count} quiz questions on: {topic}
    Difficulty: {difficulty}

    Include a mix of:
    - Multiple choice questions (70%)
    - True/False questions (20%)
    - Short answer questions (10%)

    For multiple choice questions, provide 4 options with exactly one correct answer.
    Include explanations for all correct answers.
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)
        return {
            "quiz_questions": response.text,
            "topic": topic,
            "difficulty": difficulty,
            "question_count": question_count,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"AI quiz generation failed: {str(e)}")

@app.post("/ai/analyze-performance")
async def analyze_performance(request: dict, user=Depends(_current_user)):
    """Analyze student performance using AI"""
    user_id = request.get("user_id")
    course_id = request.get("course_id")

    # Get performance data from database
    db = get_database()
    progress_data = await db.course_progress.find({"user_id": user_id}).to_list(20)
    submissions = await db.submissions.find({"user_id": user_id}).to_list(50)

    # Calculate metrics
    completed_courses = len([p for p in progress_data if p.get("completed")])
    avg_progress = sum([p.get("overall_progress", 0) for p in progress_data]) / len(progress_data) if progress_data else 0
    total_submissions = len(submissions)

    # Generate AI analysis
    prompt = f"""
    Analyze this student's performance:

    Performance Summary:
    - Courses Enrolled: {len(progress_data)}
    - Courses Completed: {completed_courses}
    - Average Progress: {avg_progress:.1f}%
    - Total Submissions: {total_submissions}

    Provide:
    1. Performance assessment
    2. Strengths and areas for improvement
    3. Learning pattern analysis
    4. Personalized recommendations
    5. Predicted completion trajectory
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)

        return {
            "analysis": response.text,
            "metrics": {
                "completed_courses": completed_courses,
                "average_progress": round(avg_progress, 1),
                "total_submissions": total_submissions
            },
            "recommendations": [
                "Focus on consistent daily study sessions",
                "Practice more hands-on exercises",
                "Review fundamental concepts regularly"
            ],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"Performance analysis failed: {str(e)}")

@app.post("/ai/personalize-learning")
async def personalize_learning(request: dict, user=Depends(_current_user)):
    """Generate personalized learning recommendations"""
    user_id = request.get("user_id")
    learning_goals = request.get("learning_goals", [])
    current_level = request.get("current_level", "beginner")
    preferred_style = request.get("preferred_style", "visual")

    prompt = f"""
    Create a personalized learning plan for:

    Learning Goals: {', '.join(learning_goals) if learning_goals else 'General skill development'}
    Current Level: {current_level}
    Preferred Learning Style: {preferred_style}

    Provide:
    1. Customized study schedule
    2. Recommended learning resources
    3. Practice exercises and projects
    4. Assessment strategies
    5. Motivation and progress tracking tips
    6. Timeline and milestones
    """

    try:
        model = _get_ai()
        response = model.generate_content(prompt)

        return {
            "personalized_plan": response.text,
            "learning_goals": learning_goals,
            "current_level": current_level,
            "preferred_style": preferred_style,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"Personalization failed: {str(e)}")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ai"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "AI Service", "status": "running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=settings.environment == 'development')