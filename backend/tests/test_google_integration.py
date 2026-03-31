"""
Test Google OAuth Integration Endpoints for The Ile Ubuntu

Tests:
- GET /api/google/auth-url - Returns Google OAuth URL (requires auth)
- GET /api/google/status - Returns connection status (requires auth)
- DELETE /api/google/disconnect - Disconnects Google account (requires auth)
- GET /api/google/slides - Lists Google Slides (requires Google token)
- GET /api/google/docs - Lists Google Docs (requires Google token)
- POST /api/google/slides/{id}/import - Imports slide to lesson (requires Google token)
- POST /api/google/docs/{id}/import - Imports doc to lesson (requires Google token)
- GET /api/google/callback - Handles OAuth callback (exchanges code for tokens)

NOTE: Actual Google OAuth flow cannot be tested without real Google credentials.
We test API structure, auth requirements, and error handling.
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# MongoDB connection for test data setup
client = MongoClient(MONGO_URL)
db = client[DB_NAME]
users_col = db.users
sessions_col = db.sessions
courses_col = db.courses
lessons_col = db.lessons
google_tokens_col = db.google_tokens


class TestSetup:
    """Setup test users and sessions for Google integration tests"""
    
    @pytest.fixture(scope="class")
    def faculty_user(self):
        """Create a faculty user for testing"""
        user_id = f"GOOGLE_TEST_faculty_{uuid.uuid4().hex[:8]}"
        user_data = {
            "id": user_id,
            "email": f"{user_id}@test.com",
            "name": "Google Test Faculty",
            "picture": "https://example.com/pic.jpg",
            "role": "faculty",
            "bio": "",
            "created_at": datetime.now(timezone.utc),
        }
        users_col.insert_one(user_data)
        
        # Create session
        session_id = f"GOOGLE_TEST_session_{uuid.uuid4().hex[:8]}"
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "session_token": f"token_{uuid.uuid4().hex}",
            "expires_at": datetime.now(timezone.utc) + timedelta(days=7),  # Future expiration
        }
        sessions_col.insert_one(session_data)
        
        yield {"user": user_data, "session_id": session_id}
        
        # Cleanup
        users_col.delete_one({"id": user_id})
        sessions_col.delete_one({"session_id": session_id})
        google_tokens_col.delete_one({"user_id": user_id})
    
    @pytest.fixture(scope="class")
    def student_user(self):
        """Create a student user for testing"""
        user_id = f"GOOGLE_TEST_student_{uuid.uuid4().hex[:8]}"
        user_data = {
            "id": user_id,
            "email": f"{user_id}@test.com",
            "name": "Google Test Student",
            "picture": "https://example.com/pic.jpg",
            "role": "student",
            "bio": "",
            "created_at": datetime.now(timezone.utc),
        }
        users_col.insert_one(user_data)
        
        # Create session
        session_id = f"GOOGLE_TEST_session_{uuid.uuid4().hex[:8]}"
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "session_token": f"token_{uuid.uuid4().hex}",
            "expires_at": datetime.now(timezone.utc) + timedelta(days=7),  # Future expiration
        }
        sessions_col.insert_one(session_data)
        
        yield {"user": user_data, "session_id": session_id}
        
        # Cleanup
        users_col.delete_one({"id": user_id})
        sessions_col.delete_one({"session_id": session_id})
    
    @pytest.fixture(scope="class")
    def test_course_and_lesson(self, faculty_user):
        """Create a test course and lesson for import tests"""
        course_id = f"GOOGLE_TEST_course_{uuid.uuid4().hex[:8]}"
        course_data = {
            "id": course_id,
            "title": "Google Test Course",
            "description": "Course for testing Google imports",
            "instructor_id": faculty_user["user"]["id"],
            "instructor_name": faculty_user["user"]["name"],
            "status": "active",
            "tags": [],
            "enrolled_count": 0,
            "created_at": datetime.now(timezone.utc),
        }
        courses_col.insert_one(course_data)
        
        lesson_id = f"GOOGLE_TEST_lesson_{uuid.uuid4().hex[:8]}"
        lesson_data = {
            "id": lesson_id,
            "course_id": course_id,
            "title": "Google Test Lesson",
            "description": "Lesson for testing Google imports",
            "content": "",
            "order": 1,
            "google_resources": [],
            "created_at": datetime.now(timezone.utc),
        }
        lessons_col.insert_one(lesson_data)
        
        yield {"course_id": course_id, "lesson_id": lesson_id}
        
        # Cleanup
        courses_col.delete_one({"id": course_id})
        lessons_col.delete_one({"id": lesson_id})


class TestGoogleAuthEndpoints(TestSetup):
    """Test Google OAuth authentication endpoints"""
    
    def test_auth_url_requires_auth(self):
        """GET /api/google/auth-url should require authentication"""
        response = requests.get(f"{BASE_URL}/api/google/auth-url")
        assert response.status_code == 401
        data = response.json()
        assert "Session ID required" in data.get("detail", "")
        print("PASSED: auth-url requires authentication")
    
    def test_auth_url_returns_google_oauth_url(self, faculty_user):
        """GET /api/google/auth-url should return valid Google OAuth URL"""
        headers = {"X-Session-ID": faculty_user["session_id"]}
        response = requests.get(f"{BASE_URL}/api/google/auth-url", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "auth_url" in data
        assert "redirect_uri" in data
        
        # Verify auth_url contains Google OAuth endpoint
        assert "accounts.google.com/o/oauth2" in data["auth_url"]
        
        # Verify required OAuth parameters
        assert "client_id=" in data["auth_url"]
        assert "redirect_uri=" in data["auth_url"]
        assert "scope=" in data["auth_url"]
        assert "response_type=code" in data["auth_url"]
        assert "access_type=offline" in data["auth_url"]
        assert "state=" in data["auth_url"]  # Contains user_id
        
        # Verify redirect_uri points to callback
        assert "/api/google/callback" in data["redirect_uri"]
        
        print(f"PASSED: auth-url returns valid Google OAuth URL")
        print(f"  - auth_url contains accounts.google.com/o/oauth2")
        print(f"  - redirect_uri: {data['redirect_uri']}")
    
    def test_status_requires_auth(self):
        """GET /api/google/status should require authentication"""
        response = requests.get(f"{BASE_URL}/api/google/status")
        assert response.status_code == 401
        print("PASSED: status requires authentication")
    
    def test_status_returns_not_connected_by_default(self, faculty_user):
        """GET /api/google/status should return connected=false for new users"""
        headers = {"X-Session-ID": faculty_user["session_id"]}
        response = requests.get(f"{BASE_URL}/api/google/status", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "connected" in data
        assert data["connected"] == False
        
        print("PASSED: status returns connected=false for new users")
    
    def test_disconnect_requires_auth(self):
        """DELETE /api/google/disconnect should require authentication"""
        response = requests.delete(f"{BASE_URL}/api/google/disconnect")
        assert response.status_code == 401
        print("PASSED: disconnect requires authentication")
    
    def test_disconnect_succeeds_even_when_not_connected(self, faculty_user):
        """DELETE /api/google/disconnect should succeed even if not connected"""
        headers = {"X-Session-ID": faculty_user["session_id"]}
        response = requests.delete(f"{BASE_URL}/api/google/disconnect", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        
        print("PASSED: disconnect succeeds even when not connected")


class TestGoogleCallbackEndpoint(TestSetup):
    """Test Google OAuth callback endpoint"""
    
    def test_callback_with_error_redirects(self):
        """GET /api/google/callback with error should redirect with error"""
        response = requests.get(
            f"{BASE_URL}/api/google/callback",
            params={"error": "access_denied"},
            allow_redirects=False
        )
        # Should redirect (302 or 307)
        assert response.status_code in [302, 307]
        
        # Check redirect location contains error
        location = response.headers.get("location", "")
        assert "google_error=access_denied" in location
        
        print("PASSED: callback with error redirects with error parameter")
    
    def test_callback_without_code_redirects_with_error(self):
        """GET /api/google/callback without code should redirect with error"""
        response = requests.get(
            f"{BASE_URL}/api/google/callback",
            allow_redirects=False
        )
        assert response.status_code in [302, 307]
        
        location = response.headers.get("location", "")
        assert "google_error=no_code" in location
        
        print("PASSED: callback without code redirects with no_code error")
    
    def test_callback_with_invalid_code_redirects_with_error(self, faculty_user):
        """GET /api/google/callback with invalid code should redirect with error"""
        response = requests.get(
            f"{BASE_URL}/api/google/callback",
            params={
                "code": "invalid_code_12345",
                "state": faculty_user["user"]["id"]
            },
            allow_redirects=False
        )
        # Should redirect with error (Google will reject invalid code)
        assert response.status_code in [302, 307]
        
        location = response.headers.get("location", "")
        assert "google_error" in location
        
        print("PASSED: callback with invalid code redirects with error")


class TestGoogleSlidesEndpoints(TestSetup):
    """Test Google Slides listing and import endpoints"""
    
    def test_slides_requires_auth(self):
        """GET /api/google/slides should require authentication"""
        response = requests.get(f"{BASE_URL}/api/google/slides")
        assert response.status_code == 401
        print("PASSED: slides requires authentication")
    
    def test_slides_requires_google_connection(self, faculty_user):
        """GET /api/google/slides should return 400 if Google not connected"""
        headers = {"X-Session-ID": faculty_user["session_id"]}
        response = requests.get(f"{BASE_URL}/api/google/slides", headers=headers)
        
        # Should return 400 with "Google account not connected"
        assert response.status_code == 400
        data = response.json()
        assert "Google account not connected" in data.get("detail", "")
        
        print("PASSED: slides returns 400 when Google not connected")
    
    def test_import_slide_requires_auth(self):
        """POST /api/google/slides/{id}/import should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/google/slides/test_slide_id/import",
            json={"lesson_id": "test_lesson"}
        )
        assert response.status_code == 401
        print("PASSED: import slide requires authentication")
    
    def test_import_slide_requires_google_connection(self, faculty_user, test_course_and_lesson):
        """POST /api/google/slides/{id}/import should return 400 if Google not connected"""
        headers = {"X-Session-ID": faculty_user["session_id"]}
        response = requests.post(
            f"{BASE_URL}/api/google/slides/test_slide_id/import",
            headers=headers,
            json={
                "lesson_id": test_course_and_lesson["lesson_id"],
                "course_id": test_course_and_lesson["course_id"]
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Google account not connected" in data.get("detail", "")
        
        print("PASSED: import slide returns 400 when Google not connected")
    
    def test_import_slide_requires_faculty_role(self, student_user):
        """POST /api/google/slides/{id}/import should require faculty+ role"""
        # First, mock a Google token for the student
        google_tokens_col.insert_one({
            "user_id": student_user["user"]["id"],
            "access_token": "mock_token",
            "refresh_token": "mock_refresh",
        })
        
        try:
            headers = {"X-Session-ID": student_user["session_id"]}
            response = requests.post(
                f"{BASE_URL}/api/google/slides/test_slide_id/import",
                headers=headers,
                json={"lesson_id": "test_lesson"}
            )
            
            # Should return 403 for students
            assert response.status_code == 403
            data = response.json()
            assert "faculty" in data.get("detail", "").lower()
            
            print("PASSED: import slide requires faculty+ role")
        finally:
            google_tokens_col.delete_one({"user_id": student_user["user"]["id"]})


class TestGoogleDocsEndpoints(TestSetup):
    """Test Google Docs listing and import endpoints"""
    
    def test_docs_requires_auth(self):
        """GET /api/google/docs should require authentication"""
        response = requests.get(f"{BASE_URL}/api/google/docs")
        assert response.status_code == 401
        print("PASSED: docs requires authentication")
    
    def test_docs_requires_google_connection(self, faculty_user):
        """GET /api/google/docs should return 400 if Google not connected"""
        headers = {"X-Session-ID": faculty_user["session_id"]}
        response = requests.get(f"{BASE_URL}/api/google/docs", headers=headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "Google account not connected" in data.get("detail", "")
        
        print("PASSED: docs returns 400 when Google not connected")
    
    def test_import_doc_requires_auth(self):
        """POST /api/google/docs/{id}/import should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/google/docs/test_doc_id/import",
            json={"lesson_id": "test_lesson"}
        )
        assert response.status_code == 401
        print("PASSED: import doc requires authentication")
    
    def test_import_doc_requires_google_connection(self, faculty_user, test_course_and_lesson):
        """POST /api/google/docs/{id}/import should return 400 if Google not connected"""
        headers = {"X-Session-ID": faculty_user["session_id"]}
        response = requests.post(
            f"{BASE_URL}/api/google/docs/test_doc_id/import",
            headers=headers,
            json={
                "lesson_id": test_course_and_lesson["lesson_id"],
                "course_id": test_course_and_lesson["course_id"]
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Google account not connected" in data.get("detail", "")
        
        print("PASSED: import doc returns 400 when Google not connected")
    
    def test_import_doc_requires_faculty_role(self, student_user):
        """POST /api/google/docs/{id}/import should require faculty+ role"""
        # First, mock a Google token for the student
        google_tokens_col.insert_one({
            "user_id": student_user["user"]["id"],
            "access_token": "mock_token",
            "refresh_token": "mock_refresh",
        })
        
        try:
            headers = {"X-Session-ID": student_user["session_id"]}
            response = requests.post(
                f"{BASE_URL}/api/google/docs/test_doc_id/import",
                headers=headers,
                json={"lesson_id": "test_lesson"}
            )
            
            # Should return 403 for students
            assert response.status_code == 403
            data = response.json()
            assert "faculty" in data.get("detail", "").lower()
            
            print("PASSED: import doc requires faculty+ role")
        finally:
            google_tokens_col.delete_one({"user_id": student_user["user"]["id"]})


class TestGoogleConnectionStatus(TestSetup):
    """Test Google connection status with mocked tokens"""
    
    def test_status_returns_connected_when_token_exists(self, faculty_user):
        """GET /api/google/status should return connected=true when token exists"""
        # Insert a mock Google token
        google_tokens_col.insert_one({
            "user_id": faculty_user["user"]["id"],
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "connected_at": datetime.now(timezone.utc),
        })
        
        try:
            headers = {"X-Session-ID": faculty_user["session_id"]}
            response = requests.get(f"{BASE_URL}/api/google/status", headers=headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["connected"] == True
            
            print("PASSED: status returns connected=true when token exists")
        finally:
            google_tokens_col.delete_one({"user_id": faculty_user["user"]["id"]})
    
    def test_disconnect_removes_token(self, faculty_user):
        """DELETE /api/google/disconnect should remove the token"""
        # Insert a mock Google token
        google_tokens_col.insert_one({
            "user_id": faculty_user["user"]["id"],
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
        })
        
        headers = {"X-Session-ID": faculty_user["session_id"]}
        
        # Verify connected
        status_response = requests.get(f"{BASE_URL}/api/google/status", headers=headers)
        assert status_response.json()["connected"] == True
        
        # Disconnect
        disconnect_response = requests.delete(f"{BASE_URL}/api/google/disconnect", headers=headers)
        assert disconnect_response.status_code == 200
        assert disconnect_response.json()["success"] == True
        
        # Verify disconnected
        status_response = requests.get(f"{BASE_URL}/api/google/status", headers=headers)
        assert status_response.json()["connected"] == False
        
        print("PASSED: disconnect removes token and status shows disconnected")


class TestRegressionFileAttachments(TestSetup):
    """Regression tests for file attachments (from iteration 5)"""
    
    def test_file_upload_endpoint_exists(self, faculty_user, test_course_and_lesson):
        """POST /api/files/upload should exist and require auth"""
        # Without auth
        response = requests.post(f"{BASE_URL}/api/files/upload")
        assert response.status_code == 401
        print("PASSED: file upload endpoint exists and requires auth")
    
    def test_file_list_endpoint_exists(self, faculty_user, test_course_and_lesson):
        """GET /api/files should exist and require auth"""
        # Without auth
        response = requests.get(f"{BASE_URL}/api/files")
        assert response.status_code == 401
        
        # With auth
        headers = {"X-Session-ID": faculty_user["session_id"]}
        response = requests.get(
            f"{BASE_URL}/api/files",
            headers=headers,
            params={"course_id": test_course_and_lesson["course_id"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        
        print("PASSED: file list endpoint works")


class TestRegressionLessonCreation(TestSetup):
    """Regression tests for lesson creation (from iteration 5)"""
    
    def test_lesson_creation_endpoint_exists(self, faculty_user, test_course_and_lesson):
        """POST /api/courses/{id}/lessons should exist"""
        headers = {"X-Session-ID": faculty_user["session_id"]}
        
        lesson_data = {
            "title": "GOOGLE_TEST_Regression_Lesson",
            "description": "Testing lesson creation regression",
            "content": "Test content",
            "order": 99
        }
        
        response = requests.post(
            f"{BASE_URL}/api/courses/{test_course_and_lesson['course_id']}/lessons",
            headers=headers,
            json=lesson_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("title") == lesson_data["title"]
        
        # Cleanup
        if "id" in data:
            lessons_col.delete_one({"id": data["id"]})
        
        print("PASSED: lesson creation endpoint works")


class TestCleanup:
    """Cleanup any remaining test data"""
    
    def test_cleanup_test_data(self):
        """Clean up all GOOGLE_TEST_ prefixed data"""
        # Clean up users
        users_deleted = users_col.delete_many({"id": {"$regex": "^GOOGLE_TEST_"}})
        print(f"Cleaned up {users_deleted.deleted_count} test users")
        
        # Clean up sessions
        sessions_deleted = sessions_col.delete_many({"session_id": {"$regex": "^GOOGLE_TEST_"}})
        print(f"Cleaned up {sessions_deleted.deleted_count} test sessions")
        
        # Clean up courses
        courses_deleted = courses_col.delete_many({"id": {"$regex": "^GOOGLE_TEST_"}})
        print(f"Cleaned up {courses_deleted.deleted_count} test courses")
        
        # Clean up lessons
        lessons_deleted = lessons_col.delete_many({"id": {"$regex": "^GOOGLE_TEST_"}})
        print(f"Cleaned up {lessons_deleted.deleted_count} test lessons")
        
        # Clean up google tokens
        tokens_deleted = google_tokens_col.delete_many({"user_id": {"$regex": "^GOOGLE_TEST_"}})
        print(f"Cleaned up {tokens_deleted.deleted_count} test google tokens")
        
        print("PASSED: Test data cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
