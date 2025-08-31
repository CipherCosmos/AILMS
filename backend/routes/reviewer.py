from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
from database import get_database, _uuid
from auth import _current_user
from models import UserProfile, CareerProfile

reviewer_router = APIRouter()

@reviewer_router.get("/student-profiles")
async def get_student_profiles(search: Optional[str] = None, skills: Optional[str] = None, user=Depends(_current_user)):
    """Get student profiles for review"""
    db = get_database()

    # Check if user is a reviewer/employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["external_reviewer", "employer"]:
        raise HTTPException(403, "Reviewer/Employer access required")

    # Get student profiles (simplified - would filter based on permissions)
    students = [
        {
            "_id": "student1",
            "name": "Emma Johnson",
            "email": "emma.student@example.com",
            "grade": "10th Grade",
            "gpa": 3.8,
            "skills": ["Python", "JavaScript", "Data Analysis"],
            "projects": ["AI Chatbot", "Data Visualization Dashboard"],
            "certifications": ["Python Programming", "Web Development"],
            "work_experience": [],
            "availability": "available",
            "last_updated": (datetime.utcnow() - timedelta(days=2)).isoformat()
        },
        {
            "_id": "student2",
            "name": "Alex Johnson",
            "email": "alex.student@example.com",
            "grade": "8th Grade",
            "gpa": 3.6,
            "skills": ["Java", "SQL", "Machine Learning"],
            "projects": ["Mobile App Development", "Database Design"],
            "certifications": ["Java Programming", "Database Administration"],
            "work_experience": ["Summer Internship at Tech Corp"],
            "availability": "available",
            "last_updated": (datetime.utcnow() - timedelta(days=5)).isoformat()
        }
    ]

    # Apply filters
    if search:
        students = [s for s in students if search.lower() in s["name"].lower() or search.lower() in s["email"].lower()]

    if skills:
        skill_list = [s.strip() for s in skills.split(",")]
        students = [s for s in students if any(skill in s["skills"] for skill in skill_list)]

    return students

@reviewer_router.get("/student/{student_id}/detailed-profile")
async def get_student_detailed_profile(student_id: str, user=Depends(_current_user)):
    """Get detailed student profile for review"""
    db = get_database()

    # Check if user is a reviewer/employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["external_reviewer", "employer"]:
        raise HTTPException(403, "Reviewer/Employer access required")

    # Get detailed student profile
    profile = {
        "basic_info": {
            "name": "Emma Johnson",
            "email": "emma.student@example.com",
            "grade": "10th Grade",
            "school": "Lincoln High School",
            "gpa": 3.8,
            "graduation_date": "2025-06-15"
        },
        "academic_performance": {
            "courses": [
                {"name": "Advanced Mathematics", "grade": "A", "credits": 4},
                {"name": "Physics", "grade": "A-", "credits": 4},
                {"name": "English Literature", "grade": "A", "credits": 3}
            ],
            "test_scores": {
                "SAT": 1450,
                "ACT": 32,
                "AP_Calculus": 5,
                "AP_Physics": 4
            }
        },
        "skills_assessment": {
            "technical_skills": [
                {"skill": "Python", "level": "Advanced", "verified": True},
                {"skill": "JavaScript", "level": "Intermediate", "verified": True},
                {"skill": "Data Analysis", "level": "Advanced", "verified": False}
            ],
            "soft_skills": [
                {"skill": "Communication", "level": "Excellent"},
                {"skill": "Teamwork", "level": "Good"},
                {"skill": "Problem Solving", "level": "Excellent"}
            ]
        },
        "projects_portfolio": [
            {
                "title": "AI-Powered Chatbot",
                "description": "Developed an intelligent chatbot using NLP and machine learning",
                "technologies": ["Python", "TensorFlow", "Flask"],
                "github_url": "https://github.com/emma/ai-chatbot",
                "demo_url": "https://emma-chatbot.demo.com",
                "completion_date": "2024-01-15"
            },
            {
                "title": "Data Visualization Dashboard",
                "description": "Interactive dashboard for analyzing educational data",
                "technologies": ["React", "D3.js", "Node.js"],
                "github_url": "https://github.com/emma/data-viz",
                "demo_url": "https://emma-dashboard.demo.com",
                "completion_date": "2024-01-20"
            }
        ],
        "work_experience": [],
        "certifications": [
            {
                "name": "Python Programming Certification",
                "issuer": "Python Institute",
                "issue_date": "2023-11-15",
                "expiry_date": None,
                "credential_id": "PY-2023-001"
            },
            {
                "name": "Web Development Bootcamp",
                "issuer": "Tech Academy",
                "issue_date": "2023-09-30",
                "expiry_date": None,
                "credential_id": "WD-2023-045"
            }
        ],
        "recommendations": [
            {
                "from": "Dr. Sarah Mitchell",
                "position": "Mathematics Teacher",
                "relationship": "Teacher",
                "content": "Emma is an exceptional student with strong analytical skills and dedication to learning.",
                "date": "2024-01-10"
            }
        ],
        "extracurricular_activities": [
            "Math Club President",
            "Science Fair Winner 2023",
            "Volunteer Coding Instructor"
        ]
    }

    return profile

@reviewer_router.post("/schedule-interview")
async def schedule_interview(interview_data: dict, user=Depends(_current_user)):
    """Schedule an interview with a student"""
    db = get_database()

    # Check if user is a reviewer/employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["external_reviewer", "employer"]:
        raise HTTPException(403, "Reviewer/Employer access required")

    # Create interview record
    interview = {
        "_id": _uuid(),
        "reviewer_id": user["id"],
        "student_id": interview_data.get("student_id"),
        "scheduled_date": interview_data.get("scheduled_date"),
        "duration": interview_data.get("duration", 60),
        "interview_type": interview_data.get("interview_type", "technical"),
        "format": interview_data.get("format", "virtual"),
        "topics": interview_data.get("topics", []),
        "status": "scheduled",
        "created_at": datetime.utcnow().isoformat()
    }

    # Save interview
    await db.interviews.insert_one(interview)

    return {
        "interview_id": interview["_id"],
        "status": "scheduled",
        "message": "Interview scheduled successfully"
    }

@reviewer_router.get("/scheduled-interviews")
async def get_scheduled_interviews(user=Depends(_current_user)):
    """Get scheduled interviews"""
    db = get_database()

    # Check if user is a reviewer/employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["external_reviewer", "employer"]:
        raise HTTPException(403, "Reviewer/Employer access required")

    # Get scheduled interviews
    interviews = [
        {
            "_id": _uuid(),
            "student_name": "Emma Johnson",
            "student_id": "student1",
            "scheduled_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
            "duration": 60,
            "interview_type": "technical",
            "format": "virtual",
            "status": "scheduled",
            "topics": ["Python Programming", "Data Structures", "Problem Solving"]
        },
        {
            "_id": _uuid(),
            "student_name": "Alex Johnson",
            "student_id": "student2",
            "scheduled_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "duration": 45,
            "interview_type": "behavioral",
            "format": "virtual",
            "status": "scheduled",
            "topics": ["Teamwork", "Communication", "Leadership"]
        }
    ]

    return interviews

@reviewer_router.post("/submit-feedback")
async def submit_feedback(feedback_data: dict, user=Depends(_current_user)):
    """Submit feedback for a student"""
    db = get_database()

    # Check if user is a reviewer/employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["external_reviewer", "employer"]:
        raise HTTPException(403, "Reviewer/Employer access required")

    # Create feedback record
    feedback = {
        "_id": _uuid(),
        "reviewer_id": user["id"],
        "student_id": feedback_data.get("student_id"),
        "interview_id": feedback_data.get("interview_id"),
        "overall_rating": feedback_data.get("overall_rating"),
        "technical_skills": feedback_data.get("technical_skills", {}),
        "soft_skills": feedback_data.get("soft_skills", {}),
        "strengths": feedback_data.get("strengths", []),
        "areas_for_improvement": feedback_data.get("areas_for_improvement", []),
        "recommendation": feedback_data.get("recommendation"),
        "comments": feedback_data.get("comments"),
        "submitted_at": datetime.utcnow().isoformat()
    }

    # Save feedback
    await db.feedback.insert_one(feedback)

    return {
        "feedback_id": feedback["_id"],
        "status": "submitted",
        "message": "Feedback submitted successfully"
    }

@reviewer_router.get("/feedback-history")
async def get_feedback_history(user=Depends(_current_user)):
    """Get feedback history"""
    db = get_database()

    # Check if user is a reviewer/employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["external_reviewer", "employer"]:
        raise HTTPException(403, "Reviewer/Employer access required")

    # Get feedback history
    feedback_history = [
        {
            "_id": _uuid(),
            "student_name": "Emma Johnson",
            "student_id": "student1",
            "overall_rating": 4.5,
            "recommendation": "Strong Hire",
            "submitted_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
            "key_strengths": ["Technical Skills", "Problem Solving", "Communication"]
        },
        {
            "_id": _uuid(),
            "student_name": "Alex Johnson",
            "student_id": "student2",
            "overall_rating": 4.0,
            "recommendation": "Hire",
            "submitted_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
            "key_strengths": ["Teamwork", "Adaptability", "Learning Ability"]
        }
    ]

    return feedback_history

@reviewer_router.post("/request-verification")
async def request_skill_verification(verification_data: dict, user=Depends(_current_user)):
    """Request verification of a student's skills"""
    db = get_database()

    # Check if user is a reviewer/employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["external_reviewer", "employer"]:
        raise HTTPException(403, "Reviewer/Employer access required")

    # Create verification request
    verification = {
        "_id": _uuid(),
        "requester_id": user["id"],
        "student_id": verification_data.get("student_id"),
        "skill": verification_data.get("skill"),
        "assessment_type": verification_data.get("assessment_type", "project_review"),
        "deadline": verification_data.get("deadline"),
        "requirements": verification_data.get("requirements", []),
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }

    # Save verification request
    await db.verifications.insert_one(verification)

    return {
        "verification_id": verification["_id"],
        "status": "requested",
        "message": "Skill verification requested successfully"
    }

@reviewer_router.get("/verification-requests")
async def get_verification_requests(user=Depends(_current_user)):
    """Get verification requests"""
    db = get_database()

    # Check if user is a reviewer/employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["external_reviewer", "employer"]:
        raise HTTPException(403, "Reviewer/Employer access required")

    # Get verification requests
    verifications = [
        {
            "_id": _uuid(),
            "student_name": "Emma Johnson",
            "student_id": "student1",
            "skill": "Python Programming",
            "assessment_type": "coding_challenge",
            "status": "pending",
            "deadline": (datetime.utcnow() + timedelta(days=14)).isoformat(),
            "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
        },
        {
            "_id": _uuid(),
            "student_name": "Alex Johnson",
            "student_id": "student2",
            "skill": "Machine Learning",
            "assessment_type": "project_review",
            "status": "in_progress",
            "deadline": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat()
        }
    ]

    return verifications

@reviewer_router.post("/endorse-student")
async def endorse_student(endorsement_data: dict, user=Depends(_current_user)):
    """Endorse a student for specific skills"""
    db = get_database()

    # Check if user is a reviewer/employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["external_reviewer", "employer"]:
        raise HTTPException(403, "Reviewer/Employer access required")

    # Create endorsement
    endorsement = {
        "_id": _uuid(),
        "endorser_id": user["id"],
        "endorser_name": user_doc.get("name", ""),
        "endorser_title": user_doc.get("title", "External Reviewer"),
        "student_id": endorsement_data.get("student_id"),
        "skill": endorsement_data.get("skill"),
        "level": endorsement_data.get("level", "proficient"),
        "comment": endorsement_data.get("comment", ""),
        "endorsed_at": datetime.utcnow().isoformat()
    }

    # Save endorsement
    await db.endorsements.insert_one(endorsement)

    return {
        "endorsement_id": endorsement["_id"],
        "status": "endorsed",
        "message": "Student endorsed successfully"
    }

@reviewer_router.get("/analytics")
async def get_reviewer_analytics(user=Depends(_current_user)):
    """Get reviewer analytics and insights"""
    db = get_database()

    # Check if user is a reviewer/employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") not in ["external_reviewer", "employer"]:
        raise HTTPException(403, "Reviewer/Employer access required")

    # Get analytics data
    analytics = {
        "total_reviews": 24,
        "interviews_conducted": 8,
        "students_endorsed": 15,
        "verifications_requested": 6,
        "average_rating_given": 4.2,
        "top_skills_reviewed": [
            {"skill": "Python", "count": 12},
            {"skill": "JavaScript", "count": 8},
            {"skill": "Data Analysis", "count": 6}
        ],
        "review_trends": {
            "this_month": 6,
            "last_month": 8,
            "two_months_ago": 10
        },
        "endorsement_impact": {
            "students_hired": 3,
            "students_interning": 5,
            "positive_outcomes": 8
        }
    }

    return analytics

@reviewer_router.post("/create-job-posting")
async def create_job_posting(job_data: dict, user=Depends(_current_user)):
    """Create a job posting for students"""
    db = get_database()

    # Check if user is an employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "employer":
        raise HTTPException(403, "Employer access required")

    # Create job posting
    job = {
        "_id": _uuid(),
        "employer_id": user["id"],
        "employer_name": user_doc.get("name", ""),
        "company": user_doc.get("company", ""),
        "title": job_data.get("title"),
        "description": job_data.get("description"),
        "requirements": job_data.get("requirements", []),
        "skills_required": job_data.get("skills_required", []),
        "location": job_data.get("location"),
        "job_type": job_data.get("job_type", "full_time"),
        "salary_range": job_data.get("salary_range"),
        "application_deadline": job_data.get("application_deadline"),
        "status": "active",
        "posted_at": datetime.utcnow().isoformat()
    }

    # Save job posting
    await db.job_postings.insert_one(job)

    return {
        "job_id": job["_id"],
        "status": "posted",
        "message": "Job posting created successfully"
    }

@reviewer_router.get("/job-postings")
async def get_job_postings(user=Depends(_current_user)):
    """Get job postings created by employer"""
    db = get_database()

    # Check if user is an employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "employer":
        raise HTTPException(403, "Employer access required")

    # Get job postings
    jobs = [
        {
            "_id": _uuid(),
            "title": "Junior Software Developer",
            "company": "Tech Innovations Inc.",
            "location": "Remote",
            "job_type": "full_time",
            "applications_count": 12,
            "status": "active",
            "posted_at": (datetime.utcnow() - timedelta(days=5)).isoformat()
        },
        {
            "_id": _uuid(),
            "title": "Data Analyst Intern",
            "company": "DataCorp Solutions",
            "location": "New York, NY",
            "job_type": "internship",
            "applications_count": 8,
            "status": "active",
            "posted_at": (datetime.utcnow() - timedelta(days=10)).isoformat()
        }
    ]

    return jobs

@reviewer_router.get("/applications/{job_id}")
async def get_job_applications(job_id: str, user=Depends(_current_user)):
    """Get applications for a specific job posting"""
    db = get_database()

    # Check if user is an employer
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "employer":
        raise HTTPException(403, "Employer access required")

    # Get job applications
    applications = [
        {
            "_id": _uuid(),
            "student_name": "Emma Johnson",
            "student_id": "student1",
            "applied_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
            "status": "under_review",
            "resume_score": 85,
            "skill_match": 90,
            "cover_letter": "I am excited to apply for the Junior Software Developer position..."
        },
        {
            "_id": _uuid(),
            "student_name": "Alex Johnson",
            "student_id": "student2",
            "applied_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
            "status": "shortlisted",
            "resume_score": 78,
            "skill_match": 82,
            "cover_letter": "I am interested in the Data Analyst Intern position..."
        }
    ]

    return applications