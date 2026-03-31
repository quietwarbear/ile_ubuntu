"""
Test suite for File Attachments feature
Tests file upload, download, list, and delete operations for course lessons
"""
import pytest
import requests
import os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import uuid
import io

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# MongoDB connection for test data setup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

client = MongoClient(MONGO_URL)
db = client[DB_NAME]


class TestFileAttachmentsSetup:
    """Setup test users, courses, and lessons for file attachment testing"""
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_test_data(self, request):
        """Create test users, courses, and lessons before tests run"""
        # Create test users
        faculty_id = f"TEST_FILE_faculty_{uuid.uuid4().hex[:8]}"
        student_id = f"TEST_FILE_student_{uuid.uuid4().hex[:8]}"
        
        # Faculty user
        faculty_user = {
            "id": faculty_id,
            "email": f"test_file_faculty_{uuid.uuid4().hex[:6]}@test.com",
            "name": "Test File Faculty",
            "role": "faculty",
            "picture": "",
            "created_at": datetime.now(timezone.utc)
        }
        
        # Student user
        student_user = {
            "id": student_id,
            "email": f"test_file_student_{uuid.uuid4().hex[:6]}@test.com",
            "name": "Test File Student",
            "role": "student",
            "picture": "",
            "created_at": datetime.now(timezone.utc)
        }
        
        # Insert users
        db.users.insert_many([faculty_user, student_user])
        
        # Create sessions for each user
        faculty_session_id = f"TEST_FILE_session_{uuid.uuid4().hex}"
        student_session_id = f"TEST_FILE_session_{uuid.uuid4().hex}"
        
        sessions = [
            {
                "session_id": faculty_session_id,
                "user_id": faculty_id,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=7)
            },
            {
                "session_id": student_session_id,
                "user_id": student_id,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=7)
            }
        ]
        db.sessions.insert_many(sessions)
        
        # Create a test course
        course_id = f"TEST_FILE_course_{uuid.uuid4().hex[:8]}"
        course = {
            "id": course_id,
            "title": "TEST_FILE Course for Attachments",
            "description": "Test course for file attachment testing",
            "instructor_id": faculty_id,
            "instructor_name": "Test File Faculty",
            "status": "active",
            "tags": [],
            "lessons": [],
            "enrolled_count": 0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        db.courses.insert_one(course)
        
        # Create a test lesson
        lesson_id = f"TEST_FILE_lesson_{uuid.uuid4().hex[:8]}"
        lesson = {
            "id": lesson_id,
            "course_id": course_id,
            "title": "TEST_FILE Lesson 1",
            "description": "Test lesson for file attachments",
            "content": "This is the lesson content",
            "order": 1,
            "files": [],
            "created_by": faculty_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        db.lessons.insert_one(lesson)
        
        # Update course with lesson
        db.courses.update_one({"id": course_id}, {"$push": {"lessons": lesson_id}})
        
        # Store IDs for tests
        request.cls.faculty_id = faculty_id
        request.cls.student_id = student_id
        request.cls.faculty_session_id = faculty_session_id
        request.cls.student_session_id = student_session_id
        request.cls.course_id = course_id
        request.cls.lesson_id = lesson_id
        request.cls.uploaded_file_ids = []
        
        yield
        
        # Cleanup after all tests
        db.users.delete_many({"id": {"$regex": "^TEST_FILE_"}})
        db.sessions.delete_many({"session_id": {"$regex": "^TEST_FILE_"}})
        db.courses.delete_many({"id": {"$regex": "^TEST_FILE_"}})
        db.lessons.delete_many({"id": {"$regex": "^TEST_FILE_"}})
        db.files.delete_many({"course_id": {"$regex": "^TEST_FILE_"}})


@pytest.mark.usefixtures("setup_test_data")
class TestFileUpload(TestFileAttachmentsSetup):
    """Test file upload functionality"""
    
    def test_faculty_can_upload_txt_file(self):
        """Faculty can upload a text file to a lesson"""
        # Create a test file
        file_content = b"This is a test file content for testing file uploads."
        files = {
            'file': ('test_document.txt', io.BytesIO(file_content), 'text/plain')
        }
        data = {
            'lesson_id': self.lesson_id,
            'course_id': self.course_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/files/upload",
            files=files,
            data=data,
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        assert result["success"] == True
        assert "file" in result
        assert result["file"]["original_filename"] == "test_document.txt"
        assert result["file"]["mime_type"] == "text/plain"
        assert result["file"]["lesson_id"] == self.lesson_id
        assert result["file"]["course_id"] == self.course_id
        assert "download_url" in result
        
        # Store file ID for later tests
        self.__class__.uploaded_file_ids.append(result["file"]["id"])
        self.__class__.test_file_id = result["file"]["id"]
    
    def test_upload_requires_auth(self):
        """Upload without auth returns 401/403"""
        file_content = b"Test content"
        files = {
            'file': ('test.txt', io.BytesIO(file_content), 'text/plain')
        }
        data = {
            'lesson_id': self.lesson_id,
            'course_id': self.course_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/files/upload",
            files=files,
            data=data
            # No auth header
        )
        
        assert response.status_code in [401, 403, 422], f"Expected 401/403/422, got {response.status_code}"
    
    def test_upload_invalid_file_type(self):
        """Upload of invalid file type returns 400"""
        file_content = b"#!/bin/bash\necho 'test'"
        files = {
            'file': ('test.sh', io.BytesIO(file_content), 'application/x-sh')
        }
        data = {
            'lesson_id': self.lesson_id,
            'course_id': self.course_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/files/upload",
            files=files,
            data=data,
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "not allowed" in response.json()["detail"].lower()


@pytest.mark.usefixtures("setup_test_data")
class TestFileList(TestFileAttachmentsSetup):
    """Test file listing functionality"""
    
    @pytest.fixture(autouse=True)
    def ensure_file_exists(self):
        """Ensure at least one file exists for listing tests"""
        # Upload a file if none exists
        file_content = b"Test file for listing"
        files = {
            'file': ('list_test.txt', io.BytesIO(file_content), 'text/plain')
        }
        data = {
            'lesson_id': self.lesson_id,
            'course_id': self.course_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/files/upload",
            files=files,
            data=data,
            headers={"X-Session-ID": self.faculty_session_id}
        )
        if response.status_code == 200:
            self.list_test_file_id = response.json()["file"]["id"]
            self.__class__.uploaded_file_ids.append(self.list_test_file_id)
        yield
    
    def test_list_files_by_course_id(self):
        """List all files for a course"""
        response = requests.get(
            f"{BASE_URL}/api/files?course_id={self.course_id}",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        assert "files" in result
        assert isinstance(result["files"], list)
        assert len(result["files"]) > 0
        
        # Verify file structure
        for f in result["files"]:
            assert "id" in f
            assert "original_filename" in f
            assert "file_size" in f
            assert "mime_type" in f
            assert "download_url" in f
    
    def test_list_files_by_lesson_id(self):
        """List files for a specific lesson"""
        response = requests.get(
            f"{BASE_URL}/api/files?lesson_id={self.lesson_id}",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        assert "files" in result
        assert isinstance(result["files"], list)
        
        # All files should belong to the lesson
        for f in result["files"]:
            assert f["lesson_id"] == self.lesson_id
    
    def test_list_files_requires_auth(self):
        """List files without auth returns 401/403"""
        response = requests.get(
            f"{BASE_URL}/api/files?course_id={self.course_id}"
            # No auth header
        )
        
        assert response.status_code in [401, 403, 422], f"Expected 401/403/422, got {response.status_code}"


@pytest.mark.usefixtures("setup_test_data")
class TestFileDownload(TestFileAttachmentsSetup):
    """Test file download functionality - PUBLIC access"""
    
    @pytest.fixture(autouse=True)
    def ensure_download_file_exists(self):
        """Ensure a file exists for download tests"""
        file_content = b"Download test content - this should be downloadable without auth"
        files = {
            'file': ('download_test.txt', io.BytesIO(file_content), 'text/plain')
        }
        data = {
            'lesson_id': self.lesson_id,
            'course_id': self.course_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/files/upload",
            files=files,
            data=data,
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 200, f"Failed to upload test file: {response.text}"
        self.download_test_file_id = response.json()["file"]["id"]
        self.__class__.uploaded_file_ids.append(self.download_test_file_id)
        yield
    
    def test_download_file_without_auth(self):
        """Download file works without authentication (public link)"""
        response = requests.get(
            f"{BASE_URL}/api/files/{self.download_test_file_id}/download"
            # No auth header - should still work
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert b"Download test content" in response.content
        assert "text/plain" in response.headers.get("content-type", "")
    
    def test_download_file_with_auth(self):
        """Download file also works with authentication"""
        response = requests.get(
            f"{BASE_URL}/api/files/{self.download_test_file_id}/download",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert b"Download test content" in response.content
    
    def test_download_nonexistent_file(self):
        """Download nonexistent file returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/files/nonexistent-file-id-12345/download"
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


@pytest.mark.usefixtures("setup_test_data")
class TestFileDelete(TestFileAttachmentsSetup):
    """Test file deletion functionality"""
    
    def test_owner_can_delete_file(self):
        """File owner can delete their file"""
        # First upload a file
        file_content = b"File to be deleted"
        files = {
            'file': ('delete_test.txt', io.BytesIO(file_content), 'text/plain')
        }
        data = {
            'lesson_id': self.lesson_id,
            'course_id': self.course_id
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/api/files/upload",
            files=files,
            data=data,
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file"]["id"]
        
        # Delete the file
        delete_response = requests.delete(
            f"{BASE_URL}/api/files/{file_id}",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"
        assert delete_response.json()["success"] == True
        
        # Verify file is gone
        download_response = requests.get(
            f"{BASE_URL}/api/files/{file_id}/download"
        )
        assert download_response.status_code == 404
    
    def test_non_owner_cannot_delete_file(self):
        """Non-owner cannot delete someone else's file"""
        # First upload a file as faculty
        file_content = b"File owned by faculty"
        files = {
            'file': ('faculty_file.txt', io.BytesIO(file_content), 'text/plain')
        }
        data = {
            'lesson_id': self.lesson_id,
            'course_id': self.course_id
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/api/files/upload",
            files=files,
            data=data,
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file"]["id"]
        self.__class__.uploaded_file_ids.append(file_id)
        
        # Student tries to delete
        delete_response = requests.delete(
            f"{BASE_URL}/api/files/{file_id}",
            headers={"X-Session-ID": self.student_session_id}
        )
        
        assert delete_response.status_code == 403, f"Expected 403, got {delete_response.status_code}: {delete_response.text}"
    
    def test_delete_requires_auth(self):
        """Delete without auth returns 401/403"""
        # Use any file ID
        response = requests.delete(
            f"{BASE_URL}/api/files/some-file-id"
            # No auth header
        )
        
        assert response.status_code in [401, 403, 422], f"Expected 401/403/422, got {response.status_code}"
    
    def test_delete_nonexistent_file(self):
        """Delete nonexistent file returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/files/nonexistent-file-id-12345",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


@pytest.mark.usefixtures("setup_test_data")
class TestLessonCreation(TestFileAttachmentsSetup):
    """Test lesson creation from course detail page"""
    
    def test_instructor_can_create_lesson(self):
        """Course instructor can create a lesson"""
        response = requests.post(
            f"{BASE_URL}/api/courses/{self.course_id}/lessons",
            json={
                "title": "TEST_FILE New Lesson",
                "description": "A new lesson created via API",
                "content": "This is the lesson content with instructions.",
                "order": 2
            },
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        assert result["title"] == "TEST_FILE New Lesson"
        assert result["description"] == "A new lesson created via API"
        assert result["content"] == "This is the lesson content with instructions."
        assert result["course_id"] == self.course_id
        assert "id" in result
        
        # Store for cleanup
        self.__class__.created_lesson_id = result["id"]
    
    def test_student_cannot_create_lesson(self):
        """Student cannot create a lesson (403)"""
        response = requests.post(
            f"{BASE_URL}/api/courses/{self.course_id}/lessons",
            json={
                "title": "TEST_FILE Student Lesson",
                "description": "Should fail"
            },
            headers={"X-Session-ID": self.student_session_id}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
    
    def test_list_lessons_for_course(self):
        """List all lessons for a course"""
        response = requests.get(
            f"{BASE_URL}/api/courses/{self.course_id}/lessons",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        assert isinstance(result, list)
        assert len(result) >= 1  # At least our initial lesson
        
        # Verify lesson structure
        for lesson in result:
            assert "id" in lesson
            assert "title" in lesson
            assert "course_id" in lesson
            assert lesson["course_id"] == self.course_id


class TestFileAttachmentsCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self):
        """Clean up all test data"""
        # Delete test files
        result = db.files.delete_many({"course_id": {"$regex": "^TEST_FILE_"}})
        print(f"Deleted {result.deleted_count} test files")
        
        # Delete test lessons
        result = db.lessons.delete_many({"id": {"$regex": "^TEST_FILE_"}})
        print(f"Deleted {result.deleted_count} test lessons")
        
        # Delete test courses
        result = db.courses.delete_many({"id": {"$regex": "^TEST_FILE_"}})
        print(f"Deleted {result.deleted_count} test courses")
        
        # Delete test users
        result = db.users.delete_many({"id": {"$regex": "^TEST_FILE_"}})
        print(f"Deleted {result.deleted_count} test users")
        
        # Delete test sessions
        result = db.sessions.delete_many({"session_id": {"$regex": "^TEST_FILE_"}})
        print(f"Deleted {result.deleted_count} test sessions")
        
        assert True  # Cleanup always passes
