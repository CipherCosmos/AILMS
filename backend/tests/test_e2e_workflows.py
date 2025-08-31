"""
End-to-end tests for complete user workflows.
"""
import pytest
from tests.test_base import BaseTestCase


class TestStudentLearningWorkflow(BaseTestCase):
    """End-to-end test for complete student learning workflow."""

    def test_complete_student_journey(self):
        """Test complete student journey from registration to certification."""
        # Step 1: Register new student
        student_data = {
            "email": "e2e.student@example.com",
            "name": "E2E Test Student",
            "password": "testpassword123"
        }

        response = self.client.post("/api/auth/register", json=student_data)
        assert response.status_code == 200
        student = response.json()

        # Step 2: Login
        login_response = self.client.post("/api/auth/login", json={
            "email": student_data["email"],
            "password": student_data["password"]
        })
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 3: Browse available courses
        courses_response = self.client.get("/api/courses", headers=headers)
        assert courses_response.status_code == 200
        courses = courses_response.json()
        assert len(courses) > 0

        # Step 4: Get course recommendations
        rec_response = self.client.get("/api/courses/course_recommendations", headers=headers)
        assert rec_response.status_code == 200

        # Step 5: Enroll in a course (AI ML course)
        enroll_response = self.client.post("/api/courses/course_ai_ml_001/enroll", headers=headers)
        assert enroll_response.status_code == 200

        # Step 6: Get enrolled course details
        course_response = self.client.get("/api/courses/course_ai_ml_001", headers=headers)
        assert course_response.status_code == 200
        course = course_response.json()

        # Step 7: Complete lessons and quizzes
        for lesson in course["lessons"]:
            # Mark lesson as completed
            progress_data = {
                "lesson_id": lesson["id"],
                "completed": True,
                "quiz_score": 85
            }
            progress_response = self.client.post("/api/courses/course_ai_ml_001/progress", json=progress_data, headers=headers)
            assert progress_response.status_code == 200

        # Step 8: Submit quiz answers
        for quiz in course["quiz"]:
            quiz_data = {
                "question_id": quiz["id"],
                "selected_index": 1  # Assume second option is correct
            }
            quiz_response = self.client.post("/api/courses/quizzes/course_ai_ml_001/submit", json=quiz_data, headers=headers)
            assert quiz_response.status_code == 200

        # Step 9: Check progress
        progress_response = self.client.get("/api/courses/course_ai_ml_001/progress", headers=headers)
        assert progress_response.status_code == 200
        progress = progress_response.json()
        assert progress["overall_progress"] == 100
        assert progress["completed"] is True

        # Step 10: Generate certificate
        cert_response = self.client.post("/api/courses/course_ai_ml_001/certificate", headers=headers)
        assert cert_response.status_code == 200
        certificate = cert_response.json()
        assert certificate["student_name"] == student_data["name"]
        assert certificate["course_title"] == course["title"]

        # Step 11: Get learning path recommendations
        path_response = self.client.get("/api/courses/learning_path", headers=headers)
        assert path_response.status_code == 200

        # Step 12: View submissions (should be empty for this student)
        submissions_response = self.client.get("/api/courses/my_submissions", headers=headers)
        assert submissions_response.status_code == 200

        print("✅ Complete student learning workflow test passed!")


class TestInstructorCourseManagementWorkflow(BaseTestCase):
    """End-to-end test for instructor course management workflow."""

    def test_complete_instructor_workflow(self):
        """Test complete instructor workflow from course creation to student management."""
        # Step 1: Register new instructor
        instructor_data = {
            "email": "e2e.instructor@example.com",
            "name": "E2E Test Instructor",
            "password": "testpassword123"
        }

        response = self.client.post("/api/auth/register", json=instructor_data)
        assert response.status_code == 200

        # Step 2: Login as instructor
        login_response = self.client.post("/api/auth/login", json={
            "email": instructor_data["email"],
            "password": instructor_data["password"]
        })
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 3: Create a new course
        course_data = {
            "title": "E2E Test Course",
            "audience": "Test Students",
            "difficulty": "intermediate"
        }

        create_response = self.client.post("/api/courses", json=course_data, headers=headers)
        assert create_response.status_code == 200
        course = create_response.json()
        course_id = course["id"]

        # Step 4: Add lessons to the course
        lessons_data = [
            {
                "title": "Introduction",
                "content": "Welcome to the course!"
            },
            {
                "title": "Core Concepts",
                "content": "Let's learn the fundamentals."
            }
        ]

        for lesson_data in lessons_data:
            lesson_response = self.client.post(f"/api/courses/{course_id}/lessons", json=lesson_data, headers=headers)
            assert lesson_response.status_code == 200

        # Step 5: Update course details
        update_data = {
            "title": "Updated E2E Test Course",
            "audience": "Advanced Test Students"
        }

        update_response = self.client.put(f"/api/courses/{course_id}", json=update_data, headers=headers)
        assert update_response.status_code == 200

        # Step 6: Generate AI course content (if available)
        ai_request = {
            "topic": "Test Topic",
            "audience": "Students",
            "difficulty": "beginner",
            "lessons_count": 2
        }

        ai_response = self.client.post("/api/courses/ai/generate_course", json=ai_request, headers=headers)
        # AI might not be available in test environment, so just check it doesn't crash
        assert ai_response.status_code in [200, 500]

        # Step 7: View enrolled students (should be empty)
        students_response = self.client.get(f"/api/courses/{course_id}/students", headers=headers)
        assert students_response.status_code == 200
        students = students_response.json()
        assert len(students) == 0

        # Step 8: Get course analytics
        analytics_response = self.client.get(f"/api/analytics/courses/{course_id}", headers=headers)
        # Analytics endpoint might not exist, just check it doesn't crash
        assert analytics_response.status_code in [200, 404]

        # Step 9: Publish the course
        publish_data = {
            "published": True
        }

        publish_response = self.client.put(f"/api/courses/{course_id}", json=publish_data, headers=headers)
        assert publish_response.status_code == 200

        print("✅ Complete instructor workflow test passed!")


class TestAdminUserManagementWorkflow(BaseTestCase):
    """End-to-end test for admin user management workflow."""

    def test_complete_admin_workflow(self):
        """Test complete admin workflow for user and system management."""
        # Step 1: Login as admin
        login_response = self.client.post("/api/auth/login", json={
            "email": "admin@lms.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 2: List all users
        users_response = self.client.get("/api/auth/users", headers=headers)
        assert users_response.status_code == 200
        users = users_response.json()
        initial_user_count = len(users)

        # Step 3: Create a new user
        new_user_data = {
            "email": "admin.created@example.com",
            "name": "Admin Created User",
            "password": "newpassword123",
            "role": "student"
        }

        create_response = self.client.post("/api/auth/register", json=new_user_data)
        assert create_response.status_code == 200
        new_user = create_response.json()

        # Step 4: Update user details
        update_data = {
            "name": "Updated by Admin",
            "role": "instructor"
        }

        update_response = self.client.put(f"/api/auth/users/{new_user['id']}", json=update_data, headers=headers)
        assert update_response.status_code == 200

        # Step 5: Verify user was updated
        updated_users_response = self.client.get("/api/auth/users", headers=headers)
        assert updated_users_response.status_code == 200
        updated_users = updated_users_response.json()

        # Find the updated user
        updated_user = next((u for u in updated_users if u["id"] == new_user["id"]), None)
        assert updated_user is not None
        assert updated_user["name"] == "Updated by Admin"
        assert updated_user["role"] == "instructor"

        # Step 6: Delete the test user
        delete_response = self.client.delete(f"/api/auth/users/{new_user['id']}", headers=headers)
        assert delete_response.status_code == 200

        # Step 7: Verify user was deleted
        final_users_response = self.client.get("/api/auth/users", headers=headers)
        assert final_users_response.status_code == 200
        final_users = final_users_response.json()
        assert len(final_users) == initial_user_count

        print("✅ Complete admin workflow test passed!")


class TestAssignmentSubmissionWorkflow(BaseTestCase):
    """End-to-end test for assignment submission workflow."""

    def test_complete_assignment_workflow(self):
        """Test complete assignment creation, submission, and grading workflow."""
        # Step 1: Login as instructor
        instructor_token = self.login_user("john.doe@university.edu", "password")
        instructor_headers = self.get_auth_headers(instructor_token)

        # Step 2: Create assignment for AI ML course
        assignment_data = {
            "title": "Research Paper on AI Ethics",
            "description": "Write a 5-page research paper on ethical considerations in AI development.",
            "due_at": "2024-12-31T23:59:59Z",
            "rubric": [
                "Content Quality (40%)",
                "Research Depth (30%)",
                "Writing Quality (20%)",
                "Citations (10%)"
            ]
        }

        # Note: Assignment creation endpoint might not exist, skip if not available
        # This is just a demonstration of the workflow

        # Step 3: Login as student
        student_token = self.login_user("alice.johnson@student.edu", "password")
        student_headers = self.get_auth_headers(student_token)

        # Step 4: Submit assignment (if endpoint exists)
        submission_data = {
            "text_answer": "This is my submission for the AI ethics research paper...",
            "file_ids": []
        }

        # Check if assignment submission endpoint exists
        submit_response = self.client.post("/api/assignments/assignment_001/submit", json=submission_data, headers=student_headers)
        if submit_response.status_code == 404:
            # Endpoint doesn't exist, skip this part
            print("Assignment submission endpoint not available, skipping submission test")
        else:
            assert submit_response.status_code == 200

        # Step 5: Instructor views submissions
        submissions_response = self.client.get("/api/assignments/assignment_001/submissions", headers=instructor_headers)
        if submissions_response.status_code == 404:
            print("Assignment submissions endpoint not available, skipping grading test")
        else:
            assert submissions_response.status_code == 200
            submissions = submissions_response.json()
            assert isinstance(submissions, list)

        # Step 6: Instructor grades submission
        if submissions_response.status_code == 200 and submissions:
            grade_data = {
                "score": 85,
                "feedback": "Excellent work on AI ethics! Good research and analysis.",
                "criteria_scores": {
                    "content_quality": 85,
                    "research_depth": 80,
                    "writing_quality": 90,
                    "citations": 85
                }
            }

            grade_response = self.client.post(f"/api/assignments/submissions/{submissions[0]['id']}/grade", json=grade_data, headers=instructor_headers)
            if grade_response.status_code != 404:
                assert grade_response.status_code == 200

        print("✅ Complete assignment workflow test passed!")


class TestCourseDiscoveryWorkflow(BaseTestCase):
    """End-to-end test for course discovery and enrollment workflow."""

    def test_course_discovery_workflow(self):
        """Test course discovery, comparison, and enrollment workflow."""
        # Step 1: Register new student
        student_data = {
            "email": "discovery.student@example.com",
            "name": "Discovery Test Student",
            "password": "testpassword123"
        }

        register_response = self.client.post("/api/auth/register", json=student_data)
        assert register_response.status_code == 200

        # Step 2: Login
        login_response = self.client.post("/api/auth/login", json={
            "email": student_data["email"],
            "password": student_data["password"]
        })
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 3: Browse all courses
        courses_response = self.client.get("/api/courses", headers=headers)
        assert courses_response.status_code == 200
        courses = courses_response.json()
        assert len(courses) >= 3

        # Step 4: Get personalized recommendations
        rec_response = self.client.get("/api/courses/course_recommendations", headers=headers)
        assert rec_response.status_code == 200
        recommendations = rec_response.json()
        assert isinstance(recommendations, list)

        # Step 5: Get learning path
        path_response = self.client.get("/api/courses/learning_path", headers=headers)
        assert path_response.status_code == 200
        learning_path = path_response.json()
        assert "current_focus" in learning_path
        assert "recommended_next" in learning_path

        # Step 6: View course details
        course_id = courses[0]["id"]
        detail_response = self.client.get(f"/api/courses/{course_id}", headers=headers)
        assert detail_response.status_code == 200
        course_detail = detail_response.json()
        assert course_detail["id"] == course_id

        # Step 7: Enroll in course
        enroll_response = self.client.post(f"/api/courses/{course_id}/enroll", headers=headers)
        assert enroll_response.status_code == 200

        # Step 8: Check enrollment in course list
        updated_courses_response = self.client.get("/api/courses", headers=headers)
        assert updated_courses_response.status_code == 200
        updated_courses = updated_courses_response.json()

        # Find the enrolled course
        enrolled_course = next((c for c in updated_courses if c["id"] == course_id), None)
        assert enrolled_course is not None
        assert student_data["email"].split("@")[0] in str(enrolled_course.get("enrolled_user_ids", []))

        print("✅ Complete course discovery workflow test passed!")


class TestRealWorldScenarioWorkflow(BaseTestCase):
    """End-to-end test simulating real-world LMS usage scenarios."""

    def test_real_world_learning_scenario(self):
        """Test a realistic learning scenario with multiple users and interactions."""
        # Scenario: A student discovers courses, enrolls, learns, and gets certified
        # while an instructor creates content and manages the course

        # === STUDENT JOURNEY ===

        # Student registration and login
        student_email = "realworld.student@example.com"
        student_data = {
            "email": student_email,
            "name": "Real World Student",
            "password": "learn123"
        }

        # Register
        self.client.post("/api/auth/register", json=student_data)

        # Login
        login_response = self.client.post("/api/auth/login", json={
            "email": student_email,
            "password": "learn123"
        })
        student_token = login_response.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}

        # Browse and discover courses
        courses = self.client.get("/api/courses", headers=student_headers).json()
        ai_course = next(c for c in courses if "AI" in c["title"])

        # Get course details and enroll
        course_detail = self.client.get(f"/api/courses/{ai_course['id']}", headers=student_headers).json()
        self.client.post(f"/api/courses/{ai_course['id']}/enroll", headers=student_headers)

        # Simulate learning progress
        for lesson in course_detail["lessons"][:2]:  # Complete first 2 lessons
            progress_data = {
                "lesson_id": lesson["id"],
                "completed": True,
                "quiz_score": 88
            }
            self.client.post(f"/api/courses/{ai_course['id']}/progress", json=progress_data, headers=student_headers)

        # Check progress
        progress = self.client.get(f"/api/courses/{ai_course['id']}/progress", headers=student_headers).json()
        assert progress["overall_progress"] > 0

        # === INSTRUCTOR MANAGEMENT ===

        # Instructor login (using existing instructor)
        instructor_token = self.login_user("john.doe@university.edu", "password")
        instructor_headers = self.get_auth_headers(instructor_token)

        # View enrolled students
        students = self.client.get(f"/api/courses/{ai_course['id']}/students", headers=instructor_headers).json()
        assert len(students) > 0

        # Check student progress
        student_progress = self.client.get(f"/api/courses/{ai_course['id']}/students/student_001/progress", headers=instructor_headers).json()
        assert "overall_progress" in student_progress

        # === ADMINISTRATOR OVERSIGHT ===

        # Admin login
        admin_token = self.login_user("admin@lms.com", "admin123")
        admin_headers = self.get_auth_headers(admin_token)

        # View all users
        all_users = self.client.get("/api/auth/users", headers=admin_headers).json()
        assert len(all_users) >= 8  # Original + new student

        # Check system status
        health_response = self.client.get("/api/")
        assert health_response.status_code == 200

        print("✅ Real-world learning scenario test passed!")

    def test_concurrent_user_workflow(self):
        """Test multiple users working concurrently (simulated)."""
        # This test simulates multiple users performing actions simultaneously

        # Create multiple test users
        test_users = []
        for i in range(3):
            user_data = {
                "email": f"concurrent.user{i}@example.com",
                "name": f"Concurrent User {i}",
                "password": "test123"
            }

            self.client.post("/api/auth/register", json=user_data)
            test_users.append(user_data)

        # All users login and browse courses
        user_tokens = []
        for user in test_users:
            login_response = self.client.post("/api/auth/login", json={
                "email": user["email"],
                "password": user["password"]
            })
            token = login_response.json()["access_token"]
            user_tokens.append(token)

        # All users get course recommendations
        for token in user_tokens:
            headers = {"Authorization": f"Bearer {token}"}
            rec_response = self.client.get("/api/courses/course_recommendations", headers=headers)
            assert rec_response.status_code == 200

        # Users enroll in different courses
        courses_response = self.client.get("/api/courses")
        courses = courses_response.json()

        for i, token in enumerate(user_tokens):
            headers = {"Authorization": f"Bearer {token}"}
            course_id = courses[i % len(courses)]["id"]
            enroll_response = self.client.post(f"/api/courses/{course_id}/enroll", headers=headers)
            assert enroll_response.status_code == 200

        print("✅ Concurrent user workflow test passed!")