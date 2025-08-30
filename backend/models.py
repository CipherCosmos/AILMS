from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

def _uuid() -> str:
    return str(uuid.uuid4())

# Auth models
class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserBase(BaseModel):
    id: str = Field(default_factory=_uuid)
    email: EmailStr
    name: str
    role: str = Field(pattern=r"^(admin|instructor|student|auditor|career_coach|marketplace_manager|industry_reviewer|parent_guardian|alumni|proctor)$")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    password: Optional[str] = None
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

# Course models
class MediaAttachment(BaseModel):
    id: str = Field(default_factory=_uuid)
    filename: str
    file_type: str  # pdf, video, audio, image, document
    file_size: int
    url: str
    thumbnail_url: Optional[str] = None
    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}

class CourseLesson(BaseModel):
    id: str = Field(default_factory=_uuid)
    title: str
    content: str = ""
    content_type: str = "text"  # text, video, interactive, quiz
    resources: List[str] = []  # file_ids
    media_attachments: List[MediaAttachment] = []
    transcript_text: Optional[str] = None
    summary: Optional[str] = None
    estimated_time: int = 30  # minutes
    difficulty_level: str = "intermediate"
    learning_objectives: List[str] = []
    prerequisites: List[str] = []
    tags: List[str] = []
    is_published: bool = True
    order_index: int = 0

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

# Assignment models
class Assignment(BaseModel):
    id: str = Field(default_factory=_uuid)
    course_id: str
    title: str
    description: str = ""
    due_at: Optional[datetime] = None
    rubric: List[str] = []  # simple textual criteria
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AssignmentCreate(BaseModel):
    title: str
    description: str = ""
    due_at: Optional[datetime] = None
    rubric: List[str] = []

class Submission(BaseModel):
    id: str = Field(default_factory=_uuid)
    assignment_id: str
    user_id: str
    text_answer: Optional[str] = None
    file_ids: List[str] = []
    ai_grade: Optional[Dict[str, Any]] = None
    plagiarism: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SubmissionCreate(BaseModel):
    text_answer: Optional[str] = None
    file_ids: List[str] = []

class AIDescriptor(BaseModel):
    additional_instructions: Optional[str] = None

# Discussion models
class Thread(BaseModel):
    id: str = Field(default_factory=_uuid)
    course_id: str
    user_id: str
    title: str
    body: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ThreadCreate(BaseModel):
    title: str
    body: str

class Post(BaseModel):
    id: str = Field(default_factory=_uuid)
    thread_id: str
    user_id: str
    body: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PostCreate(BaseModel):
    body: str

# Chat models
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

# Other models
class LessonCreate(BaseModel):
    title: str
    content: str = ""

class QuizSubmitRequest(BaseModel):
    question_id: str
    selected_index: int

class TranscriptBody(BaseModel):
    text: str

# Progress models
class LessonProgress(BaseModel):
    lesson_id: str
    completed: bool = False
    completed_at: Optional[datetime] = None
    quiz_score: Optional[int] = None

class CourseProgress(BaseModel):
    course_id: str
    user_id: str
    lessons_progress: List[LessonProgress] = []
    overall_progress: float = 0.0  # percentage
    completed: bool = False
    completed_at: Optional[datetime] = None
    certificate_issued: bool = False

# Notification models
class Notification(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    title: str
    message: str
    type: str  # assignment, quiz, course, system
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Certificate model
class Certificate(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    course_id: str
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    certificate_data: Dict[str, Any]  # PDF data or URL
    blockchain_hash: Optional[str] = None  # For blockchain verification
    verification_url: Optional[str] = None

# Career and Skills Models
class Skill(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str
    category: str
    level: str = Field(pattern=r"^(beginner|intermediate|advanced|expert)$")
    description: str

class CareerGoal(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    title: str
    description: str
    target_skills: List[str]
    timeline_months: int
    current_progress: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SkillAssessment(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    skill_id: str
    current_level: str
    target_level: str
    assessment_date: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float

class CareerRecommendation(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    recommended_career: str
    match_score: float
    required_skills: List[str]
    suggested_courses: List[str]
    salary_range: Dict[str, Any]
    job_market_trend: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)

# Portfolio and Projects
class Project(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    title: str
    description: str
    technologies: List[str]
    github_url: Optional[str] = None
    live_url: Optional[str] = None
    images: List[str] = []
    skills_demonstrated: List[str]
    completion_date: datetime
    featured: bool = False

class Portfolio(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    title: str
    bio: str
    skills: List[str]
    projects: List[str]  # Project IDs
    experience: List[Dict[str, Any]]
    education: List[Dict[str, Any]]
    certifications: List[str]
    public: bool = False
    last_updated: datetime = Field(default_factory=datetime.utcnow)

# Practice and Labs
class CodeSandbox(BaseModel):
    id: str = Field(default_factory=_uuid)
    title: str
    language: str
    starter_code: str
    instructions: str
    test_cases: List[Dict[str, Any]]
    difficulty: str
    tags: List[str]

class MathProblem(BaseModel):
    id: str = Field(default_factory=_uuid)
    problem_text: str
    solution_steps: List[str]
    difficulty: str
    topic: str
    hints: List[str]

class LanguageExercise(BaseModel):
    id: str = Field(default_factory=_uuid)
    exercise_type: str  # vocabulary, grammar, pronunciation, writing
    content: str
    correct_answer: str
    difficulty: str
    audio_url: Optional[str] = None

# Interview and Career Tools
class InterviewQuestion(BaseModel):
    id: str = Field(default_factory=_uuid)
    question: str
    category: str  # technical, behavioral, situational
    difficulty: str
    sample_answer: str
    keywords: List[str]

class ResumeTemplate(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str
    template_data: Dict[str, Any]
    category: str
    preview_image: str

# Financial Aid and Scholarships
class Scholarship(BaseModel):
    id: str = Field(default_factory=_uuid)
    title: str
    description: str
    amount: float
    deadline: datetime
    eligibility_criteria: Dict[str, Any]
    application_url: str
    sponsor: str

class FinancialAidApplication(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    scholarship_id: str
    application_data: Dict[str, Any]
    status: str = "draft"  # draft, submitted, approved, rejected
    submitted_at: Optional[datetime] = None

# AI Governance and Ethics
class AIInteraction(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    interaction_type: str  # recommendation, tutoring, assessment, etc.
    prompt: str
    response: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    consent_given: bool = True
    feedback_provided: Optional[str] = None

class BiasReport(BaseModel):
    id: str = Field(default_factory=_uuid)
    content_type: str  # course, assessment, recommendation
    content_id: str
    bias_type: str
    severity_score: float
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    mitigation_suggestion: str
    status: str = "pending"  # pending, reviewed, mitigated



# Profile Management Models
class UserProfile(BaseModel):
    user_id: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    social_links: Dict[str, str] = {}  # {"linkedin": "url", "github": "url", etc.}
    skills: List[str] = []
    interests: List[str] = []
    learning_goals: List[str] = []
    preferred_learning_style: Optional[str] = None  # visual, auditory, kinesthetic, reading
    timezone: Optional[str] = None
    language: str = "en"
    notifications_enabled: bool = True
    privacy_settings: Dict[str, bool] = {
        "show_profile": True,
        "show_progress": True,
        "show_achievements": True,
        "allow_messages": True
    }
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Achievement(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    type: str  # course_completion, streak, high_score, etc.
    title: str
    description: str
    icon: str
    points: int = 0
    metadata: Dict[str, Any] = {}
    earned_at: datetime = Field(default_factory=datetime.utcnow)


class LearningStreak(BaseModel):
    user_id: str
    current_streak: int = 0
    longest_streak: int = 0
    last_activity_date: Optional[datetime] = None
    streak_start_date: Optional[datetime] = None
    total_study_days: int = 0
    weekly_goal: int = 7  # days per week
    monthly_goal: int = 30  # days per month


class UserPreferences(BaseModel):
    user_id: str
    theme: str = "light"  # light, dark, auto
    email_notifications: Dict[str, bool] = {
        "course_updates": True,
        "assignment_deadlines": True,
        "new_messages": True,
        "weekly_progress": True,
        "achievement_unlocks": True
    }
    study_reminders: bool = True
    reminder_time: str = "09:00"  # HH:MM format
    dashboard_layout: str = "default"
    quick_actions: List[str] = ["continue_course", "view_progress", "check_assignments"]
    accessibility: Dict[str, Any] = {
        "font_size": "medium",
        "high_contrast": False,
        "reduced_motion": False
    }


# Advanced RBAC Models
class Permission(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str  # e.g., "courses:create", "assignments:grade"
    description: str
    resource_type: str  # courses, assignments, users, analytics, etc.
    action: str  # create, read, update, delete, grade, manage, etc.
    scope: str = "global"  # global, tenant, department, course, self


class Role(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str  # super_admin, org_admin, dept_admin, instructor, ta, student, parent, etc.
    display_name: str
    description: str
    tenant_id: Optional[str] = None  # null for global roles
    permissions: List[str] = []  # permission IDs
    is_system_role: bool = False  # cannot be deleted
    hierarchy_level: int = 0  # for role comparison
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Tenant(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str
    domain: Optional[str] = None
    subdomain: Optional[str] = None
    branding: Dict[str, Any] = {
        "logo_url": None,
        "primary_color": "#667eea",
        "secondary_color": "#764ba2",
        "custom_css": None
    }
    settings: Dict[str, Any] = {
        "max_users": 1000,
        "storage_limit_gb": 100,
        "ai_enabled": True,
        "marketplace_enabled": False,
        "sso_enabled": False
    }
    plan: str = "basic"  # basic, pro, enterprise
    status: str = "active"  # active, suspended, trial
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserRole(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    role_id: str
    tenant_id: Optional[str] = None
    scope_id: Optional[str] = None  # department, course, etc.
    scope_type: Optional[str] = None  # department, course, section
    assigned_by: str
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


# Advanced User Types
class StudentProfile(BaseModel):
    user_id: str
    student_id: Optional[str] = None
    grade_level: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[float] = None
    major: Optional[str] = None
    minor: Optional[str] = None
    advisor_id: Optional[str] = None
    guardian_ids: List[str] = []
    accommodations: List[str] = []
    emergency_contact: Dict[str, str] = {}
    enrollment_status: str = "active"  # active, inactive, graduated, withdrawn


class InstructorProfile(BaseModel):
    user_id: str
    employee_id: Optional[str] = None
    department: Optional[str] = None
    title: str = "Instructor"
    office_hours: List[Dict[str, Any]] = []
    research_interests: List[str] = []
    publications: List[str] = []
    certifications: List[str] = []
    teaching_load: int = 0  # courses per semester
    tenure_status: Optional[str] = None


class ParentGuardian(BaseModel):
    user_id: str
    relationship_type: str  # mother, father, guardian, etc.
    student_ids: List[str] = []
    contact_preferences: Dict[str, bool] = {
        "email": True,
        "sms": False,
        "push": True
    }
    emergency_contact: bool = False
    legal_guardian: bool = True


# Department/Organization Structure
class Department(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    name: str
    code: str
    parent_id: Optional[str] = None  # for hierarchical departments
    head_id: Optional[str] = None  # department head user ID
    description: Optional[str] = None
    settings: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CourseSection(BaseModel):
    id: str = Field(default_factory=_uuid)
    course_id: str
    section_number: str
    instructor_id: str
    schedule: Dict[str, Any] = {}  # days, times, location
    capacity: int = 30
    enrolled_count: int = 0
    waitlist_count: int = 0
    settings: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Advanced Assessment Models
class QuestionBank(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    name: str
    description: Optional[str] = None
    subject: str
    grade_level: Optional[str] = None
    tags: List[str] = []
    created_by: str
    is_public: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QuestionItem(BaseModel):
    id: str = Field(default_factory=_uuid)
    bank_id: str
    type: str  # multiple_choice, true_false, short_answer, essay, code, formula, etc.
    difficulty: str = "medium"  # easy, medium, hard
    points: float = 1.0
    question_text: str
    question_data: Dict[str, Any] = {}  # choices, correct_answer, hints, etc.
    explanation: Optional[str] = None
    tags: List[str] = []
    learning_objectives: List[str] = []
    created_by: str
    ai_generated: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QuizTemplate(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    name: str
    description: Optional[str] = None
    settings: Dict[str, Any] = {
        "time_limit": None,
        "attempts_allowed": 1,
        "shuffle_questions": False,
        "shuffle_answers": False,
        "show_results": True,
        "show_correct_answers": False
    }
    question_pools: List[Dict[str, Any]] = []  # pool_id, count, points
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Career and Professional Development
class CareerProfile(BaseModel):
    user_id: str
    career_goals: List[str] = []
    target_industries: List[str] = []
    target_roles: List[str] = []
    skills_to_develop: List[str] = []
    resume_data: Dict[str, Any] = {}
    linkedin_profile: Optional[str] = None
    portfolio_url: Optional[str] = None
    mentor_ids: List[str] = []
    mentee_ids: List[str] = []


class JobPosting(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    title: str
    company: str
    description: str
    requirements: List[str] = []
    skills_required: List[str] = []
    location: str
    salary_range: Optional[str] = None
    job_type: str = "full_time"  # full_time, part_time, internship, contract
    posted_by: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InternshipProject(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    title: str
    company: str
    description: str
    skills_developed: List[str] = []
    duration_weeks: int
    compensation: Optional[str] = None
    remote_allowed: bool = True
    posted_by: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Well-being and Mental Health
class WellBeingProfile(BaseModel):
    user_id: str
    stress_level: int = 5  # 1-10 scale
    sleep_hours: Optional[float] = None
    exercise_frequency: str = "rarely"  # daily, weekly, rarely, never
    study_hours_per_week: Optional[int] = None
    social_connections: int = 5  # 1-10 scale
    last_check_in: Optional[datetime] = None
    support_resources_used: List[str] = []
    goals: List[str] = []


class WellBeingResource(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    title: str
    type: str  # article, video, tool, contact
    category: str  # stress, sleep, motivation, etc.
    content: str
    url: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Gamification and Achievements
class Badge(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    name: str
    description: str
    icon_url: str
    category: str  # academic, social, skill, participation
    criteria: Dict[str, Any] = {}
    points_value: int = 0
    rarity: str = "common"  # common, rare, epic, legendary
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserBadge(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    badge_id: str
    earned_at: datetime = Field(default_factory=datetime.utcnow)
    earned_reason: str


class Leaderboard(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    name: str
    type: str  # points, streak, completion, social
    scope: str  # global, department, course
    period: str  # all_time, monthly, weekly, daily
    entries: List[Dict[str, Any]] = []
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# Marketplace and Monetization
class CourseMarketplace(BaseModel):
    id: str = Field(default_factory=_uuid)
    course_id: str
    seller_tenant_id: str
    price: float
    currency: str = "USD"
    license_type: str = "single_use"  # single_use, multi_use, unlimited
    description: str
    tags: List[str] = []
    rating: float = 0.0
    review_count: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CoursePurchase(BaseModel):
    id: str = Field(default_factory=_uuid)
    buyer_tenant_id: str
    marketplace_id: str
    purchase_price: float
    license_key: str
    purchased_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


# Blockchain Credentials
class BlockchainCredential(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    credential_type: str  # certificate, badge, diploma
    credential_id: str
    issuer_did: str
    subject_did: str
    issuance_date: datetime
    expiration_date: Optional[datetime] = None
    credential_data: Dict[str, Any]
    blockchain_tx_hash: Optional[str] = None
    verification_url: str
    status: str = "active"  # active, revoked, expired


# Proctoring and Academic Integrity
class ProctoringSession(BaseModel):
    id: str = Field(default_factory=_uuid)
    quiz_attempt_id: str
    proctor_id: str
    session_start: datetime
    session_end: Optional[datetime] = None
    status: str = "active"  # active, completed, terminated
    incidents: List[Dict[str, Any]] = []
    recordings: List[str] = []  # file IDs
    ai_monitoring_enabled: bool = True
    behavioral_flags: List[str] = []


class AcademicIntegrityReport(BaseModel):
    id: str = Field(default_factory=_uuid)
    submission_id: str
    report_type: str  # plagiarism, ai_generated, collusion
    vendor: str  # turnitin, originality_ai, etc.
    score: float  # similarity percentage
    matches: List[Dict[str, Any]] = []
    ai_probability: Optional[float] = None
    flagged_content: List[str] = []
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    status: str = "pending"  # pending, reviewed, dismissed


# Advanced Analytics
class AnalyticsEvent(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    user_id: str
    event_type: str
    event_data: Dict[str, Any]
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PredictiveModel(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    model_type: str  # completion_prediction, at_risk_detection, grade_prediction
    model_data: Dict[str, Any]
    accuracy_score: float
    last_trained: datetime
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Integration Models
class LTIIntegration(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    tool_name: str
    tool_url: str
    consumer_key: str
    shared_secret: str
    lti_version: str = "1.3"
    custom_parameters: Dict[str, str] = {}
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SSOConfiguration(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    provider: str  # saml, oidc, google, microsoft
    configuration: Dict[str, Any]
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Course Content Models for Comprehensive LMS
class CourseContent(BaseModel):
    id: str = Field(default_factory=_uuid)
    course_id: str
    title: str
    description: str
    modules: List[Dict[str, Any]] = []
    assessment_types: List[Dict[str, Any]] = []
    certification: Dict[str, Any] = {}
    gamification_elements: Dict[str, Any] = {}
    adaptive_features: Dict[str, Any] = {}
    collaboration_features: Dict[str, Any] = {}
    analytics_and_reporting: Dict[str, Any] = {}
    accessibility_features: Dict[str, Any] = {}
    integration_capabilities: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ModuleProgress(BaseModel):
    module_id: str
    completed: bool = False
    progress_percentage: float = 0.0
    time_spent: int = 0  # minutes
    completed_at: Optional[datetime] = None
    quiz_scores: Dict[str, float] = {}
    assessment_results: Dict[str, Any] = {}

class StudentCourseProgress(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    course_id: str
    overall_progress: float = 0.0
    modules_progress: List[ModuleProgress] = []
    current_module: str = ""
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    completed: bool = False
    completed_at: Optional[datetime] = None
    certificate_issued: bool = False
    gamification_data: Dict[str, Any] = {}
    adaptive_settings: Dict[str, Any] = {}

class QuizAttempt(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    course_id: str
    module_id: str
    quiz_id: str
    answers: Dict[str, Any] = {}
    score: float = 0.0
    max_score: float = 0.0
    time_taken: int = 0  # seconds
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    feedback: Dict[str, Any] = {}

class DiscussionThread(BaseModel):
    id: str = Field(default_factory=_uuid)
    course_id: str
    module_id: str
    user_id: str
    title: str
    content: str
    tags: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    views: int = 0
    likes: int = 0
    replies_count: int = 0
    is_pinned: bool = False
    is_locked: bool = False

class DiscussionReply(BaseModel):
    id: str = Field(default_factory=_uuid)
    thread_id: str
    user_id: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    likes: int = 0
    is_instructor_reply: bool = False

class GamificationData(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    course_id: str
    total_points: int = 0
    badges_earned: List[str] = []
    streak_days: int = 0
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    achievements: Dict[str, Any] = {}
    leaderboard_position: int = 0

class AdaptiveLearningProfile(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    course_id: str
    learning_style: str = "visual"  # visual, auditory, kinesthetic, reading
    preferred_pace: str = "moderate"  # slow, moderate, fast
    difficulty_preference: str = "adaptive"
    content_preferences: Dict[str, Any] = {}
    performance_history: List[Dict[str, Any]] = []
    recommended_adjustments: Dict[str, Any] = {}
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Course Reviews and Ratings
class CourseReview(BaseModel):
    id: str = Field(default_factory=_uuid)
    course_id: str
    user_id: str
    rating: int = Field(ge=1, le=5)
    title: str
    content: str
    pros: List[str] = []
    cons: List[str] = []
    helpful_votes: int = 0
    is_verified_purchase: bool = False
    is_instructor_response: bool = False
    instructor_response: Optional[str] = None
    response_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ReviewVote(BaseModel):
    id: str = Field(default_factory=_uuid)
    review_id: str
    user_id: str
    vote_type: str  # helpful, not_helpful
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Enhanced Discussion/Q&A System
class CourseDiscussion(BaseModel):
    id: str = Field(default_factory=_uuid)
    course_id: str
    lesson_id: Optional[str] = None
    user_id: str
    title: str
    content: str
    discussion_type: str = "question"  # question, discussion, announcement, clarification
    tags: List[str] = []
    is_pinned: bool = False
    is_locked: bool = False
    is_featured: bool = False
    view_count: int = 0
    upvote_count: int = 0
    reply_count: int = 0
    last_reply_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class DiscussionPost(BaseModel):
    id: str = Field(default_factory=_uuid)
    discussion_id: str
    user_id: str
    content: str
    is_instructor_reply: bool = False
    is_solution: bool = False
    upvote_count: int = 0
    parent_reply_id: Optional[str] = None  # for nested replies
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class DiscussionVote(BaseModel):
    id: str = Field(default_factory=_uuid)
    discussion_id: Optional[str] = None
    reply_id: Optional[str] = None
    user_id: str
    vote_type: str  # upvote, downvote
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Enhanced Analytics Models
class CourseAnalytics(BaseModel):
    course_id: str
    total_enrollments: int = 0
    active_students: int = 0
    completion_rate: float = 0.0
    average_rating: float = 0.0
    total_reviews: int = 0
    discussion_count: int = 0
    average_time_spent: float = 0.0  # minutes
    popular_lessons: List[Dict[str, Any]] = []
    student_demographics: Dict[str, Any] = {}
    engagement_metrics: Dict[str, Any] = {}
    performance_trends: List[Dict[str, Any]] = []
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class StudentAnalytics(BaseModel):
    user_id: str
    course_id: str
    lessons_completed: int = 0
    total_time_spent: int = 0  # minutes
    quiz_scores: List[Dict[str, Any]] = []
    discussion_participation: int = 0
    last_activity: Optional[datetime] = None
    progress_percentage: float = 0.0
    predicted_completion_date: Optional[datetime] = None
    learning_pattern: str = ""
    strengths: List[str] = []
    areas_for_improvement: List[str] = []
    personalized_recommendations: List[str] = []


# Media Management
class MediaLibrary(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    media_type: str  # image, video, audio, document, pdf
    file_path: str
    file_size: int
    mime_type: str
    thumbnail_path: Optional[str] = None
    tags: List[str] = []
    uploaded_by: str
    is_public: bool = False
    usage_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# AI Content Generation
class ContentGenerationRequest(BaseModel):
    content_type: str  # lesson, quiz, assignment, explanation
    topic: str
    target_audience: str
    difficulty_level: str
    length_requirements: Optional[str] = None
    specific_instructions: Optional[str] = None
    include_examples: bool = True
    include_assessment: bool = False

class GeneratedContent(BaseModel):
    id: str = Field(default_factory=_uuid)
    request_id: str
    content_type: str
    generated_content: str
    metadata: Dict[str, Any] = {}
    quality_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)