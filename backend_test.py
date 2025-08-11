#!/usr/bin/env python3
"""
Backend API Testing Script for AI Course Generator
Tests all backend endpoints according to the review request.
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BACKEND_URL = "https://b73e20c6-764f-43c9-85dc-0258a2ed0875.preview.emergentagent.com"

class BackendTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.created_course_id = None
        
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
    
    def test_health_endpoint(self):
        """Test 1: Health check - GET /api/"""
        try:
            response = self.session.get(f"{self.base_url}/api/")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("message") == "Hello World":
                    self.log_test("Health Check", True, "Endpoint returned correct message")
                else:
                    self.log_test("Health Check", False, f"Expected 'Hello World', got: {data}", data)
            else:
                self.log_test("Health Check", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")
    
    def test_generate_course(self):
        """Test 2: Generate Course - POST /api/ai/generate_course"""
        payload = {
            "topic": "Introduction to Prompt Engineering",
            "audience": "Beginners",
            "difficulty": "beginner",
            "lessons_count": 4
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/ai/generate_course",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                required_fields = ["id", "topic", "audience", "difficulty", "lessons_count", "lessons", "quiz"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Generate Course", False, f"Missing fields: {missing_fields}", data)
                    return
                
                # Validate lessons count
                if data["lessons_count"] != 4:
                    self.log_test("Generate Course", False, f"Expected 4 lessons, got: {data['lessons_count']}", data)
                    return
                
                # Validate lessons array
                if len(data["lessons"]) != 4:
                    self.log_test("Generate Course", False, f"Expected 4 lessons in array, got: {len(data['lessons'])}", data)
                    return
                
                # Store course ID for later tests
                self.created_course_id = data["id"]
                
                self.log_test("Generate Course", True, f"Course created with ID: {self.created_course_id}, {len(data['lessons'])} lessons, {len(data['quiz'])} quiz questions")
                
            else:
                self.log_test("Generate Course", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Generate Course", False, f"Exception: {str(e)}")
    
    def test_list_courses(self):
        """Test 3: List Courses - GET /api/courses"""
        try:
            response = self.session.get(f"{self.base_url}/api/courses")
            
            if response.status_code == 200:
                data = response.json()
                
                if not isinstance(data, list):
                    self.log_test("List Courses", False, "Response is not a list", data)
                    return
                
                # Check if our created course is in the list
                if self.created_course_id:
                    course_found = any(course.get("id") == self.created_course_id for course in data)
                    if course_found:
                        self.log_test("List Courses", True, f"Found {len(data)} courses, including our created course")
                    else:
                        self.log_test("List Courses", False, f"Created course ID {self.created_course_id} not found in list", data)
                else:
                    self.log_test("List Courses", True, f"Retrieved {len(data)} courses (no specific course to verify)")
                    
            else:
                self.log_test("List Courses", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("List Courses", False, f"Exception: {str(e)}")
    
    def test_get_course(self):
        """Test 4: Get Course - GET /api/courses/{id}"""
        if not self.created_course_id:
            self.log_test("Get Course", False, "No course ID available from previous test")
            return
            
        try:
            response = self.session.get(f"{self.base_url}/api/courses/{self.created_course_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                required_fields = ["id", "topic", "audience", "difficulty", "lessons_count", "lessons", "quiz"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Get Course", False, f"Missing fields: {missing_fields}", data)
                    return
                
                if data["id"] == self.created_course_id:
                    self.log_test("Get Course", True, f"Successfully retrieved course: {data['topic']}")
                else:
                    self.log_test("Get Course", False, f"ID mismatch: expected {self.created_course_id}, got {data['id']}", data)
                    
            elif response.status_code == 404:
                self.log_test("Get Course", False, "Course not found (404)", response.text)
            else:
                self.log_test("Get Course", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Get Course", False, f"Exception: {str(e)}")
    
    def test_chat(self):
        """Test 5: Chat - POST /api/ai/chat"""
        if not self.created_course_id:
            self.log_test("Chat", False, "No course ID available from previous test")
            return
            
        payload = {
            "course_id": self.created_course_id,
            "session_id": "test-session-123",
            "message": "Give me a quick summary of the course"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/ai/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "reply" in data and isinstance(data["reply"], str) and len(data["reply"]) > 0:
                    self.log_test("Chat", True, f"Received chat response: {data['reply'][:100]}...")
                else:
                    self.log_test("Chat", False, "Invalid chat response format", data)
                    
            elif response.status_code == 404:
                self.log_test("Chat", False, "Course not found for chat (404)", response.text)
            else:
                self.log_test("Chat", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Chat", False, f"Exception: {str(e)}")
    
    def test_chat_history(self):
        """Test 6: Chat History - GET /api/chats/{course_id}/{session_id}"""
        if not self.created_course_id:
            self.log_test("Chat History", False, "No course ID available from previous test")
            return
            
        try:
            response = self.session.get(f"{self.base_url}/api/chats/{self.created_course_id}/test-session-123")
            
            if response.status_code == 200:
                data = response.json()
                
                if not isinstance(data, list):
                    self.log_test("Chat History", False, "Response is not a list", data)
                    return
                
                # Should have at least 2 messages (user + assistant) from previous chat test
                if len(data) >= 2:
                    # Verify message structure
                    user_msg = next((msg for msg in data if msg.get("role") == "user"), None)
                    assistant_msg = next((msg for msg in data if msg.get("role") == "assistant"), None)
                    
                    if user_msg and assistant_msg:
                        self.log_test("Chat History", True, f"Retrieved {len(data)} messages with user and assistant roles")
                    else:
                        self.log_test("Chat History", False, f"Missing user or assistant messages in history", data)
                else:
                    self.log_test("Chat History", False, f"Expected at least 2 messages, got {len(data)}", data)
                    
            else:
                self.log_test("Chat History", False, f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Chat History", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend tests in sequence"""
        print(f"🚀 Starting Backend API Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Run tests in order
        self.test_health_endpoint()
        self.test_generate_course()
        self.test_list_courses()
        self.test_get_course()
        self.test_chat()
        self.test_chat_history()
        
        # Summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
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