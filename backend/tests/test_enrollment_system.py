"""
Backend API Tests for The Ile Ubuntu - Enrollment System
Tests: Enroll, Unenroll, Progress, Lesson Completion, My Courses, Enrolled Students
"""
import pytest
import requests
import os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import uuid

# Use public URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "http://localhost:8001"

# MongoDB connection for test data setup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

client = MongoClient(MONGO_URL)
db = client[DB_NAME]


class TestEnrollmentSetup:
    """Setup test users, sessions, courses, and lessons for enrollment tests"""
    
    @pytest.fixture(scope="class")
    def test_users(self):
        """Create test users with different roles"""
        users = {
            "faculty": {
                "id": f"TEST_enroll_faculty_{uuid.uuid4().hex[:8]}",
                "email": "test_enroll_faculty@ileubuntu.test",
                "name": "Test Faculty Enrollment",
                "picture": "https://ui-avatars.com/api/?name=Test+Faculty",
                "role": "faculty",
                "bio": "Test faculty user for enrollment",
                "created_at": datetime.now(timezone.utc),
            },
            "student": {
                "id": f"TEST_enroll_student_{uuid.uuid4().hex[:8]}",
                "email": "test_enroll_student@ileubuntu.test",
                "name": "Test Student Enrollment",
                "picture": "https://ui-avatars.com/api/?name=Test+Student",
                "role": "student",
                "bio": "Test student user for enrollment",
                "created_at": datetime.now(timezone.utc),
            },
            "student2": {
                "id": f"TEST_enroll_student2_{uuid.uuid4().hex[:8]}",
                "email": "test_enroll_student2@ileubuntu.test",
                "name": "Test Student 2 Enrollment",
                "picture": "https://ui-avatars.com/api/?name=Test+Student2",
                "role": "student",
                "bio": "Second test student for enrollment",
                "created_at": datetime.now(timezone.utc),
            },
        }
        
        # Insert users into MongoDB
        for role, user in users.items():
            db.users.delete_many({"email": user["email"]})
            db.users.insert_one(user.copy())
        
        yield users
        
        # Cleanup after tests
        for role, user in users.items():
            db.users.delete_many({"email": user["email"]})
    
    @pytest.fixture(scope="class")
    def sessions(self, test_users):
        """Create sessions for test users"""
        sessions = {}
        for role, user in test_users.items():
            session_id = f"TEST_enroll_session_{role}_{uuid.uuid4().hex[:8]}"
            session_data = {
                "session_id": session_id,
                "user_id": user["id"],
                "session_token": f"test_token_{role}",
                "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            }
            db.sessions.delete_many({"user_id": user["id"]})
            db.sessions.insert_one(session_data.copy())
            sessions[role] = session_id
        
        yield sessions
        
        # Cleanup after tests
        for role, session_id in sessions.items():
            db.sessions.delete_many({"session_id": session_id})


class TestEnrollmentEndpoints(TestEnrollmentSetup):
    """Test enrollment-related endpoints"""
    
    @pytest.fixture(scope="class")
    def active_course_with_lessons(self, test_users, sessions):
        """Create an active course with lessons for enrollment testing"""
        headers = {"X-Session-ID": sessions["faculty"]}
        
        # Create course
        course_response = requests.post(
            f"{BASE_URL}/api/courses",
            headers=headers,
            json={
                "title": "TEST_Enrollment_Course_Active",
                "description": "An active course for enrollment testing",
                "tags": ["enrollment", "test"]
            }
        )
        assert course_response.status_code == 200
        course = course_response.json()
        course_id = course["id"]
        
        # Publish the course (set status to active)
        publish_response = requests.put(
            f"{BASE_URL}/api/courses/{course_id}",
            headers=headers,
            json={"status": "active"}
        )
        assert publish_response.status_code == 200
        
        # Create 3 lessons
        lesson_ids = []
        for i in range(1, 4):
            lesson_response = requests.post(
                f"{BASE_URL}/api/courses/{course_id}/lessons",
                headers=headers,
                json={
                    "title": f"TEST_Lesson_{i}",
                    "description": f"Lesson {i} description",
                    "content": f"Content for lesson {i}",
                    "order": i
                }
            )
            assert lesson_response.status_code == 200
            lesson_ids.append(lesson_response.json()["id"])
        
        print(f"✓ Created active course with {len(lesson_ids)} lessons")
        
        yield {"course_id": course_id, "lesson_ids": lesson_ids}
        
        # Cleanup
        try:
            # Delete enrollments first
            db.enrollments.delete_many({"course_id": course_id})
            # Delete lessons
            db.lessons.delete_many({"course_id": course_id})
            # Delete course
            requests.delete(f"{BASE_URL}/api/courses/{course_id}", headers=headers)
        except:
            pass
    
    @pytest.fixture(scope="class")
    def draft_course(self, test_users, sessions):
        """Create a draft course (not active) for testing enrollment restrictions"""
        headers = {"X-Session-ID": sessions["faculty"]}
        
        course_response = requests.post(
            f"{BASE_URL}/api/courses",
            headers=headers,
            json={
                "title": "TEST_Enrollment_Course_Draft",
                "description": "A draft course - should not allow enrollment",
                "tags": ["draft", "test"]
            }
        )
        assert course_response.status_code == 200
        course = course_response.json()
        course_id = course["id"]
        
        print(f"✓ Created draft course: {course['title']}")
        
        yield course_id
        
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/api/courses/{course_id}", headers=headers)
        except:
            pass
    
    # --- Enrollment Tests ---
    
    def test_enroll_in_active_course(self, test_users, sessions, active_course_with_lessons):
        """POST /api/courses/{id}/enroll - Student enrolls in active course"""
        headers = {"X-Session-ID": sessions["student"]}
        course_id = active_course_with_lessons["course_id"]
        
        # First, unenroll if already enrolled (cleanup from previous runs)
        requests.post(f"{BASE_URL}/api/courses/{course_id}/unenroll", headers=headers)
        
        # Get initial enrolled_count
        course_before = requests.get(f"{BASE_URL}/api/courses/{course_id}", headers=headers).json()
        initial_count = course_before.get("enrolled_count", 0)
        
        # Enroll
        response = requests.post(f"{BASE_URL}/api/courses/{course_id}/enroll", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify enrollment data
        assert data["user_id"] == test_users["student"]["id"]
        assert data["course_id"] == course_id
        assert data["status"] == "active"
        assert data["progress"] == 0.0
        assert data["completed_lessons"] == []
        assert "enrolled_at" in data
        print(f"✓ Student enrolled in course: {data['id']}")
        
        # Verify enrolled_count incremented
        course_after = requests.get(f"{BASE_URL}/api/courses/{course_id}", headers=headers).json()
        assert course_after["enrolled_count"] == initial_count + 1
        print(f"✓ Enrolled count incremented: {initial_count} -> {course_after['enrolled_count']}")
    
    def test_cannot_enroll_in_draft_course(self, test_users, sessions, draft_course):
        """POST /api/courses/{id}/enroll - Cannot enroll in draft course (400)"""
        headers = {"X-Session-ID": sessions["student"]}
        
        response = requests.post(f"{BASE_URL}/api/courses/{draft_course}/enroll", headers=headers)
        assert response.status_code == 400
        data = response.json()
        assert "not open for enrollment" in data["detail"].lower() or "not active" in data["detail"].lower()
        print("✓ Cannot enroll in draft course (400)")
    
    def test_cannot_double_enroll(self, test_users, sessions, active_course_with_lessons):
        """POST /api/courses/{id}/enroll - Cannot double-enroll (400)"""
        headers = {"X-Session-ID": sessions["student"]}
        course_id = active_course_with_lessons["course_id"]
        
        # Try to enroll again (should already be enrolled from previous test)
        response = requests.post(f"{BASE_URL}/api/courses/{course_id}/enroll", headers=headers)
        assert response.status_code == 400
        data = response.json()
        assert "already enrolled" in data["detail"].lower()
        print("✓ Cannot double-enroll (400)")
    
    def test_get_enrollment_status_enrolled(self, test_users, sessions, active_course_with_lessons):
        """GET /api/courses/{id}/enrollment - Returns enrollment status (enrolled)"""
        headers = {"X-Session-ID": sessions["student"]}
        course_id = active_course_with_lessons["course_id"]
        
        response = requests.get(f"{BASE_URL}/api/courses/{course_id}/enrollment", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["enrolled"] == True
        assert data["enrollment"] is not None
        assert data["enrollment"]["user_id"] == test_users["student"]["id"]
        print(f"✓ Enrollment status: enrolled=True")
    
    def test_get_enrollment_status_not_enrolled(self, test_users, sessions, active_course_with_lessons):
        """GET /api/courses/{id}/enrollment - Returns enrollment status (not enrolled)"""
        headers = {"X-Session-ID": sessions["student2"]}
        course_id = active_course_with_lessons["course_id"]
        
        response = requests.get(f"{BASE_URL}/api/courses/{course_id}/enrollment", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["enrolled"] == False
        assert data["enrollment"] is None
        print(f"✓ Enrollment status: enrolled=False for non-enrolled student")
    
    # --- Lesson Completion & Progress Tests ---
    
    def test_complete_lesson_updates_progress(self, test_users, sessions, active_course_with_lessons):
        """POST /api/courses/{id}/lessons/{lid}/complete - Mark lesson complete, progress updates"""
        headers = {"X-Session-ID": sessions["student"]}
        course_id = active_course_with_lessons["course_id"]
        lesson_ids = active_course_with_lessons["lesson_ids"]
        
        # Complete first lesson
        response = requests.post(
            f"{BASE_URL}/api/courses/{course_id}/lessons/{lesson_ids[0]}/complete",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "progress" in data
        # With 3 lessons, completing 1 should be ~33.3%
        assert data["progress"] > 0
        print(f"✓ Completed lesson 1, progress: {data['progress']}%")
        
        # Complete second lesson
        response2 = requests.post(
            f"{BASE_URL}/api/courses/{course_id}/lessons/{lesson_ids[1]}/complete",
            headers=headers
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # With 3 lessons, completing 2 should be ~66.7%
        assert data2["progress"] > data["progress"]
        print(f"✓ Completed lesson 2, progress: {data2['progress']}%")
    
    def test_complete_lesson_already_completed(self, test_users, sessions, active_course_with_lessons):
        """POST /api/courses/{id}/lessons/{lid}/complete - Already completed returns message"""
        headers = {"X-Session-ID": sessions["student"]}
        course_id = active_course_with_lessons["course_id"]
        lesson_ids = active_course_with_lessons["lesson_ids"]
        
        # Try to complete first lesson again
        response = requests.post(
            f"{BASE_URL}/api/courses/{course_id}/lessons/{lesson_ids[0]}/complete",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "already completed" in data.get("message", "").lower()
        print("✓ Already completed lesson returns appropriate message")
    
    def test_complete_lesson_not_enrolled(self, test_users, sessions, active_course_with_lessons):
        """POST /api/courses/{id}/lessons/{lid}/complete - Not enrolled returns 400"""
        headers = {"X-Session-ID": sessions["student2"]}
        course_id = active_course_with_lessons["course_id"]
        lesson_ids = active_course_with_lessons["lesson_ids"]
        
        response = requests.post(
            f"{BASE_URL}/api/courses/{course_id}/lessons/{lesson_ids[0]}/complete",
            headers=headers
        )
        assert response.status_code == 400
        data = response.json()
        assert "not enrolled" in data["detail"].lower()
        print("✓ Cannot complete lesson if not enrolled (400)")
    
    def test_get_course_progress(self, test_users, sessions, active_course_with_lessons):
        """GET /api/courses/{id}/progress - Returns progress with completed_lessons and total_lessons"""
        headers = {"X-Session-ID": sessions["student"]}
        course_id = active_course_with_lessons["course_id"]
        
        response = requests.get(f"{BASE_URL}/api/courses/{course_id}/progress", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["enrolled"] == True
        assert "progress" in data
        assert "completed_lessons" in data
        assert "total_lessons" in data
        assert data["total_lessons"] == 3
        assert len(data["completed_lessons"]) == 2  # We completed 2 lessons
        assert data["status"] == "active"
        print(f"✓ Progress: {data['progress']}%, {len(data['completed_lessons'])}/{data['total_lessons']} lessons")
    
    def test_get_course_progress_not_enrolled(self, test_users, sessions, active_course_with_lessons):
        """GET /api/courses/{id}/progress - Not enrolled returns enrolled=False"""
        headers = {"X-Session-ID": sessions["student2"]}
        course_id = active_course_with_lessons["course_id"]
        
        response = requests.get(f"{BASE_URL}/api/courses/{course_id}/progress", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["enrolled"] == False
        assert data["progress"] == 0
        assert data["completed_lessons"] == []
        print("✓ Progress for non-enrolled: enrolled=False, progress=0")
    
    def test_complete_all_lessons_marks_completed(self, test_users, sessions, active_course_with_lessons):
        """Complete all lessons marks enrollment as completed"""
        headers = {"X-Session-ID": sessions["student"]}
        course_id = active_course_with_lessons["course_id"]
        lesson_ids = active_course_with_lessons["lesson_ids"]
        
        # Complete the third (last) lesson
        response = requests.post(
            f"{BASE_URL}/api/courses/{course_id}/lessons/{lesson_ids[2]}/complete",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["progress"] == 100.0
        print(f"✓ Completed all lessons, progress: {data['progress']}%")
        
        # Check progress endpoint shows completed status
        progress_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/progress", headers=headers)
        progress_data = progress_response.json()
        assert progress_data["status"] == "completed"
        print("✓ Enrollment status changed to 'completed'")
    
    # --- My Courses Tests ---
    
    def test_get_my_courses(self, test_users, sessions, active_course_with_lessons):
        """GET /api/enrollments/my-courses - Returns enriched enrollment list"""
        headers = {"X-Session-ID": sessions["student"]}
        
        response = requests.get(f"{BASE_URL}/api/enrollments/my-courses", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Find our test enrollment
        test_enrollment = next((e for e in data if e["course_id"] == active_course_with_lessons["course_id"]), None)
        assert test_enrollment is not None
        
        # Verify enriched data
        assert "course_title" in test_enrollment
        assert "course_description" in test_enrollment
        assert "instructor_name" in test_enrollment
        assert "total_lessons" in test_enrollment
        assert "course_status" in test_enrollment
        assert test_enrollment["course_title"] == "TEST_Enrollment_Course_Active"
        print(f"✓ My courses returns {len(data)} enrollments with enriched data")
    
    def test_get_my_courses_empty(self, test_users, sessions):
        """GET /api/enrollments/my-courses - Returns empty list for non-enrolled user"""
        headers = {"X-Session-ID": sessions["student2"]}
        
        response = requests.get(f"{BASE_URL}/api/enrollments/my-courses", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Filter out any test enrollments (should be empty for student2)
        test_enrollments = [e for e in data if "TEST_" in e.get("course_title", "")]
        assert len(test_enrollments) == 0
        print("✓ My courses returns empty for non-enrolled student")
    
    # --- Enrolled Students (Faculty View) Tests ---
    
    def test_faculty_can_see_enrolled_students(self, test_users, sessions, active_course_with_lessons):
        """GET /api/courses/{id}/enrollments - Faculty can see enrolled students"""
        headers = {"X-Session-ID": sessions["faculty"]}
        course_id = active_course_with_lessons["course_id"]
        
        response = requests.get(f"{BASE_URL}/api/courses/{course_id}/enrollments", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Find our test student enrollment
        student_enrollment = next((e for e in data if e["user_id"] == test_users["student"]["id"]), None)
        assert student_enrollment is not None
        assert student_enrollment["user_name"] == test_users["student"]["name"]
        assert "progress" in student_enrollment
        assert "enrolled_at" in student_enrollment
        print(f"✓ Faculty can see {len(data)} enrolled students")
    
    def test_student_cannot_see_enrollments(self, test_users, sessions, active_course_with_lessons):
        """GET /api/courses/{id}/enrollments - Student cannot see enrollments (403)"""
        headers = {"X-Session-ID": sessions["student2"]}
        course_id = active_course_with_lessons["course_id"]
        
        response = requests.get(f"{BASE_URL}/api/courses/{course_id}/enrollments", headers=headers)
        assert response.status_code == 403
        print("✓ Student cannot see course enrollments (403)")
    
    # --- Unenroll Tests ---
    
    def test_unenroll_from_course(self, test_users, sessions, active_course_with_lessons):
        """POST /api/courses/{id}/unenroll - Student unenrolls from course"""
        headers = {"X-Session-ID": sessions["student"]}
        course_id = active_course_with_lessons["course_id"]
        
        # Get enrolled_count before unenroll
        course_before = requests.get(f"{BASE_URL}/api/courses/{course_id}", headers=headers).json()
        count_before = course_before.get("enrolled_count", 0)
        
        response = requests.post(f"{BASE_URL}/api/courses/{course_id}/unenroll", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print("✓ Student unenrolled from course")
        
        # Verify enrolled_count decremented
        course_after = requests.get(f"{BASE_URL}/api/courses/{course_id}", headers=headers).json()
        assert course_after["enrolled_count"] == count_before - 1
        print(f"✓ Enrolled count decremented: {count_before} -> {course_after['enrolled_count']}")
        
        # Verify enrollment status
        enrollment_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/enrollment", headers=headers)
        enrollment_data = enrollment_response.json()
        assert enrollment_data["enrolled"] == False
        print("✓ Enrollment status shows not enrolled after unenroll")
    
    def test_unenroll_not_enrolled(self, test_users, sessions, active_course_with_lessons):
        """POST /api/courses/{id}/unenroll - Not enrolled returns 404"""
        headers = {"X-Session-ID": sessions["student2"]}
        course_id = active_course_with_lessons["course_id"]
        
        response = requests.post(f"{BASE_URL}/api/courses/{course_id}/unenroll", headers=headers)
        assert response.status_code == 404
        print("✓ Cannot unenroll if not enrolled (404)")


class TestEnrollmentCleanup:
    """Cleanup test data after all enrollment tests"""
    
    def test_cleanup_enrollment_test_data(self):
        """Remove all TEST_Enrollment_ prefixed data"""
        # Clean up enrollments
        deleted_enrollments = db.enrollments.delete_many({"course_id": {"$regex": "TEST_"}})
        print(f"Cleaned up {deleted_enrollments.deleted_count} test enrollments")
        
        # Clean up lessons
        deleted_lessons = db.lessons.delete_many({"title": {"$regex": "^TEST_"}})
        print(f"Cleaned up {deleted_lessons.deleted_count} test lessons")
        
        # Clean up courses
        deleted_courses = db.courses.delete_many({"title": {"$regex": "^TEST_Enrollment_"}})
        print(f"Cleaned up {deleted_courses.deleted_count} test courses")
        
        # Clean up test users
        deleted_users = db.users.delete_many({"email": {"$regex": "test_enroll.*@ileubuntu.test$"}})
        print(f"Cleaned up {deleted_users.deleted_count} test users")
        
        # Clean up test sessions
        deleted_sessions = db.sessions.delete_many({"session_id": {"$regex": "^TEST_enroll_"}})
        print(f"Cleaned up {deleted_sessions.deleted_count} test sessions")
        
        print("✓ All enrollment test data cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
