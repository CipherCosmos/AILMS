// MongoDB Initialization Script for LMS
// This script runs when the MongoDB container starts for the first time

// Switch to the LMS database
db = db.getSiblingDB('lms_prod');

// Create collections with indexes
db.createCollection('users');
db.createCollection('courses');
db.createCollection('course_progress');
db.createCollection('assignments');
db.createCollection('submissions');
db.createCollection('notifications');
db.createCollection('certificates');
db.createCollection('chats');
db.createCollection('discussions');
db.createCollection('user_profiles');
db.createCollection('user_preferences');
db.createCollection('analytics_events');
db.createCollection('ai_interactions');
db.createCollection('marketplace_listings');
db.createCollection('financial_aid_applications');
db.createCollection('scholarships');
db.createCollection('job_postings');
db.createCollection('internship_projects');
db.createCollection('wellbeing_resources');
db.createCollection('badges');
db.createCollection('user_badges');
db.createCollection('leaderboards');
db.createCollection('blockchain_credentials');
db.createCollection('proctoring_sessions');
db.createCollection('academic_integrity_reports');
db.createCollection('lti_integrations');
db.createCollection('sso_configurations');
db.createCollection('media_library');
db.createCollection('content_generation_requests');
db.createCollection('generated_content');
db.createCollection('career_profiles');
db.createCollection('skill_assessments');
db.createCollection('career_recommendations');
db.createCollection('projects');
db.createCollection('portfolios');
db.createCollection('code_sandboxes');
db.createCollection('math_problems');
db.createCollection('language_exercises');
db.createCollection('interview_questions');
db.createCollection('resume_templates');
db.createCollection('learning_streaks');
db.createCollection('achievement_definitions');
db.createCollection('user_achievements');
db.createCollection('course_reviews');
db.createCollection('review_votes');
db.createCollection('course_discussions');
db.createCollection('discussion_posts');
db.createCollection('discussion_votes');
db.createCollection('course_analytics');
db.createCollection('student_analytics');
db.createCollection('permission_definitions');
db.createCollection('roles');
db.createCollection('user_roles');
db.createCollection('tenants');
db.createCollection('departments');
db.createCollection('course_sections');
db.createCollection('question_banks');
db.createCollection('question_items');
db.createCollection('quiz_templates');
db.createCollection('student_profiles');
db.createCollection('instructor_profiles');
db.createCollection('parent_guardians');

// Create indexes for better performance

// Users collection indexes
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "role": 1 });
db.users.createIndex({ "created_at": -1 });

// Courses collection indexes
db.courses.createIndex({ "owner_id": 1 });
db.courses.createIndex({ "published": 1 });
db.courses.createIndex({ "enrolled_user_ids": 1 });
db.courses.createIndex({ "created_at": -1 });
db.courses.createIndex({ "title": "text", "description": "text" });

// Course progress indexes
db.course_progress.createIndex({ "user_id": 1, "course_id": 1 }, { unique: true });
db.course_progress.createIndex({ "user_id": 1 });
db.course_progress.createIndex({ "course_id": 1 });
db.course_progress.createIndex({ "completed": 1 });

// Assignments indexes
db.assignments.createIndex({ "course_id": 1 });
db.assignments.createIndex({ "due_at": 1 });

// Submissions indexes
db.submissions.createIndex({ "assignment_id": 1 });
db.submissions.createIndex({ "user_id": 1 });
db.submissions.createIndex({ "created_at": -1 });

// Notifications indexes
db.notifications.createIndex({ "user_id": 1 });
db.notifications.createIndex({ "read": 1 });
db.notifications.createIndex({ "created_at": -1 });

// Chat indexes
db.chats.createIndex({ "session_id": 1 });
db.chats.createIndex({ "user_id": 1 });
db.chats.createIndex({ "created_at": -1 });

// Analytics indexes
db.analytics_events.createIndex({ "user_id": 1 });
db.analytics_events.createIndex({ "event_type": 1 });
db.analytics_events.createIndex({ "timestamp": -1 });
db.analytics_events.createIndex({ "tenant_id": 1 });

// AI interactions indexes
db.ai_interactions.createIndex({ "user_id": 1 });
db.ai_interactions.createIndex({ "interaction_type": 1 });
db.ai_interactions.createIndex({ "timestamp": -1 });

// File storage indexes
db.media_library.createIndex({ "uploaded_by": 1 });
db.media_library.createIndex({ "file_type": 1 });
db.media_library.createIndex({ "tags": 1 });

// Reviews and ratings indexes
db.course_reviews.createIndex({ "course_id": 1 });
db.course_reviews.createIndex({ "user_id": 1 });
db.course_reviews.createIndex({ "rating": 1 });
db.course_reviews.createIndex({ "helpful_votes": -1 });

// Discussions indexes
db.course_discussions.createIndex({ "course_id": 1 });
db.course_discussions.createIndex({ "user_id": 1 });
db.course_discussions.createIndex({ "created_at": -1 });
db.course_discussions.createIndex({ "tags": 1 });

// Gamification indexes
db.user_badges.createIndex({ "user_id": 1 });
db.user_badges.createIndex({ "badge_id": 1 });
db.leaderboards.createIndex({ "scope": 1 });
db.leaderboards.createIndex({ "period": 1 });

// Career and skills indexes
db.career_profiles.createIndex({ "user_id": 1 });
db.skill_assessments.createIndex({ "user_id": 1 });
db.skill_assessments.createIndex({ "skill_id": 1 });

// Projects and portfolios indexes
db.projects.createIndex({ "user_id": 1 });
db.projects.createIndex({ "technologies": 1 });
db.projects.createIndex({ "skills_demonstrated": 1 });
db.portfolios.createIndex({ "user_id": 1 });

// Academic integrity indexes
db.academic_integrity_reports.createIndex({ "submission_id": 1 });
db.academic_integrity_reports.createIndex({ "status": 1 });

// Proctoring indexes
db.proctoring_sessions.createIndex({ "quiz_attempt_id": 1 });
db.proctoring_sessions.createIndex({ "proctor_id": 1 });
db.proctoring_sessions.createIndex({ "status": 1 });

// Blockchain credentials indexes
db.blockchain_credentials.createIndex({ "user_id": 1 });
db.blockchain_credentials.createIndex({ "credential_type": 1 });

// Marketplace indexes
db.marketplace_listings.createIndex({ "seller_tenant_id": 1 });
db.marketplace_listings.createIndex({ "is_active": 1 });
db.marketplace_listings.createIndex({ "price": 1 });

// Job postings indexes
db.job_postings.createIndex({ "posted_by": 1 });
db.job_postings.createIndex({ "is_active": 1 });
db.job_postings.createIndex({ "skills_required": 1 });

// Wellbeing indexes
db.wellbeing_resources.createIndex({ "category": 1 });
db.wellbeing_resources.createIndex({ "is_active": 1 });

// Compound indexes for complex queries
db.courses.createIndex({ "published": 1, "enrolled_user_ids": 1 });
db.courses.createIndex({ "owner_id": 1, "published": 1 });
db.submissions.createIndex({ "user_id": 1, "assignment_id": 1 });
db.notifications.createIndex({ "user_id": 1, "read": 1, "created_at": -1 });

// Text indexes for search functionality
db.courses.createIndex({
    "title": "text",
    "description": "text",
    "audience": "text",
    "difficulty": "text"
});

db.users.createIndex({
    "name": "text",
    "email": "text"
});

db.assignments.createIndex({
    "title": "text",
    "description": "text"
});

// Create admin user (for initial setup)
db.users.insertOne({
    "_id": "admin_user",
    "email": "admin@lms.com",
    "name": "System Administrator",
    "role": "super_admin",
    "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6fYzYXxQK", // "admin123"
    "created_at": new Date().toISOString(),
    "is_active": true,
    "email_verified": true
});

// Create sample tenant
db.tenants.insertOne({
    "_id": "default_tenant",
    "name": "Default Organization",
    "domain": null,
    "settings": {
        "max_users": 1000,
        "storage_limit_gb": 100,
        "ai_enabled": true,
        "marketplace_enabled": true
    },
    "plan": "enterprise",
    "status": "active",
    "created_at": new Date().toISOString()
});

// Create default roles
db.roles.insertMany([
    {
        "_id": "super_admin",
        "name": "super_admin",
        "display_name": "Super Administrator",
        "description": "Full system access",
        "permissions": ["*"],
        "is_system_role": true,
        "hierarchy_level": 100
    },
    {
        "_id": "org_admin",
        "name": "org_admin",
        "display_name": "Organization Administrator",
        "description": "Organization-level administration",
        "permissions": ["users:*", "courses:*", "analytics:read"],
        "is_system_role": true,
        "hierarchy_level": 80
    },
    {
        "_id": "instructor",
        "name": "instructor",
        "display_name": "Instructor",
        "description": "Can create and manage courses",
        "permissions": ["courses:*", "assignments:*", "analytics:read"],
        "is_system_role": true,
        "hierarchy_level": 60
    },
    {
        "_id": "student",
        "name": "student",
        "display_name": "Student",
        "description": "Can access enrolled courses",
        "permissions": ["courses:read", "assignments:submit", "profile:*"],
        "is_system_role": true,
        "hierarchy_level": 10
    }
]);

print("✅ LMS Database initialized successfully!");
print("📊 Created collections and indexes");
print("👤 Created default admin user: admin@lms.com / admin123");
print("🏢 Created default tenant and roles");