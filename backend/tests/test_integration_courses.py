"""
Integration tests for courses endpoints.
"""
import pytest
from tests.test_base import BaseTestCase


class TestCoursesEndpoints(BaseTestCase):
    """Integration tests for courses endpoints."""

    def test_list_courses_authenticated(self):
        """Test listing courses when authenticated."""
        # Login as student
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.get("/api/courses", headers=headers)
        assert response.status_code == 200

        courses = response.json()
        assert isinstance(courses, list)
        assert len(courses) >= 3  # Should have at least the seeded courses

        # Check course structure
        for course in courses:
            assert "id" in course
            assert "title" in course
            assert "audience" in course
            assert "difficulty" in course
            assert "owner_id" in course

    def test_list_courses_unauthenticated(self):
        """Test listing courses without authentication."""
        response = self.client.get("/api/courses")
        assert response.status_code == 401

    def test_get_course_authenticated(self):
        """Test getting a specific course when authenticated."""
        # Login as student
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Get the AI ML course
        response = self.client.get("/api/courses/course_ai_ml_001", headers=headers)
        assert response.status_code == 200

        course = response.json()
        assert course["id"] == "course_ai_ml_001"
        assert course["title"] == "Introduction to Artificial Intelligence and Machine Learning"
        assert "lessons" in course
        assert "quiz" in course

    def test_get_course_not_enrolled(self):
        """Test getting course when not enrolled (should fail for private course)."""
        # Login as a different student
        token = self.login_user("carol.brown@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Try to get AI ML course (Carol is not enrolled)
        response = self.client.get("/api/courses/course_ai_ml_001", headers=headers)
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    def test_get_course_as_instructor(self):
        """Test getting course as instructor (owner)."""
        # Login as instructor
        token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.get("/api/courses/course_ai_ml_001", headers=headers)
        assert response.status_code == 200

        course = response.json()
        assert course["owner_id"] == "instructor_001"

    def test_get_course_as_admin(self):
        """Test getting course as admin."""
        # Login as admin
        token = self.login_user("admin@lms.com", "admin123")
        headers = self.get_auth_headers(token)

        response = self.client.get("/api/courses/course_ai_ml_001", headers=headers)
        assert response.status_code == 200

    def test_get_nonexistent_course(self):
        """Test getting a nonexistent course."""
        # Login as admin
        token = self.login_user("admin@lms.com", "admin123")
        headers = self.get_auth_headers(token)

        response = self.client.get("/api/courses/nonexistent_course", headers=headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_course_as_instructor(self):
        """Test creating a course as instructor."""
        # Login as instructor
        token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(token)

        course_data = {
            "title": "New Test Course",
            "audience": "Graduate Students",
            "difficulty": "advanced"
        }

        response = self.client.post("/api/courses", json=course_data, headers=headers)
        assert response.status_code == 200

        course = response.json()
        assert course["title"] == "New Test Course"
        assert course["audience"] == "Graduate Students"
        assert course["difficulty"] == "advanced"
        assert course["owner_id"] == "instructor_001"
        assert "id" in course

    def test_create_course_as_student(self):
        """Test creating course as student (should fail)."""
        # Login as student
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        course_data = {
            "title": "Student Course",
            "audience": "Students",
            "difficulty": "beginner"
        }

        response = self.client.post("/api/courses", json=course_data, headers=headers)
        assert response.status_code == 403
        assert "insufficient permissions" in response.json()["detail"].lower()

    def test_update_course_as_owner(self):
        """Test updating course as owner."""
        # Login as instructor (owner of AI ML course)
        token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(token)

        update_data = {
            "title": "Updated AI Course Title",
            "audience": "Advanced Students"
        }

        response = self.client.put("/api/courses/course_ai_ml_001", json=update_data, headers=headers)
        assert response.status_code == 200

        course = response.json()
        assert course["title"] == "Updated AI Course Title"
        assert course["audience"] == "Advanced Students"

    def test_update_course_as_non_owner(self):
        """Test updating course as non-owner (should fail)."""
        # Login as different instructor
        token = self.login_user("jane.smith@university.edu", "password")
        headers = self.get_auth_headers(token)

        update_data = {
            "title": "Hacked Title"
        }

        response = self.client.put("/api/courses/course_ai_ml_001", json=update_data, headers=headers)
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    def test_enroll_in_course(self):
        """Test enrolling in a course."""
        # Login as student not enrolled in web dev course
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.post("/api/courses/course_web_dev_001/enroll", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "enrolled"

    def test_enroll_already_enrolled(self):
        """Test enrolling in already enrolled course."""
        # Login as Alice (already enrolled in AI ML course)
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.post("/api/courses/course_ai_ml_001/enroll", headers=headers)
        assert response.status_code == 200
        # Should still succeed (idempotent operation)

    def test_add_lesson_as_owner(self):
        """Test adding lesson as course owner."""
        # Login as instructor (owner of AI ML course)
        token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(token)

        lesson_data = {
            "title": "New Lesson on Ethics",
            "content": "This lesson covers AI ethics in detail..."
        }

        response = self.client.post("/api/courses/course_ai_ml_001/lessons", json=lesson_data, headers=headers)
        assert response.status_code == 200

        course = response.json()
        assert len(course["lessons"]) > 3  # Should have original 3 + new lesson
        assert any(lesson["title"] == "New Lesson on Ethics" for lesson in course["lessons"])

    def test_add_lesson_as_non_owner(self):
        """Test adding lesson as non-owner (should fail)."""
        # Login as different instructor
        token = self.login_user("jane.smith@university.edu", "password")
        headers = self.get_auth_headers(token)

        lesson_data = {
            "title": "Unauthorized Lesson",
            "content": "This should not be allowed"
        }

        response = self.client.post("/api/courses/course_ai_ml_001/lessons", json=lesson_data, headers=headers)
        assert response.status_code == 403

    def test_generate_course_ai(self):
        """Test AI course generation."""
        # Login as instructor
        token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(token)

        course_request = {
            "topic": "Blockchain Technology",
            "audience": "Computer Science Students",
            "difficulty": "intermediate",
            "lessons_count": 3
        }

        response = self.client.post("/api/courses/ai/generate_course", json=course_request, headers=headers)
        assert response.status_code == 200

        course = response.json()
        assert "id" in course
        assert course["title"] is not None
        assert len(course["lessons"]) == 3
        assert course["owner_id"] == "instructor_001"

    def test_submit_quiz(self):
        """Test quiz submission."""
        # Login as student
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Submit answer for first quiz question (correct answer is index 1)
        quiz_data = {
            "question_id": "quiz_1",
            "selected_index": 1
        }

        response = self.client.post("/api/courses/quizzes/course_ai_ml_001/submit", json=quiz_data, headers=headers)
        assert response.status_code == 200

        result = response.json()
        assert "correct" in result
        assert "explanation" in result
        assert result["correct"] is True  # Should be correct

    def test_submit_quiz_wrong_answer(self):
        """Test quiz submission with wrong answer."""
        # Login as student
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Submit wrong answer (index 0 is wrong)
        quiz_data = {
            "question_id": "quiz_1",
            "selected_index": 0
        }

        response = self.client.post("/api/courses/quizzes/course_ai_ml_001/submit", json=quiz_data, headers=headers)
        assert response.status_code == 200

        result = response.json()
        assert result["correct"] is False

    def test_update_progress(self):
        """Test updating course progress."""
        # Login as student
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        progress_data = {
            "lesson_id": "lesson_1",
            "completed": True,
            "quiz_score": 85
        }

        response = self.client.post("/api/courses/course_ai_ml_001/progress", json=progress_data, headers=headers)
        assert response.status_code == 200

        result = response.json()
        assert "progress" in result
        assert "completed" in result
        assert result["progress"] >= 0

    def test_get_progress(self):
        """Test getting course progress."""
        # Login as student
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.get("/api/courses/course_ai_ml_001/progress", headers=headers)
        assert response.status_code == 200

        progress = response.json()
        assert "course_id" in progress
        assert "user_id" in progress
        assert "lessons_progress" in progress
        assert "overall_progress" in progress
        assert "completed" in progress

    def test_generate_certificate(self):
        """Test certificate generation."""
        # First, complete a course by updating progress
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Mark all lessons as completed
        course_response = self.client.get("/api/courses/course_ai_ml_001", headers=headers)
        course = course_response.json()

        for lesson in course["lessons"]:
            progress_data = {
                "lesson_id": lesson["id"],
                "completed": True,
                "quiz_score": 90
            }
            self.client.post("/api/courses/course_ai_ml_001/progress", json=progress_data, headers=headers)

        # Now try to generate certificate
        response = self.client.post("/api/courses/course_ai_ml_001/certificate", headers=headers)
        assert response.status_code == 200

        certificate = response.json()
        assert "student_name" in certificate
        assert "course_title" in certificate
        assert "completion_date" in certificate
        assert "certificate_id" in certificate

    def test_generate_certificate_incomplete_course(self):
        """Test certificate generation for incomplete course."""
        # Login as student with incomplete course
        token = self.login_user("bob.wilson@student.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.post("/api/courses/course_data_science_001/certificate", headers=headers)
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

    def test_get_basic_recommendations(self):
        """Test getting basic course recommendations."""
        # Login as student
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.get("/api/courses/basic_recommendations", headers=headers)
        assert response.status_code == 200

        recommendations = response.json()
        assert "recommendations" in recommendations
        assert isinstance(recommendations["recommendations"], list)

    def test_get_learning_path(self):
        """Test getting personalized learning path."""
        # Login as student
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.get("/api/courses/learning_path", headers=headers)
        assert response.status_code == 200

        learning_path = response.json()
        assert "current_focus" in learning_path
        assert "upcoming_courses" in learning_path
        assert "recommended_next" in learning_path
        assert "completed_milestones" in learning_path

    def test_get_course_recommendations(self):
        """Test getting course recommendations."""
        # Login as student
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.get("/api/courses/course_recommendations", headers=headers)
        assert response.status_code == 200

        recommendations = response.json()
        assert isinstance(recommendations, list)

        for rec in recommendations:
            assert "course_id" in rec
            assert "title" in rec
            assert "difficulty" in rec
            assert "score" in rec

    def test_get_my_submissions(self):
        """Test getting user's submissions."""
        # Login as student who has submissions
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.get("/api/courses/my_submissions", headers=headers)
        assert response.status_code == 200

        submissions = response.json()
        assert isinstance(submissions, list)

        # Should have at least one submission from seed data
        assert len(submissions) >= 1

        for submission in submissions:
            assert "id" in submission
            assert "assignment_title" in submission
            assert "course_title" in submission
            assert "created_at" in submission

    def test_get_enrolled_students_as_owner(self):
        """Test getting enrolled students as course owner."""
        # Login as instructor (owner)
        token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.get("/api/courses/course_ai_ml_001/students", headers=headers)
        assert response.status_code == 200

        students = response.json()
        assert isinstance(students, list)
        assert len(students) >= 3  # Alice, Bob, Carol from seed data

        for student in students:
            assert "id" in student
            assert "name" in student
            assert "email" in student

    def test_get_enrolled_students_as_non_owner(self):
        """Test getting enrolled students as non-owner (should fail)."""
        # Login as different instructor
        token = self.login_user("jane.smith@university.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.get("/api/courses/course_ai_ml_001/students", headers=headers)
        assert response.status_code == 403

    def test_get_student_progress_as_instructor(self):
        """Test getting student progress as instructor."""
        # Login as instructor
        token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(token)

        # Get Alice's progress
        response = self.client.get("/api/courses/course_ai_ml_001/students/student_001/progress", headers=headers)
        assert response.status_code == 200

        progress = response.json()
        assert "course_id" in progress
        assert "user_id" in progress
        assert progress["user_id"] == "student_001"

    def test_update_student_progress_as_instructor(self):
        """Test updating student progress as instructor."""
        # Login as instructor
        token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(token)

        progress_data = {
            "overall_progress": 75.0,
            "completed": False
        }

        response = self.client.put("/api/courses/course_ai_ml_001/students/student_001/progress", json=progress_data, headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "updated"

    def test_remove_student_from_course(self):
        """Test removing student from course as instructor."""
        # Login as instructor
        token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.delete("/api/courses/course_ai_ml_001/students/student_002", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "removed"

    def test_delete_course_as_owner(self):
        """Test deleting course as owner."""
        # First create a test course
        token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(token)

        course_data = {
            "title": "Course to Delete",
            "audience": "Test Audience",
            "difficulty": "beginner"
        }

        create_response = self.client.post("/api/courses", json=course_data, headers=headers)
        course_id = create_response.json()["id"]

        # Now delete it
        response = self.client.delete(f"/api/courses/{course_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify it's gone
        get_response = self.client.get(f"/api/courses/{course_id}", headers=headers)
        assert get_response.status_code == 404

    def test_delete_course_as_non_owner(self):
        """Test deleting course as non-owner (should fail)."""
        # Login as different instructor
        token = self.login_user("jane.smith@university.edu", "password")
        headers = self.get_auth_headers(token)

        response = self.client.delete("/api/courses/course_ai_ml_001", headers=headers)
        assert response.status_code == 403


class TestCoursesSecurity:
    """Security tests for courses endpoints."""

    def test_course_id_injection_attempt(self):
        """Test protection against course ID injection."""
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Try with malicious course ID
        malicious_id = "course_ai_ml_001'; DROP TABLE users; --"
        response = self.client.get(f"/api/courses/{malicious_id}", headers=headers)
        # Should either return 404 or 403, not execute injection
        assert response.status_code in [403, 404]

    def test_unauthorized_course_access(self):
        """Test that users cannot access courses they're not authorized for."""
        # Create a private course (not published)
        token = self.login_user("john.doe@university.edu", "password")
        headers = self.get_auth_headers(token)

        course_data = {
            "title": "Private Course",
            "audience": "Test",
            "difficulty": "beginner",
            "published": False
        }

        create_response = self.client.post("/api/courses", json=course_data, headers=headers)
        private_course_id = create_response.json()["id"]

        # Try to access as different user
        other_token = self.login_user("alice.johnson@student.edu", "password")
        other_headers = self.get_auth_headers(other_token)

        response = self.client.get(f"/api/courses/{private_course_id}", headers=other_headers)
        assert response.status_code == 403

    def test_mass_assignment_prevention(self):
        """Test prevention of mass assignment vulnerabilities."""
        token = self.login_user("alice.johnson@student.edu", "password")
        headers = self.get_auth_headers(token)

        # Try to update progress with unauthorized fields
        malicious_data = {
            "lesson_id": "lesson_1",
            "completed": True,
            "admin_only_field": "malicious_value",
            "system_field": "hacked"
        }

        response = self.client.post("/api/courses/course_ai_ml_001/progress", json=malicious_data, headers=headers)
        assert response.status_code == 200

        # Verify that malicious fields were not stored
        progress_response = self.client.get("/api/courses/course_ai_ml_001/progress", headers=headers)
        progress = progress_response.json()

        # Should not contain the malicious fields
        assert "admin_only_field" not in str(progress)
        assert "system_field" not in str(progress)