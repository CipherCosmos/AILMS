"""
Database seeding script for comprehensive testing.
Creates realistic test data for all LMS features.
"""
import asyncio
import json
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.hash import bcrypt
from config import settings
import uuid

async def seed_database():
    """Seed the database with comprehensive test data."""

    # Connect to database
    client = AsyncIOMotorClient(settings.mongo_url)
    db = client[settings.db_name]

    print("Seeding database with test data...")

    # Clear existing data
    await client.drop_database(settings.db_name)
    print("Cleared existing database")

    # Create users
    users = await create_users(db)
    print(f"Created {len(users)} users")

    # Create courses
    courses = await create_courses(db, users)
    print(f"Created {len(courses)} courses")

    # Create assignments
    assignments = await create_assignments(db, courses)
    print(f"Created {len(assignments)} assignments")

    # Create submissions
    submissions = await create_submissions(db, assignments, users)
    print(f"Created {len(submissions)} submissions")

    # Create progress data
    progress_data = await create_progress_data(db, courses, users)
    print(f"Created progress data for {len(progress_data)} user-course combinations")

    # Create discussions
    discussions = await create_discussions(db, courses, users)
    print(f"Created {len(discussions)} discussions")

    # Create notifications
    notifications = await create_notifications(db, users)
    print(f"Created {len(notifications)} notifications")

    # Create analytics data
    analytics = await create_analytics_data(db, courses, users)
    print(f"Created analytics data")

    print("Database seeding completed successfully!")
    print(f"📊 Summary:")
    print(f"   - Users: {len(users)}")
    print(f"   - Courses: {len(courses)}")
    print(f"   - Assignments: {len(assignments)}")
    print(f"   - Submissions: {len(submissions)}")
    print(f"   - Discussions: {len(discussions)}")
    print(f"   - Notifications: {len(notifications)}")

    client.close()

async def create_users(db):
    """Create diverse user accounts."""
    users_data = [
        {
            "_id": "admin_001",
            "email": "admin@lms.com",
            "name": "System Administrator",
            "role": "admin",
            "password_hash": bcrypt.hash("admin123"),
            "created_at": datetime.utcnow() - timedelta(days=365),
            "last_login": datetime.utcnow() - timedelta(hours=1)
        },
        {
            "_id": "instructor_001",
            "email": "john.doe@university.edu",
            "name": "Dr. John Doe",
            "role": "instructor",
            "password_hash": bcrypt.hash("password"),
            "created_at": datetime.utcnow() - timedelta(days=200),
            "last_login": datetime.utcnow() - timedelta(hours=2),
            "department": "Computer Science",
            "specialization": "Machine Learning"
        },
        {
            "_id": "instructor_002",
            "email": "jane.smith@university.edu",
            "name": "Prof. Jane Smith",
            "role": "instructor",
            "password_hash": bcrypt.hash("password"),
            "created_at": datetime.utcnow() - timedelta(days=180),
            "last_login": datetime.utcnow() - timedelta(hours=5),
            "department": "Data Science",
            "specialization": "Statistics"
        },
        {
            "_id": "student_001",
            "email": "alice.johnson@student.edu",
            "name": "Alice Johnson",
            "role": "student",
            "password_hash": bcrypt.hash("password"),
            "created_at": datetime.utcnow() - timedelta(days=100),
            "last_login": datetime.utcnow() - timedelta(hours=3),
            "student_id": "STU2024001",
            "major": "Computer Science",
            "year": "Junior"
        },
        {
            "_id": "student_002",
            "email": "bob.wilson@student.edu",
            "name": "Bob Wilson",
            "role": "student",
            "password_hash": bcrypt.hash("password"),
            "created_at": datetime.utcnow() - timedelta(days=90),
            "last_login": datetime.utcnow() - timedelta(hours=1),
            "student_id": "STU2024002",
            "major": "Data Science",
            "year": "Sophomore"
        },
        {
            "_id": "student_003",
            "email": "carol.brown@student.edu",
            "name": "Carol Brown",
            "role": "student",
            "password_hash": bcrypt.hash("password"),
            "created_at": datetime.utcnow() - timedelta(days=80),
            "last_login": datetime.utcnow() - timedelta(hours=6),
            "student_id": "STU2024003",
            "major": "Information Technology",
            "year": "Senior"
        },
        {
            "_id": "parent_001",
            "email": "david.johnson@parent.com",
            "name": "David Johnson",
            "role": "parent",
            "password_hash": bcrypt.hash("password"),
            "created_at": datetime.utcnow() - timedelta(days=50),
            "last_login": datetime.utcnow() - timedelta(hours=12),
            "children": ["student_001"]
        }
    ]

    await db.users.insert_many(users_data)
    return users_data

async def create_courses(db, users):
    """Create comprehensive courses with lessons and quizzes."""
    courses_data = [
        {
            "_id": "course_ai_ml_001",
            "owner_id": "instructor_001",
            "title": "Introduction to Artificial Intelligence and Machine Learning",
            "audience": "Undergraduate Students",
            "difficulty": "intermediate",
            "description": "Comprehensive course covering AI fundamentals, machine learning algorithms, and practical applications.",
            "lessons": [
                {
                    "id": "lesson_1",
                    "title": "What is Artificial Intelligence?",
                    "content": "Introduction to AI concepts, history, and current applications in various industries.",
                    "order_index": 0,
                    "estimated_time": 45,
                    "learning_objectives": ["Define AI", "Understand AI history", "Identify AI applications"]
                },
                {
                    "id": "lesson_2",
                    "title": "Machine Learning Fundamentals",
                    "content": "Core concepts of machine learning including supervised and unsupervised learning.",
                    "order_index": 1,
                    "estimated_time": 60,
                    "learning_objectives": ["Explain ML types", "Understand training data", "Describe model evaluation"]
                },
                {
                    "id": "lesson_3",
                    "title": "Neural Networks and Deep Learning",
                    "content": "Introduction to neural networks, backpropagation, and deep learning architectures.",
                    "order_index": 2,
                    "estimated_time": 75,
                    "learning_objectives": ["Explain neural networks", "Understand backpropagation", "Describe CNNs and RNNs"]
                }
            ],
            "quiz": [
                {
                    "id": "quiz_1",
                    "question": "Which of the following is NOT a type of machine learning?",
                    "options": [
                        {"text": "Supervised Learning", "is_correct": False},
                        {"text": "Unsupervised Learning", "is_correct": False},
                        {"text": "Reinforcement Learning", "is_correct": False},
                        {"text": "Quantum Learning", "is_correct": True}
                    ],
                    "explanation": "Quantum Learning is not a standard type of machine learning."
                },
                {
                    "id": "quiz_2",
                    "question": "What is the purpose of backpropagation in neural networks?",
                    "options": [
                        {"text": "To initialize weights", "is_correct": False},
                        {"text": "To calculate the loss function", "is_correct": False},
                        {"text": "To update weights based on error", "is_correct": True},
                        {"text": "To normalize input data", "is_correct": False}
                    ],
                    "explanation": "Backpropagation calculates gradients and updates weights to minimize error."
                }
            ],
            "published": True,
            "enrolled_user_ids": ["student_001", "student_002", "student_003"],
            "created_at": datetime.utcnow() - timedelta(days=150),
            "tags": ["AI", "Machine Learning", "Computer Science"],
            "prerequisites": [],
            "learning_outcomes": [
                "Understand AI fundamentals",
                "Implement basic ML algorithms",
                "Apply AI to real-world problems"
            ]
        },
        {
            "_id": "course_data_science_001",
            "owner_id": "instructor_002",
            "title": "Data Science and Analytics",
            "audience": "Undergraduate Students",
            "difficulty": "intermediate",
            "description": "Learn data analysis, visualization, and statistical methods for data-driven decision making.",
            "lessons": [
                {
                    "id": "lesson_1",
                    "title": "Data Collection and Cleaning",
                    "content": "Methods for gathering data and handling missing values, outliers, and data quality issues.",
                    "order_index": 0,
                    "estimated_time": 50
                },
                {
                    "id": "lesson_2",
                    "title": "Exploratory Data Analysis",
                    "content": "Techniques for understanding data distributions, correlations, and patterns.",
                    "order_index": 1,
                    "estimated_time": 55
                }
            ],
            "quiz": [
                {
                    "id": "quiz_1",
                    "question": "What is the first step in any data science project?",
                    "options": [
                        {"text": "Model building", "is_correct": False},
                        {"text": "Data collection", "is_correct": True},
                        {"text": "Visualization", "is_correct": False},
                        {"text": "Deployment", "is_correct": False}
                    ],
                    "explanation": "Data collection is the foundation of any data science project."
                }
            ],
            "published": True,
            "enrolled_user_ids": ["student_001", "student_002"],
            "created_at": datetime.utcnow() - timedelta(days=120),
            "tags": ["Data Science", "Analytics", "Statistics"]
        },
        {
            "_id": "course_web_dev_001",
            "owner_id": "instructor_001",
            "title": "Full-Stack Web Development",
            "audience": "Beginner to Intermediate Developers",
            "difficulty": "beginner",
            "description": "Complete guide to modern web development using React, Node.js, and cloud technologies.",
            "lessons": [
                {
                    "id": "lesson_1",
                    "title": "HTML and CSS Fundamentals",
                    "content": "Building blocks of web development: HTML structure and CSS styling.",
                    "order_index": 0,
                    "estimated_time": 40
                },
                {
                    "id": "lesson_2",
                    "title": "JavaScript Essentials",
                    "content": "Core JavaScript concepts including variables, functions, and DOM manipulation.",
                    "order_index": 1,
                    "estimated_time": 60
                }
            ],
            "quiz": [
                {
                    "id": "quiz_1",
                    "question": "What does HTML stand for?",
                    "options": [
                        {"text": "HyperText Markup Language", "is_correct": True},
                        {"text": "High Tech Modern Language", "is_correct": False},
                        {"text": "Home Tool Markup Language", "is_correct": False},
                        {"text": "Hyperlink and Text Markup Language", "is_correct": False}
                    ],
                    "explanation": "HTML stands for HyperText Markup Language."
                }
            ],
            "published": True,
            "enrolled_user_ids": ["student_003"],
            "created_at": datetime.utcnow() - timedelta(days=90),
            "tags": ["Web Development", "JavaScript", "React"]
        }
    ]

    await db.courses.insert_many(courses_data)
    return courses_data

async def create_assignments(db, courses):
    """Create assignments for courses."""
    assignments_data = [
        {
            "_id": "assignment_001",
            "course_id": "course_ai_ml_001",
            "title": "AI Ethics Case Study Analysis",
            "description": "Analyze a real-world AI ethics case study and discuss the implications.",
            "due_at": datetime.utcnow() + timedelta(days=7),
            "rubric": [
                "Understanding of ethical issues (25%)",
                "Analysis depth (25%)",
                "Solution proposals (25%)",
                "Writing quality (25%)"
            ],
            "created_at": datetime.utcnow() - timedelta(days=5),
            "max_points": 100
        },
        {
            "_id": "assignment_002",
            "course_id": "course_data_science_001",
            "title": "Data Visualization Project",
            "description": "Create an interactive dashboard using real-world data.",
            "due_at": datetime.utcnow() + timedelta(days=10),
            "rubric": [
                "Data selection and cleaning (20%)",
                "Visualization design (30%)",
                "Interactivity (20%)",
                "Insights and analysis (30%)"
            ],
            "created_at": datetime.utcnow() - timedelta(days=3),
            "max_points": 100
        },
        {
            "_id": "assignment_003",
            "course_id": "course_web_dev_001",
            "title": "Personal Portfolio Website",
            "description": "Build a responsive portfolio website using HTML, CSS, and JavaScript.",
            "due_at": datetime.utcnow() + timedelta(days=14),
            "rubric": [
                "Design and layout (25%)",
                "Responsiveness (25%)",
                "Functionality (25%)",
                "Code quality (25%)"
            ],
            "created_at": datetime.utcnow() - timedelta(days=7),
            "max_points": 100
        }
    ]

    await db.assignments.insert_many(assignments_data)
    return assignments_data

async def create_submissions(db, assignments, users):
    """Create student submissions for assignments."""
    submissions_data = [
        {
            "_id": "submission_001",
            "assignment_id": "assignment_001",
            "user_id": "student_001",
            "text_answer": "This is my analysis of AI ethics in autonomous vehicles...",
            "file_ids": [],
            "ai_grade": {
                "score": 85,
                "feedback": "Excellent analysis with good understanding of ethical implications.",
                "criteria_scores": {"understanding": 22, "analysis": 21, "solutions": 21, "writing": 21}
            },
            "created_at": datetime.utcnow() - timedelta(days=2)
        },
        {
            "_id": "submission_002",
            "assignment_id": "assignment_002",
            "user_id": "student_002",
            "text_answer": "For this project, I analyzed sales data and created visualizations...",
            "file_ids": [],
            "ai_grade": {
                "score": 92,
                "feedback": "Outstanding work with creative visualizations and deep insights.",
                "criteria_scores": {"data_selection": 18, "design": 28, "interactivity": 23, "insights": 23}
            },
            "created_at": datetime.utcnow() - timedelta(days=1)
        },
        {
            "_id": "submission_003",
            "assignment_id": "assignment_003",
            "user_id": "student_003",
            "text_answer": "I built a modern portfolio website with the following features...",
            "file_ids": [],
            "created_at": datetime.utcnow() - timedelta(hours=12)
        }
    ]

    await db.submissions.insert_many(submissions_data)
    return submissions_data

async def create_progress_data(db, courses, users):
    """Create realistic progress data for students."""
    progress_data = []

    for course in courses:
        for user_id in course["enrolled_user_ids"]:
            if user_id.startswith("student_"):
                # Create progress for each enrolled student
                progress = {
                    "course_id": course["_id"],
                    "user_id": user_id,
                    "lessons_progress": [],
                    "overall_progress": 0,
                    "completed": False,
                    "started_at": datetime.utcnow() - timedelta(days=30)
                }

                # Add lesson progress
                for lesson in course["lessons"]:
                    lesson_progress = {
                        "lesson_id": lesson["id"],
                        "completed": False,
                        "completed_at": None,
                        "quiz_score": None
                    }

                    # Randomly mark some lessons as completed
                    if hash(f"{user_id}_{lesson['id']}") % 100 < 70:  # 70% completion rate
                        lesson_progress["completed"] = True
                        lesson_progress["completed_at"] = datetime.utcnow() - timedelta(days=hash(f"{user_id}_{lesson['id']}") % 25)
                        if hash(f"{user_id}_{lesson['id']}_quiz") % 100 < 80:  # 80% quiz completion
                            lesson_progress["quiz_score"] = 70 + (hash(f"{user_id}_{lesson['id']}_score") % 30)

                    progress["lessons_progress"].append(lesson_progress)

                # Calculate overall progress
                completed_lessons = sum(1 for lp in progress["lessons_progress"] if lp["completed"])
                total_lessons = len(progress["lessons_progress"])
                progress["overall_progress"] = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

                if progress["overall_progress"] >= 100:
                    progress["completed"] = True
                    progress["completed_at"] = datetime.utcnow() - timedelta(days=hash(f"{user_id}_completed") % 10)

                progress_data.append(progress)

    await db.course_progress.insert_many(progress_data)
    return progress_data

async def create_discussions(db, courses, users):
    """Create discussion threads and posts."""
    discussions_data = [
        {
            "_id": "discussion_001",
            "course_id": "course_ai_ml_001",
            "user_id": "student_001",
            "title": "Questions about Neural Network Backpropagation",
            "content": "I'm having trouble understanding how backpropagation actually works. Can someone explain it in simpler terms?",
            "discussion_type": "question",
            "tags": ["neural networks", "backpropagation"],
            "created_at": datetime.utcnow() - timedelta(days=5),
            "updated_at": datetime.utcnow() - timedelta(days=5),
            "view_count": 15,
            "upvote_count": 3,
            "reply_count": 2
        },
        {
            "_id": "discussion_002",
            "course_id": "course_data_science_001",
            "user_id": "student_002",
            "title": "Best Practices for Data Visualization",
            "content": "What are some best practices for creating effective data visualizations?",
            "discussion_type": "discussion",
            "tags": ["visualization", "best practices"],
            "created_at": datetime.utcnow() - timedelta(days=3),
            "updated_at": datetime.utcnow() - timedelta(days=3),
            "view_count": 22,
            "upvote_count": 5,
            "reply_count": 3
        }
    ]

    # Create replies
    replies_data = [
        {
            "_id": "reply_001",
            "discussion_id": "discussion_001",
            "user_id": "instructor_001",
            "content": "Great question! Backpropagation is essentially the algorithm that allows neural networks to learn from their mistakes...",
            "is_instructor_reply": True,
            "created_at": datetime.utcnow() - timedelta(days=4),
            "upvote_count": 5
        },
        {
            "_id": "reply_002",
            "discussion_id": "discussion_001",
            "user_id": "student_002",
            "content": "Thanks for the explanation! I think I'm starting to get it now.",
            "is_instructor_reply": False,
            "created_at": datetime.utcnow() - timedelta(days=3),
            "upvote_count": 2
        }
    ]

    await db.discussions.insert_many(discussions_data)
    await db.discussion_posts.insert_many(replies_data)
    return discussions_data

async def create_notifications(db, users):
    """Create notifications for users."""
    notifications_data = [
        {
            "_id": "notification_001",
            "user_id": "student_001",
            "title": "Assignment Graded",
            "message": "Your AI Ethics Case Study assignment has been graded. Score: 85/100",
            "type": "assignment",
            "read": False,
            "created_at": datetime.utcnow() - timedelta(hours=6)
        },
        {
            "_id": "notification_002",
            "user_id": "student_002",
            "title": "New Course Available",
            "message": "A new course 'Advanced Machine Learning' is now available for enrollment.",
            "type": "course",
            "read": True,
            "created_at": datetime.utcnow() - timedelta(days=1)
        },
        {
            "_id": "notification_003",
            "user_id": "instructor_001",
            "title": "Student Question",
            "message": "A student has asked a question in your AI course discussion.",
            "type": "discussion",
            "read": False,
            "created_at": datetime.utcnow() - timedelta(hours=12)
        }
    ]

    await db.notifications.insert_many(notifications_data)
    return notifications_data

async def create_analytics_data(db, courses, users):
    """Create analytics and reporting data."""
    analytics_data = []

    for course in courses:
        course_analytics = {
            "course_id": course["_id"],
            "total_enrollments": len(course["enrolled_user_ids"]),
            "active_students": len([uid for uid in course["enrolled_user_ids"] if uid.startswith("student_")]),
            "completion_rate": 0.0,
            "average_rating": 4.2,
            "total_reviews": 8,
            "discussion_count": 5,
            "average_time_spent": 240,  # minutes
            "popular_lessons": [
                {"lesson_id": "lesson_1", "views": 45},
                {"lesson_id": "lesson_2", "views": 38}
            ],
            "last_updated": datetime.utcnow()
        }

        # Calculate completion rate
        progress_records = await db.course_progress.find({"course_id": course["_id"]}).to_list(100)
        completed_count = len([p for p in progress_records if p.get("completed")])
        course_analytics["completion_rate"] = (completed_count / len(progress_records) * 100) if progress_records else 0

        analytics_data.append(course_analytics)

    await db.course_analytics.insert_many(analytics_data)
    return analytics_data

if __name__ == "__main__":
    asyncio.run(seed_database())