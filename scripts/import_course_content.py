#!/usr/bin/env python3
"""
Script to import comprehensive course content into the LMS database.
This script loads the AI in Education course content and creates all necessary database entries.
"""

import json
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'lms_db')

def _uuid():
    return str(uuid.uuid4())

async def import_course_content():
    """Import the comprehensive course content into the database."""

    # Connect to database
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Load course content from JSON file
    with open('../content/ai-in-education-course.json', 'r', encoding='utf-8') as f:
        course_data = json.load(f)

    course_info = course_data['course']

    # Create course document
    course_doc = {
        "_id": course_info['id'],
        "owner_id": "admin",  # Default admin user
        "title": course_info['title'],
        "description": course_info['description'],
        "audience": course_info['audience'],
        "difficulty": course_info['difficulty'],
        "published": True,
        "created_at": datetime.utcnow(),
        "enrolled_user_ids": [],
        "lessons": [],  # Will be populated from modules
        "quiz": []  # Will be populated from modules
    }

    # Process modules and create lessons/quizzes
    for module_data in course_info['modules']:
        # Create lessons from module content
        if 'content' in module_data and 'core_content' in module_data['content']:
            for section_key, section in module_data['content']['core_content'].items():
                if section_key.startswith('section_'):
                    lesson = {
                        "id": _uuid(),
                        "title": section['title'],
                        "content": section['content'],
                        "resources": [],
                        "transcript_text": None,
                        "summary": None
                    }
                    course_doc['lessons'].append(lesson)

        # Create quizzes from interactive features
        if 'content' in module_data and 'interactive_features' in module_data['content']:
            interactive = module_data['content']['interactive_features']
            if 'quizzes' in interactive:
                for quiz_data in interactive['quizzes']:
                    # Handle different quiz types
                    if quiz_data.get('type') == 'multiple_choice':
                        # Convert string options to objects with is_correct based on correct_answer index
                        options = []
                        correct_index = quiz_data.get('correct_answer', 0)
                        for i, opt_text in enumerate(quiz_data.get('options', [])):
                            options.append({
                                "text": opt_text,
                                "is_correct": i == correct_index
                            })

                        quiz_question = {
                            "id": _uuid(),
                            "question": quiz_data['question'],
                            "options": options,
                            "explanation": quiz_data.get('explanation', '')
                        }
                        course_doc['quiz'].append(quiz_question)

    # Insert course
    await db.courses.insert_one(course_doc)
    print(f"✅ Created course: {course_info['title']}")

    # Create course content document
    course_content_doc = {
        "_id": _uuid(),
        "course_id": course_info['id'],
        "title": course_info['title'],
        "description": course_info['description'],
        "modules": course_info['modules'],
        "assessment_types": course_info['assessment_types'],
        "certification": course_info['certification'],
        "gamification_elements": course_info['gamification_elements'],
        "adaptive_features": course_info['adaptive_features'],
        "collaboration_features": course_info['collaboration_features'],
        "analytics_and_reporting": course_info['analytics_and_reporting'],
        "accessibility_features": course_info['accessibility_features'],
        "integration_capabilities": course_info['integration_capabilities'],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    # Insert course content
    await db.course_content.insert_one(course_content_doc)
    print(f"✅ Created course content with {len(course_info['modules'])} modules")

    # Create sample user for testing (if doesn't exist)
    sample_user = await db.users.find_one({"email": "student@example.com"})
    if not sample_user:
        sample_user_doc = {
            "_id": _uuid(),
            "email": "student@example.com",
            "name": "Demo Student",
            "role": "student",
            "password_hash": "hashed_password",  # In real implementation, use proper hashing
            "created_at": datetime.utcnow()
        }
        await db.users.insert_one(sample_user_doc)
        print("✅ Created sample student user")

        # Enroll sample user in course
        await db.courses.update_one(
            {"_id": course_info['id']},
            {"$push": {"enrolled_user_ids": sample_user_doc["_id"]}}
        )
        print("✅ Enrolled sample user in course")

    # Create sample instructor (if doesn't exist)
    instructor_user = await db.users.find_one({"email": "instructor@example.com"})
    if not instructor_user:
        instructor_doc = {
            "_id": _uuid(),
            "email": "instructor@example.com",
            "name": "Demo Instructor",
            "role": "instructor",
            "password_hash": "hashed_password",
            "created_at": datetime.utcnow()
        }
        await db.users.insert_one(instructor_doc)
        print("✅ Created sample instructor user")

    # Create sample admin (if doesn't exist)
    admin_user = await db.users.find_one({"email": "admin@example.com"})
    if not admin_user:
        admin_doc = {
            "_id": _uuid(),
            "email": "admin@example.com",
            "name": "System Admin",
            "role": "admin",
            "password_hash": "hashed_password",
            "created_at": datetime.utcnow()
        }
        await db.users.insert_one(admin_doc)
        print("✅ Created sample admin user")

    print("\n🎓 Course import completed successfully!")
    print(f"📚 Course ID: {course_info['id']}")
    print(f"📖 Modules: {len(course_info['modules'])}")
    print(f"🎯 Learning Objectives: Comprehensive AI education")
    print(f"🤖 AI Features: Adaptive learning, intelligent assessment, personalized recommendations")
    print(f"🎮 Gamification: Points, badges, leaderboards")
    print(f"Collaboration: Discussion forums, peer learning")
    print(f"Analytics: Detailed progress tracking and insights")

    print("\n🚀 Ready to use! Start the LMS server and access the course content.")

    client.close()

if __name__ == "__main__":
    asyncio.run(import_course_content())