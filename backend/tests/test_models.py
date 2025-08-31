"""
Unit tests for models module.
"""
import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
from models import (
    UserBase, UserCreate, UserUpdate, UserPublic,
    Course, CourseCreate, CourseUpdate,
    LessonCreate, QuizSubmitRequest,
    Assignment, AssignmentCreate,
    Submission, SubmissionCreate,
    Notification,
    CourseProgress, LessonProgress,
    TokenPair, LoginRequest, RefreshRequest,
    MediaAttachment, CourseLesson, QuizQuestion, QuizOption,
    GenerateCourseRequest
)


class TestUserModels:
    """Test user-related models."""

    def test_user_base_creation(self):
        """Test UserBase model creation."""
        user = UserBase(
            email="test@example.com",
            name="Test User",
            role="student"
        )

        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.role == "student"
        assert isinstance(user.id, str)
        assert len(user.id) == 36  # UUID length
        assert isinstance(user.created_at, datetime)

    def test_user_base_role_validation(self):
        """Test role validation in UserBase."""
        valid_roles = [
            "super_admin", "org_admin", "dept_admin", "instructor",
            "teaching_assistant", "content_author", "student", "auditor",
            "parent_guardian", "proctor", "support_moderator", "career_coach",
            "marketplace_manager", "industry_reviewer", "alumni"
        ]

        for role in valid_roles:
            user = UserBase(email="test@example.com", name="Test User", role=role)
            assert user.role == role

    def test_user_base_invalid_role(self):
        """Test invalid role handling."""
        with pytest.raises(ValidationError):
            UserBase(email="test@example.com", name="Test User", role="invalid_role")

    def test_user_create_model(self):
        """Test UserCreate model."""
        user_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "securepassword123",
            "role": "student"
        }

        user = UserCreate(**user_data)
        assert user.email == "newuser@example.com"
        assert user.name == "New User"
        assert user.password == "securepassword123"
        assert user.role == "student"

    def test_user_create_optional_role(self):
        """Test UserCreate with optional role."""
        user_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "securepassword123"
        }

        user = UserCreate(**user_data)
        assert user.role is None

    def test_user_public_model(self):
        """Test UserPublic model."""
        user_data = {
            "id": "user_123",
            "email": "test@example.com",
            "name": "Test User",
            "role": "student"
        }

        user = UserPublic(**user_data)
        assert user.id == "user_123"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.role == "student"

    def test_user_update_model(self):
        """Test UserUpdate model with optional fields."""
        # Test with all fields
        update_data = {
            "email": "updated@example.com",
            "name": "Updated Name",
            "password": "newpassword123",
            "role": "instructor"
        }

        update = UserUpdate(**update_data)
        assert update.email == "updated@example.com"
        assert update.name == "Updated Name"
        assert update.password == "newpassword123"
        assert update.role == "instructor"

        # Test with only some fields
        partial_update = UserUpdate(name="Just Name")
        assert partial_update.name == "Just Name"
        assert partial_update.email is None
        assert partial_update.password is None
        assert partial_update.role is None


class TestCourseModels:
    """Test course-related models."""

    def test_course_creation(self):
        """Test Course model creation."""
        course_data = {
            "id": "course_123",
            "owner_id": "user_123",
            "title": "Test Course",
            "audience": "Students",
            "difficulty": "beginner",
            "lessons": [],
            "quiz": [],
            "published": True,
            "enrolled_user_ids": ["user_456", "user_789"],
            "created_at": datetime.utcnow()
        }

        course = Course(**course_data)
        assert course.id == "course_123"
        assert course.owner_id == "user_123"
        assert course.title == "Test Course"
        assert course.audience == "Students"
        assert course.difficulty == "beginner"
        assert course.published is True
        assert len(course.enrolled_user_ids) == 2

    def test_course_create_model(self):
        """Test CourseCreate model."""
        course_data = {
            "title": "New Course",
            "audience": "Undergraduate Students",
            "difficulty": "intermediate"
        }

        course = CourseCreate(**course_data)
        assert course.title == "New Course"
        assert course.audience == "Undergraduate Students"
        assert course.difficulty == "intermediate"

    def test_course_update_model(self):
        """Test CourseUpdate model."""
        # Test with some fields
        update_data = {
            "title": "Updated Title",
            "published": False
        }

        update = CourseUpdate(**update_data)
        assert update.title == "Updated Title"
        assert update.published is False
        assert update.audience is None
        assert update.difficulty is None

    def test_generate_course_request(self):
        """Test GenerateCourseRequest model."""
        request_data = {
            "topic": "Machine Learning",
            "audience": "Computer Science Students",
            "difficulty": "intermediate",
            "lessons_count": 5
        }

        request = GenerateCourseRequest(**request_data)
        assert request.topic == "Machine Learning"
        assert request.audience == "Computer Science Students"
        assert request.difficulty == "intermediate"
        assert request.lessons_count == 5

    def test_generate_course_request_validation(self):
        """Test GenerateCourseRequest validation."""
        # Test valid lessons_count range
        valid_request = GenerateCourseRequest(
            topic="Test",
            audience="Students",
            difficulty="beginner",
            lessons_count=10
        )
        assert valid_request.lessons_count == 10

        # Test invalid lessons_count (too high)
        with pytest.raises(ValidationError):
            GenerateCourseRequest(
                topic="Test",
                audience="Students",
                difficulty="beginner",
                lessons_count=25  # Exceeds max of 20
            )

        # Test invalid difficulty
        with pytest.raises(ValidationError):
            GenerateCourseRequest(
                topic="Test",
                audience="Students",
                difficulty="invalid_difficulty"
            )


class TestLessonModels:
    """Test lesson-related models."""

    def test_course_lesson_creation(self):
        """Test CourseLesson model creation."""
        lesson_data = {
            "id": "lesson_123",
            "title": "Introduction to Python",
            "content": "Python is a programming language...",
            "content_type": "text",
            "resources": ["resource_1", "resource_2"],
            "estimated_time": 30,
            "difficulty_level": "beginner",
            "learning_objectives": ["Understand Python basics", "Write simple programs"],
            "order_index": 1
        }

        lesson = CourseLesson(**lesson_data)
        assert lesson.id == "lesson_123"
        assert lesson.title == "Introduction to Python"
        assert lesson.content == "Python is a programming language..."
        assert lesson.content_type == "text"
        assert len(lesson.resources) == 2
        assert lesson.estimated_time == 30
        assert lesson.order_index == 1

    def test_lesson_create_model(self):
        """Test LessonCreate model."""
        lesson_data = {
            "title": "New Lesson",
            "content": "Lesson content here..."
        }

        lesson = LessonCreate(**lesson_data)
        assert lesson.title == "New Lesson"
        assert lesson.content == "Lesson content here..."

    def test_quiz_question_creation(self):
        """Test QuizQuestion model creation."""
        question_data = {
            "id": "question_123",
            "question": "What is 2 + 2?",
            "options": [
                {"text": "3", "is_correct": False},
                {"text": "4", "is_correct": True},
                {"text": "5", "is_correct": False},
                {"text": "6", "is_correct": False}
            ],
            "explanation": "Basic arithmetic"
        }

        question = QuizQuestion(**question_data)
        assert question.id == "question_123"
        assert question.question == "What is 2 + 2?"
        assert len(question.options) == 4
        assert question.options[1].is_correct is True
        assert question.explanation == "Basic arithmetic"

    def test_quiz_option_creation(self):
        """Test QuizOption model creation."""
        option_data = {
            "text": "The answer is 42",
            "is_correct": True
        }

        option = QuizOption(**option_data)
        assert option.text == "The answer is 42"
        assert option.is_correct is True

    def test_quiz_submit_request(self):
        """Test QuizSubmitRequest model."""
        request_data = {
            "question_id": "question_123",
            "selected_index": 1
        }

        request = QuizSubmitRequest(**request_data)
        assert request.question_id == "question_123"
        assert request.selected_index == 1


class TestAssignmentModels:
    """Test assignment-related models."""

    def test_assignment_creation(self):
        """Test Assignment model creation."""
        assignment_data = {
            "id": "assignment_123",
            "course_id": "course_123",
            "title": "Final Project",
            "description": "Complete the final project",
            "due_at": datetime.utcnow() + timedelta(days=7),
            "rubric": ["Creativity", "Technical Skills", "Documentation"],
            "created_at": datetime.utcnow()
        }

        assignment = Assignment(**assignment_data)
        assert assignment.id == "assignment_123"
        assert assignment.course_id == "course_123"
        assert assignment.title == "Final Project"
        assert assignment.description == "Complete the final project"
        assert isinstance(assignment.due_at, datetime)
        assert len(assignment.rubric) == 3

    def test_assignment_create_model(self):
        """Test AssignmentCreate model."""
        assignment_data = {
            "title": "New Assignment",
            "description": "Assignment description",
            "due_at": datetime.utcnow() + timedelta(days=5),
            "rubric": ["Quality", "Completeness"]
        }

        assignment = AssignmentCreate(**assignment_data)
        assert assignment.title == "New Assignment"
        assert assignment.description == "Assignment description"
        assert isinstance(assignment.due_at, datetime)
        assert len(assignment.rubric) == 2

    def test_submission_creation(self):
        """Test Submission model creation."""
        submission_data = {
            "id": "submission_123",
            "assignment_id": "assignment_123",
            "user_id": "user_123",
            "text_answer": "My submission content...",
            "file_ids": ["file_1", "file_2"],
            "ai_grade": {
                "score": 85,
                "feedback": "Good work!",
                "criteria_scores": {"quality": 20, "completeness": 18}
            },
            "created_at": datetime.utcnow()
        }

        submission = Submission(**submission_data)
        assert submission.id == "submission_123"
        assert submission.assignment_id == "assignment_123"
        assert submission.user_id == "user_123"
        assert submission.text_answer == "My submission content..."
        assert len(submission.file_ids) == 2
        assert submission.ai_grade["score"] == 85

    def test_submission_create_model(self):
        """Test SubmissionCreate model."""
        submission_data = {
            "text_answer": "My answer",
            "file_ids": ["file_1"]
        }

        submission = SubmissionCreate(**submission_data)
        assert submission.text_answer == "My answer"
        assert submission.file_ids == ["file_1"]


class TestProgressModels:
    """Test progress-related models."""

    def test_course_progress_creation(self):
        """Test CourseProgress model creation."""
        progress_data = {
            "course_id": "course_123",
            "user_id": "user_123",
            "lessons_progress": [
                {
                    "lesson_id": "lesson_1",
                    "completed": True,
                    "completed_at": datetime.utcnow(),
                    "quiz_score": 85
                }
            ],
            "overall_progress": 75.0,
            "completed": False,
            "started_at": datetime.utcnow() - timedelta(days=10)
        }

        progress = CourseProgress(**progress_data)
        assert progress.course_id == "course_123"
        assert progress.user_id == "user_123"
        assert len(progress.lessons_progress) == 1
        assert progress.overall_progress == 75.0
        assert progress.completed is False

    def test_lesson_progress_creation(self):
        """Test LessonProgress model creation."""
        lesson_progress_data = {
            "lesson_id": "lesson_123",
            "completed": True,
            "completed_at": datetime.utcnow(),
            "quiz_score": 90
        }

        lesson_progress = LessonProgress(**lesson_progress_data)
        assert lesson_progress.lesson_id == "lesson_123"
        assert lesson_progress.completed is True
        assert isinstance(lesson_progress.completed_at, datetime)
        assert lesson_progress.quiz_score == 90


class TestNotificationModel:
    """Test Notification model."""

    def test_notification_creation(self):
        """Test Notification model creation."""
        notification_data = {
            "id": "notification_123",
            "user_id": "user_123",
            "title": "Assignment Due",
            "message": "Your assignment is due tomorrow",
            "type": "assignment",
            "read": False,
            "created_at": datetime.utcnow()
        }

        notification = Notification(**notification_data)
        assert notification.id == "notification_123"
        assert notification.user_id == "user_123"
        assert notification.title == "Assignment Due"
        assert notification.message == "Your assignment is due tomorrow"
        assert notification.type == "assignment"
        assert notification.read is False


class TestAuthModels:
    """Test authentication-related models."""

    def test_token_pair_creation(self):
        """Test TokenPair model creation."""
        token_data = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_456",
            "token_type": "bearer"
        }

        tokens = TokenPair(**token_data)
        assert tokens.access_token == "access_token_123"
        assert tokens.refresh_token == "refresh_token_456"
        assert tokens.token_type == "bearer"

    def test_login_request_creation(self):
        """Test LoginRequest model creation."""
        login_data = {
            "email": "user@example.com",
            "password": "password123"
        }

        login = LoginRequest(**login_data)
        assert login.email == "user@example.com"
        assert login.password == "password123"

    def test_refresh_request_creation(self):
        """Test RefreshRequest model creation."""
        refresh_data = {
            "refresh_token": "refresh_token_123"
        }

        refresh = RefreshRequest(**refresh_data)
        assert refresh.refresh_token == "refresh_token_123"


class TestMediaModels:
    """Test media-related models."""

    def test_media_attachment_creation(self):
        """Test MediaAttachment model creation."""
        media_data = {
            "id": "media_123",
            "filename": "lecture_video.mp4",
            "file_type": "video",
            "file_size": 104857600,  # 100MB
            "url": "https://example.com/media/lecture_video.mp4",
            "thumbnail_url": "https://example.com/thumbnails/lecture_video.jpg",
            "uploaded_by": "user_123",
            "uploaded_at": datetime.utcnow(),
            "metadata": {"duration": "30:00", "resolution": "1920x1080"}
        }

        media = MediaAttachment(**media_data)
        assert media.id == "media_123"
        assert media.filename == "lecture_video.mp4"
        assert media.file_type == "video"
        assert media.file_size == 104857600
        assert media.url == "https://example.com/media/lecture_video.mp4"
        assert media.thumbnail_url == "https://example.com/thumbnails/lecture_video.jpg"
        assert media.uploaded_by == "user_123"
        assert isinstance(media.uploaded_at, datetime)
        assert media.metadata["duration"] == "30:00"