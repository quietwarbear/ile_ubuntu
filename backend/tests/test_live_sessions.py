"""
Test suite for Live Teaching / Live Sessions feature
Tests all CRUD operations, RBAC permissions, and session state management
"""
import pytest
import requests
import os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import uuid

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# MongoDB connection for test data setup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

client = MongoClient(MONGO_URL)
db = client[DB_NAME]


class TestLiveSessionsSetup:
    """Setup test users and sessions for live sessions testing"""
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_test_data(self, request):
        """Create test users and sessions before tests run"""
        # Create test users
        faculty_id = f"TEST_faculty_{uuid.uuid4().hex[:8]}"
        student_id = f"TEST_student_{uuid.uuid4().hex[:8]}"
        admin_id = f"TEST_admin_{uuid.uuid4().hex[:8]}"
        
        # Faculty user
        faculty_user = {
            "id": faculty_id,
            "email": f"test_faculty_{uuid.uuid4().hex[:6]}@test.com",
            "name": "Test Faculty",
            "role": "faculty",
            "picture": "",
            "created_at": datetime.now(timezone.utc)
        }
        
        # Student user
        student_user = {
            "id": student_id,
            "email": f"test_student_{uuid.uuid4().hex[:6]}@test.com",
            "name": "Test Student",
            "role": "student",
            "picture": "",
            "created_at": datetime.now(timezone.utc)
        }
        
        # Admin user
        admin_user = {
            "id": admin_id,
            "email": f"test_admin_{uuid.uuid4().hex[:6]}@test.com",
            "name": "Test Admin",
            "role": "admin",
            "picture": "",
            "created_at": datetime.now(timezone.utc)
        }
        
        # Insert users
        db.users.insert_many([faculty_user, student_user, admin_user])
        
        # Create sessions for each user
        faculty_session_id = f"TEST_session_{uuid.uuid4().hex}"
        student_session_id = f"TEST_session_{uuid.uuid4().hex}"
        admin_session_id = f"TEST_session_{uuid.uuid4().hex}"
        
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
            },
            {
                "session_id": admin_session_id,
                "user_id": admin_id,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=7)
            }
        ]
        db.sessions.insert_many(sessions)
        
        # Store IDs for tests
        request.cls.faculty_id = faculty_id
        request.cls.student_id = student_id
        request.cls.admin_id = admin_id
        request.cls.faculty_session_id = faculty_session_id
        request.cls.student_session_id = student_session_id
        request.cls.admin_session_id = admin_session_id
        
        yield
        
        # Cleanup after all tests
        db.users.delete_many({"id": {"$regex": "^TEST_"}})
        db.sessions.delete_many({"session_id": {"$regex": "^TEST_"}})
        db.live_sessions.delete_many({"id": {"$regex": "^TEST_"}})
        db.live_sessions.delete_many({"title": {"$regex": "^TEST_"}})


@pytest.mark.usefixtures("setup_test_data")
class TestLiveSessionsCRUD(TestLiveSessionsSetup):
    """Test Live Sessions CRUD operations"""
    
    def test_faculty_can_create_session(self):
        """Faculty can create a live session"""
        response = requests.post(
            f"{BASE_URL}/api/live-sessions",
            json={
                "title": "TEST_Live Session 1",
                "description": "Test description",
                "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            },
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["title"] == "TEST_Live Session 1"
        assert data["description"] == "Test description"
        assert data["status"] == "scheduled"
        assert data["host_id"] == self.faculty_id
        assert data["host_name"] == "Test Faculty"
        assert "room_name" in data
        assert data["room_name"].startswith("ile-ubuntu-")
        # Store session ID for later tests
        self.__class__.created_session_id = data["id"]
    
    def test_student_cannot_create_session(self):
        """Student cannot create a live session (403)"""
        response = requests.post(
            f"{BASE_URL}/api/live-sessions",
            json={
                "title": "TEST_Student Session",
                "description": "Should fail"
            },
            headers={"X-Session-ID": self.student_session_id}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "faculty" in data["detail"].lower() or "permission" in data["detail"].lower()
    
    def test_list_all_sessions(self):
        """List all live sessions"""
        response = requests.get(
            f"{BASE_URL}/api/live-sessions",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # Should contain our created session
        session_ids = [s["id"] for s in data]
        assert self.created_session_id in session_ids
    
    def test_filter_sessions_by_status(self):
        """Filter sessions by status"""
        response = requests.get(
            f"{BASE_URL}/api/live-sessions?status=scheduled",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # All returned sessions should have status=scheduled
        for session in data:
            assert session["status"] == "scheduled"
    
    def test_get_single_session(self):
        """Get a single session by ID"""
        response = requests.get(
            f"{BASE_URL}/api/live-sessions/{self.created_session_id}",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["id"] == self.created_session_id
        assert data["title"] == "TEST_Live Session 1"
        assert data["status"] == "scheduled"
    
    def test_get_nonexistent_session(self):
        """Get a session that doesn't exist returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/live-sessions/nonexistent-id-12345",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"


@pytest.mark.usefixtures("setup_test_data")
class TestLiveSessionsStateManagement(TestLiveSessionsSetup):
    """Test session state transitions (start, join, end)"""
    
    @pytest.fixture(autouse=True)
    def create_test_session(self):
        """Create a fresh session for state management tests"""
        response = requests.post(
            f"{BASE_URL}/api/live-sessions",
            json={
                "title": "TEST_State Management Session",
                "description": "For state tests"
            },
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 200
        self.test_session_id = response.json()["id"]
        yield
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}",
            headers={"X-Session-ID": self.faculty_session_id}
        )
    
    def test_host_can_start_session(self):
        """Host can start their own session"""
        response = requests.put(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}/start",
            json={},
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert "room_name" in data
        
        # Verify session is now live
        get_response = requests.get(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert get_response.json()["status"] == "live"
    
    def test_non_host_cannot_start_session(self):
        """Non-host cannot start someone else's session (403)"""
        response = requests.put(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}/start",
            json={},
            headers={"X-Session-ID": self.student_session_id}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
    
    def test_join_live_session(self):
        """User can join a live session"""
        # First start the session
        requests.put(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}/start",
            json={},
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        # Student joins
        response = requests.post(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}/join",
            json={},
            headers={"X-Session-ID": self.student_session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "room_name" in data
        assert "title" in data
        assert "host_name" in data
    
    def test_cannot_join_non_live_session_as_non_host(self):
        """Non-host cannot join a session that is not live (400)"""
        # Session is still scheduled (not started)
        response = requests.post(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}/join",
            json={},
            headers={"X-Session-ID": self.student_session_id}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "not live" in data["detail"].lower()
    
    def test_host_can_join_scheduled_session(self):
        """Host can join their own scheduled session (to prepare)"""
        response = requests.post(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}/join",
            json={},
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_host_can_end_session(self):
        """Host can end their live session"""
        # Start the session first
        requests.put(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}/start",
            json={},
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        # End the session
        response = requests.put(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}/end",
            json={},
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["success"] == True
        
        # Verify session is now ended
        get_response = requests.get(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert get_response.json()["status"] == "ended"
    
    def test_non_host_cannot_end_session(self):
        """Non-host cannot end someone else's session (403)"""
        # Start the session first
        requests.put(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}/start",
            json={},
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        # Student tries to end
        response = requests.put(
            f"{BASE_URL}/api/live-sessions/{self.test_session_id}/end",
            json={},
            headers={"X-Session-ID": self.student_session_id}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


@pytest.mark.usefixtures("setup_test_data")
class TestLiveSessionsDelete(TestLiveSessionsSetup):
    """Test session deletion permissions"""
    
    def test_host_can_delete_scheduled_session(self):
        """Host can delete their scheduled session"""
        # Create a session
        create_response = requests.post(
            f"{BASE_URL}/api/live-sessions",
            json={"title": "TEST_Delete Scheduled Session"},
            headers={"X-Session-ID": self.faculty_session_id}
        )
        session_id = create_response.json()["id"]
        
        # Delete it
        response = requests.delete(
            f"{BASE_URL}/api/live-sessions/{session_id}",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify it's gone
        get_response = requests.get(
            f"{BASE_URL}/api/live-sessions/{session_id}",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert get_response.status_code == 404
    
    def test_host_can_delete_ended_session(self):
        """Host can delete their ended session"""
        # Create a session
        create_response = requests.post(
            f"{BASE_URL}/api/live-sessions",
            json={"title": "TEST_Delete Ended Session"},
            headers={"X-Session-ID": self.faculty_session_id}
        )
        session_id = create_response.json()["id"]
        
        # Start and end it
        requests.put(
            f"{BASE_URL}/api/live-sessions/{session_id}/start",
            json={},
            headers={"X-Session-ID": self.faculty_session_id}
        )
        requests.put(
            f"{BASE_URL}/api/live-sessions/{session_id}/end",
            json={},
            headers={"X-Session-ID": self.faculty_session_id}
        )
        
        # Delete it
        response = requests.delete(
            f"{BASE_URL}/api/live-sessions/{session_id}",
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_non_host_student_cannot_delete(self):
        """Non-host student cannot delete a session (403)"""
        # Create a session as faculty
        create_response = requests.post(
            f"{BASE_URL}/api/live-sessions",
            json={"title": "TEST_Student Cannot Delete"},
            headers={"X-Session-ID": self.faculty_session_id}
        )
        session_id = create_response.json()["id"]
        
        # Student tries to delete
        response = requests.delete(
            f"{BASE_URL}/api/live-sessions/{session_id}",
            headers={"X-Session-ID": self.student_session_id}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/live-sessions/{session_id}",
            headers={"X-Session-ID": self.faculty_session_id}
        )
    
    def test_admin_can_delete_any_session(self):
        """Admin can delete any session"""
        # Create a session as faculty
        create_response = requests.post(
            f"{BASE_URL}/api/live-sessions",
            json={"title": "TEST_Admin Can Delete"},
            headers={"X-Session-ID": self.faculty_session_id}
        )
        session_id = create_response.json()["id"]
        
        # Admin deletes it
        response = requests.delete(
            f"{BASE_URL}/api/live-sessions/{session_id}",
            headers={"X-Session-ID": self.admin_session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


@pytest.mark.usefixtures("setup_test_data")
class TestLiveSessionsWithCourse(TestLiveSessionsSetup):
    """Test live sessions linked to courses"""
    
    @pytest.fixture(autouse=True)
    def create_test_course(self):
        """Create a test course for linking"""
        course_id = f"TEST_course_{uuid.uuid4().hex[:8]}"
        db.courses.insert_one({
            "id": course_id,
            "title": "TEST_Course for Live Session",
            "description": "Test course",
            "instructor_id": self.faculty_id,
            "status": "active",
            "created_at": datetime.now(timezone.utc)
        })
        self.test_course_id = course_id
        yield
        db.courses.delete_one({"id": course_id})
    
    def test_create_session_with_course_link(self):
        """Create a session linked to a course"""
        response = requests.post(
            f"{BASE_URL}/api/live-sessions",
            json={
                "title": "TEST_Session with Course",
                "description": "Linked to course",
                "course_id": self.test_course_id
            },
            headers={"X-Session-ID": self.faculty_session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["course_id"] == self.test_course_id
        assert data["course_title"] == "TEST_Course for Live Session"
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/live-sessions/{data['id']}",
            headers={"X-Session-ID": self.faculty_session_id}
        )


class TestLiveSessionsCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self):
        """Clean up all test data"""
        # Delete test live sessions
        result = db.live_sessions.delete_many({"$or": [
            {"id": {"$regex": "^TEST_"}},
            {"title": {"$regex": "^TEST_"}}
        ]})
        print(f"Deleted {result.deleted_count} test live sessions")
        
        # Delete test users
        result = db.users.delete_many({"id": {"$regex": "^TEST_"}})
        print(f"Deleted {result.deleted_count} test users")
        
        # Delete test sessions
        result = db.sessions.delete_many({"session_id": {"$regex": "^TEST_"}})
        print(f"Deleted {result.deleted_count} test sessions")
        
        # Delete test courses
        result = db.courses.delete_many({"id": {"$regex": "^TEST_"}})
        print(f"Deleted {result.deleted_count} test courses")
        
        assert True  # Cleanup always passes
