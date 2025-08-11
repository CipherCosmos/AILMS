#!/usr/bin/env python3
"""
Backend API Testing Script for Expanded LMS APIs
Tests all backend endpoints according to the review request sequence 2.
"""

import requests
import json
import sys
import io
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BACKEND_URL = "https://b73e20c6-764f-43c9-85dc-0258a2ed0875.preview.emergentagent.com"

class BackendTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.created_course_id = None
        self.instructor_token = None
        self.student_token = None
        self.instructor_user_id = None
        self.student_user_id = None
        self.assignment_id = None
        self.submission_id = None
        self.thread_id = None
        self.file_id = None
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        if response_data and not success:
            print(f"   Response: {response_data}")
        print()
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data
        })

    # ===== AUTH TESTS =====
    
    def test_auth_register_instructor(self):
        """Test 1: POST /api/auth/register (instructor)"""
        payload = {
            "email": "instructor@example.com",
            "name": "John Instructor",
            "password": "instructor123",
            "role": "instructor"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "email", "name", "role"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Auth Register Instructor", False, f"Missing fields: {missing_fields}", data)
                    return
                
                # First user gets admin role automatically (bootstrap)
                if data["role"] in ["instructor", "admin"] and data["email"] == "instructor@example.com":
                    self.instructor_user_id = data["id"]
                    self.log_test("Auth Register Instructor", True, f"User registered with ID: {self.instructor_user_id}, role: {data['role']}")
                else:
                    self.log_test("Auth Register Instructor", False, f"Role/email mismatch", data)
            elif response.status_code == 400 and "Email already registered" in response.text:
                # User already exists, this is fine for testing
                self.log_test("Auth Register Instructor", True, "User already exists (from previous test run)")
            else:
                self.log_test("Auth Register Instructor", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Auth Register Instructor", False, f"Exception: {str(e)}")

    def test_auth_login_instructor(self):
        """Test 2: POST /api/auth/login (instructor)"""
        payload = {
            "email": "instructor@example.com",
            "password": "instructor123"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["access_token", "refresh_token", "token_type"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Auth Login Instructor", False, f"Missing fields: {missing_fields}", data)
                    return
                
                self.instructor_token = data["access_token"]
                self.log_test("Auth Login Instructor", True, "Instructor login successful, tokens received")
            else:
                self.log_test("Auth Login Instructor", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Auth Login Instructor", False, f"Exception: {str(e)}")

    def test_auth_me_instructor(self):
        """Test 3: GET /api/auth/me (instructor)"""
        if not self.instructor_token:
            self.log_test("Auth Me Instructor", False, "No instructor token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.instructor_token}"}
            response = self.session.get(f"{self.base_url}/api/auth/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # First user gets admin role automatically (bootstrap)
                if data.get("role") in ["instructor", "admin"] and data.get("email") == "instructor@example.com":
                    self.log_test("Auth Me Instructor", True, f"User profile retrieved: {data['name']}, role: {data['role']}")
                else:
                    self.log_test("Auth Me Instructor", False, "Profile data mismatch", data)
            else:
                self.log_test("Auth Me Instructor", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Auth Me Instructor", False, f"Exception: {str(e)}")

    def test_auth_refresh(self):
        """Test 4: POST /api/auth/refresh"""
        # First get refresh token from login
        payload = {
            "email": "instructor@example.com",
            "password": "instructor123"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                self.log_test("Auth Refresh", False, "Could not get refresh token", response.text)
                return
                
            refresh_token = response.json().get("refresh_token")
            if not refresh_token:
                self.log_test("Auth Refresh", False, "No refresh token in login response")
                return
            
            # Now test refresh
            refresh_payload = {"refresh_token": refresh_token}
            refresh_response = self.session.post(
                f"{self.base_url}/api/auth/refresh",
                json=refresh_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if refresh_response.status_code == 200:
                data = refresh_response.json()
                if "access_token" in data and "refresh_token" in data:
                    self.log_test("Auth Refresh", True, "Token refresh successful")
                else:
                    self.log_test("Auth Refresh", False, "Missing tokens in refresh response", data)
            else:
                self.log_test("Auth Refresh", False, f"Status code: {refresh_response.status_code}", refresh_response.text)
                
        except Exception as e:
            self.log_test("Auth Refresh", False, f"Exception: {str(e)}")

    # ===== COURSE & LESSONS TESTS =====
    
    def test_create_course(self):
        """Test 5: POST /api/courses (as instructor)"""
        if not self.instructor_token:
            self.log_test("Create Course", False, "No instructor token available")
            return
            
        payload = {
            "title": "Advanced Python Programming",
            "audience": "Intermediate developers",
            "difficulty": "intermediate"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.instructor_token}", "Content-Type": "application/json"}
            response = self.session.post(f"{self.base_url}/api/courses", json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "owner_id", "title", "audience", "difficulty"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Create Course", False, f"Missing fields: {missing_fields}", data)
                    return
                
                self.created_course_id = data["id"]
                self.log_test("Create Course", True, f"Course created with ID: {self.created_course_id}")
            else:
                self.log_test("Create Course", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Create Course", False, f"Exception: {str(e)}")

    def test_list_courses_instructor(self):
        """Test 6: GET /api/courses (instructor - should see owned courses)"""
        if not self.instructor_token:
            self.log_test("List Courses Instructor", False, "No instructor token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.instructor_token}"}
            response = self.session.get(f"{self.base_url}/api/courses", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                if not isinstance(data, list):
                    self.log_test("List Courses Instructor", False, "Response is not a list", data)
                    return
                
                # Check if our created course is in the list
                if self.created_course_id:
                    course_found = any(course.get("id") == self.created_course_id for course in data)
                    if course_found:
                        self.log_test("List Courses Instructor", True, f"Found {len(data)} courses, including owned course")
                    else:
                        self.log_test("List Courses Instructor", False, f"Created course not found in list", data)
                else:
                    self.log_test("List Courses Instructor", True, f"Retrieved {len(data)} courses")
                    
            else:
                self.log_test("List Courses Instructor", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("List Courses Instructor", False, f"Exception: {str(e)}")

    def test_add_lesson(self):
        """Test 7: POST /api/courses/{cid}/lessons"""
        if not self.instructor_token or not self.created_course_id:
            self.log_test("Add Lesson", False, "Missing instructor token or course ID")
            return
            
        payload = {
            "title": "Introduction to Python Classes",
            "content": "This lesson covers the basics of object-oriented programming in Python, including class definition, inheritance, and polymorphism."
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.instructor_token}", "Content-Type": "application/json"}
            response = self.session.post(
                f"{self.base_url}/api/courses/{self.created_course_id}/lessons",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if "lessons" in data and len(data["lessons"]) > 0:
                    lesson = data["lessons"][-1]  # Get the last added lesson
                    if lesson.get("title") == payload["title"]:
                        self.log_test("Add Lesson", True, f"Lesson added: {lesson['title']}")
                    else:
                        self.log_test("Add Lesson", False, "Lesson title mismatch", data)
                else:
                    self.log_test("Add Lesson", False, "No lessons in response", data)
            else:
                self.log_test("Add Lesson", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Add Lesson", False, f"Exception: {str(e)}")

    def test_ai_generate_course(self):
        """Test 8: POST /api/ai/generate_course (instructor)"""
        if not self.instructor_token:
            self.log_test("AI Generate Course", False, "No instructor token available")
            return
            
        payload = {
            "topic": "Machine Learning Fundamentals",
            "audience": "Data science beginners",
            "difficulty": "beginner",
            "lessons_count": 3
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.instructor_token}", "Content-Type": "application/json"}
            response = self.session.post(
                f"{self.base_url}/api/ai/generate_course",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "title", "lessons", "quiz"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("AI Generate Course", False, f"Missing fields: {missing_fields}", data)
                    return
                
                if len(data["lessons"]) == 3:
                    self.log_test("AI Generate Course", True, f"AI course created: {data['title']} with {len(data['lessons'])} lessons and {len(data['quiz'])} quiz questions")
                else:
                    self.log_test("AI Generate Course", False, f"Expected 3 lessons, got {len(data['lessons'])}", data)
            else:
                self.log_test("AI Generate Course", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("AI Generate Course", False, f"Exception: {str(e)}")

    # ===== STUDENT ENROLLMENT TESTS =====
    
    def test_register_student(self):
        """Test 9: Register student user"""
        payload = {
            "email": "student@example.com",
            "name": "Jane Student",
            "password": "student123",
            "role": "student"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data["role"] == "student" and data["email"] == "student@example.com":
                    self.student_user_id = data["id"]
                    self.log_test("Register Student", True, f"Student registered with ID: {self.student_user_id}")
                else:
                    self.log_test("Register Student", False, "Role/email mismatch", data)
            else:
                self.log_test("Register Student", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Register Student", False, f"Exception: {str(e)}")

    def test_login_student(self):
        """Test 10: Login student"""
        payload = {
            "email": "student@example.com",
            "password": "student123"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.student_token = data["access_token"]
                self.log_test("Login Student", True, "Student login successful")
            else:
                self.log_test("Login Student", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Login Student", False, f"Exception: {str(e)}")

    def test_student_course_visibility(self):
        """Test 11: GET /api/courses (student - should see published/enrolled)"""
        if not self.student_token:
            self.log_test("Student Course Visibility", False, "No student token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(f"{self.base_url}/api/courses", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # Student should see fewer courses than instructor (only published ones)
                self.log_test("Student Course Visibility", True, f"Student sees {len(data)} courses")
            else:
                self.log_test("Student Course Visibility", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Student Course Visibility", False, f"Exception: {str(e)}")

    def test_enroll_course(self):
        """Test 12: POST /api/courses/{cid}/enroll"""
        if not self.student_token or not self.created_course_id:
            self.log_test("Enroll Course", False, "Missing student token or course ID")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.post(
                f"{self.base_url}/api/courses/{self.created_course_id}/enroll",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "enrolled":
                    self.log_test("Enroll Course", True, "Student enrolled successfully")
                else:
                    self.log_test("Enroll Course", False, "Unexpected enrollment response", data)
            else:
                self.log_test("Enroll Course", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Enroll Course", False, f"Exception: {str(e)}")

    def test_get_enrolled_course(self):
        """Test 13: GET /api/courses/{cid} (student accessing enrolled course)"""
        if not self.student_token or not self.created_course_id:
            self.log_test("Get Enrolled Course", False, "Missing student token or course ID")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(
                f"{self.base_url}/api/courses/{self.created_course_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("id") == self.created_course_id:
                    self.log_test("Get Enrolled Course", True, f"Student can access enrolled course: {data['title']}")
                else:
                    self.log_test("Get Enrolled Course", False, "Course ID mismatch", data)
            else:
                self.log_test("Get Enrolled Course", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Get Enrolled Course", False, f"Exception: {str(e)}")

    # ===== ASSIGNMENTS & SUBMISSIONS TESTS =====
    
    def test_create_assignment(self):
        """Test 14: POST /api/courses/{cid}/assignments"""
        if not self.instructor_token or not self.created_course_id:
            self.log_test("Create Assignment", False, "Missing instructor token or course ID")
            return
            
        payload = {
            "title": "Python OOP Exercise",
            "description": "Create a class hierarchy for a library management system",
            "rubric": ["Code structure and organization", "Proper use of inheritance", "Documentation quality"]
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.instructor_token}", "Content-Type": "application/json"}
            response = self.session.post(
                f"{self.base_url}/api/courses/{self.created_course_id}/assignments",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "course_id", "title", "description"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Create Assignment", False, f"Missing fields: {missing_fields}", data)
                    return
                
                self.assignment_id = data["id"]
                self.log_test("Create Assignment", True, f"Assignment created with ID: {self.assignment_id}")
            else:
                self.log_test("Create Assignment", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Create Assignment", False, f"Exception: {str(e)}")

    def test_list_assignments(self):
        """Test 15: GET /api/courses/{cid}/assignments"""
        if not self.student_token or not self.created_course_id:
            self.log_test("List Assignments", False, "Missing student token or course ID")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(
                f"{self.base_url}/api/courses/{self.created_course_id}/assignments",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    assignment_found = any(a.get("id") == self.assignment_id for a in data)
                    if assignment_found:
                        self.log_test("List Assignments", True, f"Found {len(data)} assignments including created one")
                    else:
                        self.log_test("List Assignments", False, "Created assignment not found in list", data)
                else:
                    self.log_test("List Assignments", False, "No assignments found", data)
            else:
                self.log_test("List Assignments", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("List Assignments", False, f"Exception: {str(e)}")

    def test_submit_assignment(self):
        """Test 16: POST /api/assignments/{aid}/submit (student)"""
        if not self.student_token or not self.assignment_id:
            self.log_test("Submit Assignment", False, "Missing student token or assignment ID")
            return
            
        payload = {
            "text_answer": "Here is my solution for the library management system:\n\nclass Book:\n    def __init__(self, title, author, isbn):\n        self.title = title\n        self.author = author\n        self.isbn = isbn\n        self.is_available = True\n\nclass Library:\n    def __init__(self):\n        self.books = []\n        self.members = []\n    \n    def add_book(self, book):\n        self.books.append(book)\n    \n    def find_book(self, isbn):\n        for book in self.books:\n            if book.isbn == isbn:\n                return book\n        return None\n\nThis implementation demonstrates proper OOP principles with encapsulation and clear method definitions."
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.student_token}", "Content-Type": "application/json"}
            response = self.session.post(
                f"{self.base_url}/api/assignments/{self.assignment_id}/submit",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "assignment_id", "user_id", "text_answer"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Submit Assignment", False, f"Missing fields: {missing_fields}", data)
                    return
                
                self.submission_id = data["id"]
                plagiarism_info = data.get("plagiarism", {})
                self.log_test("Submit Assignment", True, f"Assignment submitted with ID: {self.submission_id}, plagiarism score: {plagiarism_info.get('max_similarity', 'N/A')}")
            else:
                self.log_test("Submit Assignment", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Submit Assignment", False, f"Exception: {str(e)}")

    def test_ai_grade_assignment(self):
        """Test 17: POST /api/assignments/{aid}/grade/ai (instructor)"""
        if not self.instructor_token or not self.assignment_id:
            self.log_test("AI Grade Assignment", False, "Missing instructor token or assignment ID")
            return
            
        payload = {
            "additional_instructions": "Focus on code quality and adherence to OOP principles"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.instructor_token}", "Content-Type": "application/json"}
            response = self.session.post(
                f"{self.base_url}/api/assignments/{self.assignment_id}/grade/ai",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "graded":
                    self.log_test("AI Grade Assignment", True, f"AI grading completed for {data.get('count', 0)} submissions")
                else:
                    self.log_test("AI Grade Assignment", False, "Unexpected grading response", data)
            else:
                self.log_test("AI Grade Assignment", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("AI Grade Assignment", False, f"Exception: {str(e)}")

    # ===== FILES TESTS =====
    
    def test_upload_file(self):
        """Test 18: POST /api/files/upload"""
        if not self.student_token:
            self.log_test("Upload File", False, "No student token available")
            return
            
        # Create a small test file
        test_content = "This is a test file for the LMS system.\nIt contains sample content for testing file upload functionality."
        
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            files = {"file": ("test_document.txt", io.StringIO(test_content), "text/plain")}
            
            response = self.session.post(
                f"{self.base_url}/api/files/upload",
                files=files,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if "file_id" in data and "filename" in data:
                    self.file_id = data["file_id"]
                    self.log_test("Upload File", True, f"File uploaded with ID: {self.file_id}, filename: {data['filename']}")
                else:
                    self.log_test("Upload File", False, "Missing file_id or filename in response", data)
            else:
                self.log_test("Upload File", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Upload File", False, f"Exception: {str(e)}")

    def test_download_file(self):
        """Test 19: GET /api/files/{file_id}"""
        if not self.student_token or not self.file_id:
            self.log_test("Download File", False, "Missing student token or file ID")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(
                f"{self.base_url}/api/files/{self.file_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                # Check if we got file content
                if len(response.content) > 0:
                    self.log_test("Download File", True, f"File downloaded successfully, size: {len(response.content)} bytes")
                else:
                    self.log_test("Download File", False, "Empty file content received")
            else:
                self.log_test("Download File", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Download File", False, f"Exception: {str(e)}")

    # ===== Q&A CHAT TESTS =====
    
    def test_course_chat(self):
        """Test 20: POST /api/ai/chat (student)"""
        if not self.student_token or not self.created_course_id:
            self.log_test("Course Chat", False, "Missing student token or course ID")
            return
            
        payload = {
            "course_id": self.created_course_id,
            "session_id": "student-session-456",
            "message": "Can you explain the key concepts covered in this course?"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.student_token}", "Content-Type": "application/json"}
            response = self.session.post(
                f"{self.base_url}/api/ai/chat",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if "reply" in data and isinstance(data["reply"], str) and len(data["reply"]) > 0:
                    self.log_test("Course Chat", True, f"Chat response received: {data['reply'][:100]}...")
                else:
                    self.log_test("Course Chat", False, "Invalid chat response format", data)
            else:
                self.log_test("Course Chat", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Course Chat", False, f"Exception: {str(e)}")

    def test_chat_history(self):
        """Test 21: GET /api/chats/{course_id}/{session_id}"""
        if not self.student_token or not self.created_course_id:
            self.log_test("Chat History", False, "Missing student token or course ID")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(
                f"{self.base_url}/api/chats/{self.created_course_id}/student-session-456",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) >= 2:
                    user_msg = next((msg for msg in data if msg.get("role") == "user"), None)
                    assistant_msg = next((msg for msg in data if msg.get("role") == "assistant"), None)
                    
                    if user_msg and assistant_msg:
                        self.log_test("Chat History", True, f"Retrieved {len(data)} chat messages with proper roles")
                    else:
                        self.log_test("Chat History", False, "Missing user or assistant messages", data)
                else:
                    self.log_test("Chat History", False, f"Expected at least 2 messages, got {len(data) if isinstance(data, list) else 'non-list'}", data)
            else:
                self.log_test("Chat History", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Chat History", False, f"Exception: {str(e)}")

    # ===== DISCUSSIONS TESTS =====
    
    def test_create_thread(self):
        """Test 22: POST /api/courses/{cid}/threads"""
        if not self.student_token or not self.created_course_id:
            self.log_test("Create Thread", False, "Missing student token or course ID")
            return
            
        payload = {
            "title": "Question about Python Classes",
            "body": "I'm having trouble understanding the difference between class methods and instance methods. Can someone help explain?"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.student_token}", "Content-Type": "application/json"}
            response = self.session.post(
                f"{self.base_url}/api/courses/{self.created_course_id}/threads",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "course_id", "user_id", "title", "body"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Create Thread", False, f"Missing fields: {missing_fields}", data)
                    return
                
                self.thread_id = data["id"]
                self.log_test("Create Thread", True, f"Thread created with ID: {self.thread_id}")
            else:
                self.log_test("Create Thread", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Create Thread", False, f"Exception: {str(e)}")

    def test_list_threads(self):
        """Test 23: GET /api/courses/{cid}/threads"""
        if not self.student_token or not self.created_course_id:
            self.log_test("List Threads", False, "Missing student token or course ID")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(
                f"{self.base_url}/api/courses/{self.created_course_id}/threads",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    thread_found = any(t.get("id") == self.thread_id for t in data)
                    if thread_found:
                        self.log_test("List Threads", True, f"Found {len(data)} threads including created one")
                    else:
                        self.log_test("List Threads", False, "Created thread not found in list", data)
                else:
                    self.log_test("List Threads", False, "No threads found", data)
            else:
                self.log_test("List Threads", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("List Threads", False, f"Exception: {str(e)}")

    def test_add_post(self):
        """Test 24: POST /api/threads/{tid}/posts"""
        if not self.instructor_token or not self.thread_id:
            self.log_test("Add Post", False, "Missing instructor token or thread ID")
            return
            
        payload = {
            "body": "Great question! Class methods are bound to the class and can be called on the class itself, while instance methods are bound to specific instances of the class. Class methods use @classmethod decorator and take 'cls' as first parameter, while instance methods take 'self'."
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.instructor_token}", "Content-Type": "application/json"}
            response = self.session.post(
                f"{self.base_url}/api/threads/{self.thread_id}/posts",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "thread_id", "user_id", "body"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Add Post", False, f"Missing fields: {missing_fields}", data)
                    return
                
                self.log_test("Add Post", True, f"Post added with ID: {data['id']}")
            else:
                self.log_test("Add Post", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Add Post", False, f"Exception: {str(e)}")

    def test_list_posts(self):
        """Test 25: GET /api/threads/{tid}/posts"""
        if not self.student_token or not self.thread_id:
            self.log_test("List Posts", False, "Missing student token or thread ID")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(
                f"{self.base_url}/api/threads/{self.thread_id}/posts",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    self.log_test("List Posts", True, f"Found {len(data)} posts in thread")
                else:
                    self.log_test("List Posts", False, "No posts found in thread", data)
            else:
                self.log_test("List Posts", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("List Posts", False, f"Exception: {str(e)}")

    # ===== ANALYTICS TESTS =====
    
    def test_instructor_analytics(self):
        """Test 26: GET /api/analytics/instructor"""
        if not self.instructor_token:
            self.log_test("Instructor Analytics", False, "No instructor token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.instructor_token}"}
            response = self.session.get(f"{self.base_url}/api/analytics/instructor", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["courses", "students"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Instructor Analytics", False, f"Missing fields: {missing_fields}", data)
                    return
                
                self.log_test("Instructor Analytics", True, f"Analytics: {data['courses']} courses, {data['students']} students")
            else:
                self.log_test("Instructor Analytics", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Instructor Analytics", False, f"Exception: {str(e)}")

    def test_admin_analytics(self):
        """Test 27: GET /api/analytics/admin (first user is admin)"""
        if not self.instructor_token:  # First registered user should be admin
            self.log_test("Admin Analytics", False, "No instructor token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.instructor_token}"}
            response = self.session.get(f"{self.base_url}/api/analytics/admin", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["users", "courses", "submissions"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Admin Analytics", False, f"Missing fields: {missing_fields}", data)
                    return
                
                self.log_test("Admin Analytics", True, f"Admin analytics: {data['users']} users, {data['courses']} courses, {data['submissions']} submissions")
            else:
                self.log_test("Admin Analytics", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Admin Analytics", False, f"Exception: {str(e)}")

    def test_student_analytics(self):
        """Test 28: GET /api/analytics/student"""
        if not self.student_token:
            self.log_test("Student Analytics", False, "No student token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(f"{self.base_url}/api/analytics/student", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["enrolled_courses", "submissions"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Student Analytics", False, f"Missing fields: {missing_fields}", data)
                    return
                
                self.log_test("Student Analytics", True, f"Student analytics: {data['enrolled_courses']} enrolled courses, {data['submissions']} submissions")
            else:
                self.log_test("Student Analytics", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Student Analytics", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests in sequence"""
        print(f"🚀 Starting Expanded LMS Backend API Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 80)
        
        # Auth tests
        print("🔐 AUTHENTICATION TESTS")
        print("-" * 40)
        self.test_auth_register_instructor()
        self.test_auth_login_instructor()
        self.test_auth_me_instructor()
        self.test_auth_refresh()
        
        # Course & Lessons tests
        print("\n📚 COURSE & LESSONS TESTS")
        print("-" * 40)
        self.test_create_course()
        self.test_list_courses_instructor()
        self.test_add_lesson()
        self.test_ai_generate_course()
        
        # Student enrollment tests
        print("\n👨‍🎓 STUDENT ENROLLMENT TESTS")
        print("-" * 40)
        self.test_register_student()
        self.test_login_student()
        self.test_student_course_visibility()
        self.test_enroll_course()
        self.test_get_enrolled_course()
        
        # Assignments & Submissions tests
        print("\n📝 ASSIGNMENTS & SUBMISSIONS TESTS")
        print("-" * 40)
        self.test_create_assignment()
        self.test_list_assignments()
        self.test_submit_assignment()
        self.test_ai_grade_assignment()
        
        # Files tests
        print("\n📁 FILES TESTS")
        print("-" * 40)
        self.test_upload_file()
        self.test_download_file()
        
        # Q&A Chat tests
        print("\n💬 Q&A CHAT TESTS")
        print("-" * 40)
        self.test_course_chat()
        self.test_chat_history()
        
        # Discussions tests
        print("\n🗣️ DISCUSSIONS TESTS")
        print("-" * 40)
        self.test_create_thread()
        self.test_list_threads()
        self.test_add_post()
        self.test_list_posts()
        
        # Analytics tests
        print("\n📊 ANALYTICS TESTS")
        print("-" * 40)
        self.test_instructor_analytics()
        self.test_admin_analytics()
        self.test_student_analytics()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        return passed == total

def main():
    """Main test execution"""
    tester = BackendTester(BACKEND_URL)
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()