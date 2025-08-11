#!/usr/bin/env python3
import requests
import json

BACKEND_URL = "https://b73e20c6-764f-43c9-85dc-0258a2ed0875.preview.emergentagent.com"

# Login first
login_payload = {
    "email": "instructor@example.com",
    "password": "instructor123"
}

response = requests.post(f"{BACKEND_URL}/api/auth/login", json=login_payload)
print(f"Login status: {response.status_code}")
if response.status_code == 200:
    token = response.json()["access_token"]
    print("Got token")
    
    # Test list courses
    headers = {"Authorization": f"Bearer {token}"}
    courses_response = requests.get(f"{BACKEND_URL}/api/courses", headers=headers)
    print(f"List courses status: {courses_response.status_code}")
    if courses_response.status_code == 200:
        print(f"Courses: {courses_response.json()}")
    else:
        print(f"Error: {courses_response.text}")
else:
    print(f"Login failed: {response.text}")